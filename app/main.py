from fastapi import FastAPI, Query, HTTPException
from typing import Optional, Dict, Any, List
import math
import logging
import re
from datetime import datetime, timezone
from pydantic import BaseModel
from app.db import get_db_connection, DATABASE_URL

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

HEX_COLOR_REGEX = re.compile(r"^#[0-9a-fA-F]{6}$")

app = FastAPI(title="Beacon Hub API")


class TagColorUpdate(BaseModel):
    color: str


class TagCreate(BaseModel):
    name: str
    color: str


class CalendarTagUpdate(BaseModel):
    tag_id: int


@app.get("/api/opportunities")
def get_opportunities(
    domain: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        where_clauses = ["(deadline_utc >= ? OR deadline_utc IS NULL)"]
        params = [now_utc]

        if DATABASE_URL:
            where_clauses = ["(deadline_utc >= %s OR deadline_utc IS NULL)"]

        if domain:
            where_clauses.append("domain = %s" if DATABASE_URL else "domain = ?")
            params.append(domain)
        if category:
            where_clauses.append("category = %s" if DATABASE_URL else "category = ?")
            params.append(category)
        if mode:
            where_clauses.append("mode = %s" if DATABASE_URL else "mode = ?")
            params.append(mode)

        where_str = " WHERE " + " AND ".join(where_clauses)

        count_sql = f"SELECT COUNT(*) FROM opportunities{where_str}"
        cursor.execute(count_sql, params)
        res = cursor.fetchone()
        total = res["count"] if isinstance(res, dict) else res[0]

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        page = min(page, total_pages)
        offset = (page - 1) * page_size

        if DATABASE_URL:
            sql = f"""
            SELECT o.*,
                   CASE WHEN t.id IS NOT NULL THEN TRUE ELSE FALSE END as in_todo,
                   CASE WHEN c.id IS NOT NULL THEN TRUE ELSE FALSE END as in_calendar
            FROM opportunities o
            LEFT JOIN todo_items t ON o.id = t.opportunity_id
            LEFT JOIN calendar_items c ON o.id = c.opportunity_id
            {where_str}
            ORDER BY o.deadline_utc ASC NULLS LAST, o.id ASC
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, params + [page_size, offset])
        else:
            sql = f"""
            SELECT o.*,
                   CASE WHEN t.id IS NOT NULL THEN 1 ELSE 0 END as in_todo,
                   CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END as in_calendar
            FROM opportunities o
            LEFT JOIN todo_items t ON o.id = t.opportunity_id
            LEFT JOIN calendar_items c ON o.id = c.opportunity_id
            {where_str}
            ORDER BY CASE WHEN o.deadline_utc IS NULL THEN 1 ELSE 0 END, o.deadline_utc ASC, o.id ASC
            LIMIT ? OFFSET ?
            """
            cursor.execute(sql, params + [page_size, offset])

        rows = cursor.fetchall()
        items = []
        for r in rows:
            item = dict(r)
            item["verified"] = bool(item.get("verified"))
            item["in_todo"] = bool(item.get("in_todo"))
            item["in_calendar"] = bool(item.get("in_calendar"))
            items.append(item)

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }
    finally:
        conn.close()


# --- To-Do Endpoints ---


@app.post("/api/todo/{opportunity_id}")
def add_to_todo(opportunity_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql_check = "SELECT id FROM opportunities WHERE id = %s" if DATABASE_URL else "SELECT id FROM opportunities WHERE id = ?"
        cursor.execute(sql_check, (opportunity_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Opportunity not found")

        if DATABASE_URL:
            sql_insert = """
            INSERT INTO todo_items (opportunity_id, status)
            VALUES (%s, 'active')
            ON CONFLICT (opportunity_id) DO NOTHING
            """
        else:
            sql_insert = """
            INSERT OR IGNORE INTO todo_items (opportunity_id, status)
            VALUES (?, 'active')
            """
        cursor.execute(sql_insert, (opportunity_id,))
        conn.commit()
        return {"message": "Added to To-Do", "opportunity_id": opportunity_id, "status": "active"}
    finally:
        conn.close()


@app.delete("/api/todo/{opportunity_id}")
def remove_from_todo(opportunity_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql_check = "SELECT id FROM opportunities WHERE id = %s" if DATABASE_URL else "SELECT id FROM opportunities WHERE id = ?"
        cursor.execute(sql_check, (opportunity_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Opportunity not found")

        sql_del = "DELETE FROM todo_items WHERE opportunity_id = %s" if DATABASE_URL else "DELETE FROM todo_items WHERE opportunity_id = ?"
        cursor.execute(sql_del, (opportunity_id,))
        conn.commit()
        return {"message": "Removed from To-Do", "opportunity_id": opportunity_id}
    finally:
        conn.close()


@app.patch("/api/todo/{opportunity_id}/toggle")
def toggle_todo_status(opportunity_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql_check = "SELECT id FROM opportunities WHERE id = %s" if DATABASE_URL else "SELECT id FROM opportunities WHERE id = ?"
        cursor.execute(sql_check, (opportunity_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Opportunity not found")

        sql_todo = "SELECT status FROM todo_items WHERE opportunity_id = %s" if DATABASE_URL else "SELECT status FROM todo_items WHERE opportunity_id = ?"
        cursor.execute(sql_todo, (opportunity_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not in To-Do list")

        current_status = row["status"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row[0]
        if current_status == "active":
            new_status = "done"
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            sql_update = (
                "UPDATE todo_items SET status = 'done', completed_at = %s WHERE opportunity_id = %s"
                if DATABASE_URL
                else "UPDATE todo_items SET status = 'done', completed_at = ? WHERE opportunity_id = ?"
            )
            cursor.execute(sql_update, (now_iso, opportunity_id))
        else:
            new_status = "active"
            sql_update = (
                "UPDATE todo_items SET status = 'active', completed_at = NULL WHERE opportunity_id = %s"
                if DATABASE_URL
                else "UPDATE todo_items SET status = 'active', completed_at = NULL WHERE opportunity_id = ?"
            )
            cursor.execute(sql_update, (opportunity_id,))
        conn.commit()
        return {"opportunity_id": opportunity_id, "status": new_status}
    finally:
        conn.close()


@app.get("/api/todo")
def get_todo_list():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql = """
        SELECT o.id as opportunity_id, o.title, o.domain, o.category, o.mode,
               o.deadline_utc, o.event_date_utc, o.about, o.url, o.source_domain,
               t.status, t.added_at, t.completed_at,
               CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END as in_calendar
        FROM todo_items t
        JOIN opportunities o ON t.opportunity_id = o.id
        LEFT JOIN calendar_items c ON o.id = c.opportunity_id
        ORDER BY t.added_at ASC, t.id ASC
        """
        if DATABASE_URL:
            sql = sql.replace(
                "CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END",
                "CASE WHEN c.id IS NOT NULL THEN TRUE ELSE FALSE END",
            )

        cursor.execute(sql)
        rows = cursor.fetchall()

        result = {
            "cyber": {"active": [], "completed": []},
            "ai": {"active": [], "completed": []},
            "cloud": {"active": [], "completed": []},
        }

        for r in rows:
            row_dict = dict(r)
            domain = row_dict.get("domain")
            if domain not in result:
                continue
            status = row_dict.get("status")
            status_key = "completed" if status == "done" else "active"

            item = {
                "opportunity_id": row_dict.get("opportunity_id"),
                "title": row_dict.get("title"),
                "domain": domain,
                "category": row_dict.get("category"),
                "mode": row_dict.get("mode"),
                "deadline_utc": row_dict.get("deadline_utc"),
                "event_date_utc": row_dict.get("event_date_utc"),
                "about": row_dict.get("about"),
                "url": row_dict.get("url"),
                "source_domain": row_dict.get("source_domain"),
                "in_calendar": bool(row_dict.get("in_calendar")),
                "status": status,
                "completed_at": row_dict.get("completed_at"),
            }
            result[domain][status_key].append(item)

        return result
    finally:
        conn.close()


# --- Calendar Endpoints ---


@app.post("/api/calendar/{opportunity_id}")
def add_to_calendar(opportunity_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql_check = "SELECT id, domain FROM opportunities WHERE id = %s" if DATABASE_URL else "SELECT id, domain FROM opportunities WHERE id = ?"
        cursor.execute(sql_check, (opportunity_id,))
        opp = cursor.fetchone()
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        opp_domain = opp["domain"] if isinstance(opp, dict) or hasattr(opp, "__getitem__") else opp[1]
        domain_tag_map = {
            "cyber": "Cybersecurity",
            "ai": "AI",
            "cloud": "Cloud",
        }
        target_tag_name = domain_tag_map.get(opp_domain, "Cybersecurity")

        sql_tag = "SELECT id FROM calendar_tags WHERE name = %s" if DATABASE_URL else "SELECT id FROM calendar_tags WHERE LOWER(name) = LOWER(?)"
        cursor.execute(sql_tag, (target_tag_name,))
        tag_row = cursor.fetchone()
        tag_id = (tag_row["id"] if isinstance(tag_row, dict) or hasattr(tag_row, "__getitem__") else tag_row[0]) if tag_row else None

        if DATABASE_URL:
            sql_insert = """
            INSERT INTO calendar_items (opportunity_id, tag_id)
            VALUES (%s, %s)
            ON CONFLICT (opportunity_id) DO NOTHING
            """
        else:
            sql_insert = """
            INSERT OR IGNORE INTO calendar_items (opportunity_id, tag_id)
            VALUES (?, ?)
            """
        cursor.execute(sql_insert, (opportunity_id, tag_id))
        conn.commit()
        return {"message": "Added to Calendar", "opportunity_id": opportunity_id, "tag_id": tag_id}
    finally:
        conn.close()


@app.delete("/api/calendar/{opportunity_id}")
def remove_from_calendar(opportunity_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql_check = "SELECT id FROM opportunities WHERE id = %s" if DATABASE_URL else "SELECT id FROM opportunities WHERE id = ?"
        cursor.execute(sql_check, (opportunity_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Opportunity not found")

        sql_del = "DELETE FROM calendar_items WHERE opportunity_id = %s" if DATABASE_URL else "DELETE FROM calendar_items WHERE opportunity_id = ?"
        cursor.execute(sql_del, (opportunity_id,))
        conn.commit()
        return {"message": "Removed from Calendar", "opportunity_id": opportunity_id}
    finally:
        conn.close()


@app.get("/api/calendar")
def get_calendar_items(month: str = Query(..., pattern=r"^\d{4}-\d{2}$")):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql = """
        SELECT c.opportunity_id, o.title, o.domain, o.category, o.event_date_utc, o.deadline_utc, o.location, o.url,
               t.name as tag_name, t.color as tag_color
        FROM calendar_items c
        JOIN opportunities o ON c.opportunity_id = o.id
        LEFT JOIN calendar_tags t ON c.tag_id = t.id
        """
        cursor.execute(sql)
        rows = cursor.fetchall()

        entries = []
        for r in rows:
            r_dict = dict(r)
            event_date = r_dict.get("event_date_utc")
            deadline_date = r_dict.get("deadline_utc")

            base_entry = {
                "opportunity_id": r_dict.get("opportunity_id"),
                "title": r_dict.get("title"),
                "domain": r_dict.get("domain"),
                "category": r_dict.get("category"),
                "event_date_utc": event_date,
                "deadline_utc": deadline_date,
                "location": r_dict.get("location"),
                "url": r_dict.get("url"),
                "tag_name": r_dict.get("tag_name"),
                "tag_color": r_dict.get("tag_color"),
            }

            if event_date and event_date.startswith(month):
                entry = dict(base_entry)
                entry["kind"] = "event"
                entry["date"] = event_date
                entries.append(entry)

            if deadline_date and deadline_date.startswith(month):
                entry = dict(base_entry)
                entry["kind"] = "deadline"
                entry["date"] = deadline_date
                entries.append(entry)

        return {"entries": entries}
    finally:
        conn.close()


# --- Tags Endpoints ---


@app.get("/api/tags")
def get_tags():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, color, is_default FROM calendar_tags ORDER BY id ASC")
        rows = cursor.fetchall()
        tags = []
        for r in rows:
            r_dict = dict(r)
            r_dict["is_default"] = bool(r_dict.get("is_default"))
            tags.append(r_dict)
        return tags
    finally:
        conn.close()


@app.patch("/api/tags/{id}")
def update_tag_color(id: int, payload: TagColorUpdate):
    if not HEX_COLOR_REGEX.match(payload.color):
        raise HTTPException(status_code=400, detail="Invalid hex color format")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql_check = "SELECT id, name, color, is_default FROM calendar_tags WHERE id = %s" if DATABASE_URL else "SELECT id, name, color, is_default FROM calendar_tags WHERE id = ?"
        cursor.execute(sql_check, (id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tag not found")

        sql_update = "UPDATE calendar_tags SET color = %s WHERE id = %s" if DATABASE_URL else "UPDATE calendar_tags SET color = ? WHERE id = ?"
        cursor.execute(sql_update, (payload.color, id))
        conn.commit()

        tag_dict = dict(row)
        tag_dict["color"] = payload.color
        tag_dict["is_default"] = bool(tag_dict.get("is_default"))
        return tag_dict
    finally:
        conn.close()


@app.post("/api/tags")
def create_custom_tag(payload: TagCreate):
    if not HEX_COLOR_REGEX.match(payload.color):
        raise HTTPException(status_code=400, detail="Invalid hex color format")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if DATABASE_URL:
            sql_insert = "INSERT INTO calendar_tags (name, color, is_default) VALUES (%s, %s, FALSE) RETURNING id"
            cursor.execute(sql_insert, (payload.name, payload.color))
            res = cursor.fetchone()
            tag_id = res["id"] if isinstance(res, dict) else res[0]
        else:
            sql_insert = "INSERT INTO calendar_tags (name, color, is_default) VALUES (?, ?, 0)"
            cursor.execute(sql_insert, (payload.name, payload.color))
            tag_id = cursor.lastrowid

        conn.commit()
        return {"id": tag_id, "name": payload.name, "color": payload.color, "is_default": False}
    finally:
        conn.close()


@app.patch("/api/calendar/{opportunity_id}/tag")
def assign_calendar_tag(opportunity_id: int, payload: CalendarTagUpdate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        sql_opp = "SELECT id FROM opportunities WHERE id = %s" if DATABASE_URL else "SELECT id FROM opportunities WHERE id = ?"
        cursor.execute(sql_opp, (opportunity_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Opportunity not found")

        sql_cal = "SELECT id FROM calendar_items WHERE opportunity_id = %s" if DATABASE_URL else "SELECT id FROM calendar_items WHERE opportunity_id = ?"
        cursor.execute(sql_cal, (opportunity_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Calendar item not found")

        sql_tag = "SELECT id FROM calendar_tags WHERE id = %s" if DATABASE_URL else "SELECT id FROM calendar_tags WHERE id = ?"
        cursor.execute(sql_tag, (payload.tag_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Tag not found")

        sql_update = "UPDATE calendar_items SET tag_id = %s WHERE opportunity_id = %s" if DATABASE_URL else "UPDATE calendar_items SET tag_id = ? WHERE opportunity_id = ?"
        cursor.execute(sql_update, (payload.tag_id, opportunity_id))
        conn.commit()

        return {"message": "Calendar tag updated", "opportunity_id": opportunity_id, "tag_id": payload.tag_id}
    finally:
        conn.close()
