import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from app.db import get_db_connection, DATABASE_URL

logger = logging.getLogger(__name__)


def parse_utc_datetime(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        s = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def compute_reminder_times(
    title: str,
    deadline_utc: Optional[str],
    event_date_utc: Optional[str],
    now_utc: datetime,
) -> List[Dict[str, Any]]:
    target_str = deadline_utc if deadline_utc else event_date_utc
    label = "deadline" if deadline_utc else "event"
    if not target_str:
        return []

    target_dt = parse_utc_datetime(target_str)
    if not target_dt:
        return []

    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    candidates = [
        ("7d", target_dt - timedelta(days=7), f"{title}: {label} in 7 days"),
        ("3d", target_dt - timedelta(days=3), f"{title}: {label} in 3 days"),
        ("1d", target_dt - timedelta(days=1), f"{title}: {label} in 1 day"),
        ("day_of", target_dt, f"{title}: today is the {label}"),
    ]

    results = []
    for kind, due_dt, message in candidates:
        if due_dt > now_utc:
            results.append({
                "kind": kind,
                "due_at_utc": due_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "due_at_dt": due_dt,
                "message": message,
            })

    results.sort(key=lambda x: x["due_at_dt"])
    return results


@activity.defn
async def load_dates(opportunity_id: int) -> dict:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql = (
            "SELECT title, deadline_utc, event_date_utc FROM opportunities WHERE id = %s"
            if DATABASE_URL
            else "SELECT title, deadline_utc, event_date_utc FROM opportunities WHERE id = ?"
        )
        cursor.execute(sql, (opportunity_id,))
        row = cursor.fetchone()
        demo = bool(os.getenv("DEMO_MODE"))
        if not row:
            return {"title": "Opportunity", "deadline_utc": None, "event_date_utc": None, "demo_mode": demo}
        r = dict(row)
        return {
            "title": r.get("title") or "Opportunity",
            "deadline_utc": r.get("deadline_utc"),
            "event_date_utc": r.get("event_date_utc"),
            "demo_mode": demo,
        }
    finally:
        conn.close()


@activity.defn
async def is_still_active(opportunity_id: int) -> bool:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql = (
            "SELECT status FROM todo_items WHERE opportunity_id = %s"
            if DATABASE_URL
            else "SELECT status FROM todo_items WHERE opportunity_id = ?"
        )
        cursor.execute(sql, (opportunity_id,))
        row = cursor.fetchone()
        if not row:
            return False
        status = row["status"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row[0]
        return status == "active"
    finally:
        conn.close()


@activity.defn
async def fire_reminder(opportunity_id: int, kind: str, message: str, due_at_utc: str) -> None:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if DATABASE_URL:
            sql = """
            INSERT INTO reminders (opportunity_id, kind, due_at_utc, message)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (opportunity_id, kind) DO NOTHING
            """
        else:
            sql = """
            INSERT OR IGNORE INTO reminders (opportunity_id, kind, due_at_utc, message)
            VALUES (?, ?, ?, ?)
            """
        cursor.execute(sql, (opportunity_id, kind, due_at_utc, message))
        conn.commit()
    finally:
        conn.close()


@workflow.defn
class ReminderWorkflow:
    @workflow.run
    async def run(self, opportunity_id: int) -> None:
        retry_policy = RetryPolicy(maximum_attempts=5)

        data = await workflow.execute_activity(
            load_dates,
            opportunity_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        title = data.get("title", "Opportunity")
        demo_mode = data.get("demo_mode", False)

        if demo_mode:
            delays = [10, 20, 30]
            start_time = workflow.now()
            for delay in delays:
                active = await workflow.execute_activity(
                    is_still_active,
                    opportunity_id,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
                if not active:
                    return

                target_time = start_time + timedelta(seconds=delay)
                sleep_sec = (target_time - workflow.now()).total_seconds()
                if sleep_sec > 0:
                    await workflow.sleep(sleep_sec)

                active = await workflow.execute_activity(
                    is_still_active,
                    opportunity_id,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
                if not active:
                    return

                due_at_str = target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                msg = f"{title}: demo reminder ({delay}s)"
                await workflow.execute_activity(
                    fire_reminder,
                    args=[opportunity_id, "demo", msg, due_at_str],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
            return

        deadline_utc = data.get("deadline_utc")
        event_date_utc = data.get("event_date_utc")
        now_dt = workflow.now()

        reminders = compute_reminder_times(title, deadline_utc, event_date_utc, now_dt)
        if not reminders:
            return

        for rem in reminders:
            active = await workflow.execute_activity(
                is_still_active,
                opportunity_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            if not active:
                return

            due_dt = rem["due_at_dt"]
            sleep_sec = (due_dt - workflow.now()).total_seconds()
            if sleep_sec > 0:
                await workflow.sleep(sleep_sec)

            active = await workflow.execute_activity(
                is_still_active,
                opportunity_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
            if not active:
                return

            await workflow.execute_activity(
                fire_reminder,
                args=[opportunity_id, rem["kind"], rem["message"], rem["due_at_utc"]],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
