import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import CREATE_TABLES_SQL, SEED_TAGS, get_db_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "test_todo_calendar.db")
    monkeypatch.setattr("app.db.DATABASE_URL", "")

    def test_db_conn():
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr("app.main.get_db_connection", test_db_conn)
    monkeypatch.setattr("app.db.get_db_connection", test_db_conn)

    conn = test_db_conn()
    cursor = conn.cursor()
    cursor.executescript(CREATE_TABLES_SQL)

    cursor.execute("SELECT COUNT(*) FROM calendar_tags")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO calendar_tags (name, color, is_default) VALUES (?, ?, ?)",
            SEED_TAGS,
        )

    # Seed test opportunities
    cursor.execute(
        """INSERT INTO opportunities (id, title, url, domain, category, mode, event_date_utc, deadline_utc)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            1,
            "Cyber Hackathon",
            "https://example.com/cyber1",
            "cyber",
            "hackathon",
            "virtual",
            "2026-10-20T10:00:00Z",
            "2026-10-12T10:00:00Z",
        ),
    )
    cursor.execute(
        """INSERT INTO opportunities (id, title, url, domain, category, mode, event_date_utc, deadline_utc)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            2,
            "AI Course",
            "https://example.com/ai2",
            "ai",
            "course",
            "virtual",
            "2026-10-25T10:00:00Z",
            "2026-10-15T10:00:00Z",
        ),
    )
    conn.commit()
    conn.close()


def test_add_and_toggle_todo_status():
    # Add item 1 to todo
    res_add = client.post("/api/todo/1")
    assert res_add.status_code == 200

    # Verify active in GET /api/todo
    res_get1 = client.get("/api/todo")
    assert res_get1.status_code == 200
    data1 = res_get1.json()
    assert len(data1["cyber"]["active"]) == 1
    assert data1["cyber"]["active"][0]["opportunity_id"] == 1
    assert len(data1["cyber"]["completed"]) == 0

    # Toggle status (active -> done)
    res_toggle1 = client.patch("/api/todo/1/toggle")
    assert res_toggle1.status_code == 200
    assert res_toggle1.json()["status"] == "done"

    # Verify completed in GET /api/todo
    res_get2 = client.get("/api/todo")
    data2 = res_get2.json()
    assert len(data2["cyber"]["active"]) == 0
    assert len(data2["cyber"]["completed"]) == 1
    assert data2["cyber"]["completed"][0]["opportunity_id"] == 1

    # Toggle status back (done -> active)
    res_toggle2 = client.patch("/api/todo/1/toggle")
    assert res_toggle2.status_code == 200
    assert res_toggle2.json()["status"] == "active"

    # Verify active again in GET /api/todo
    res_get3 = client.get("/api/todo")
    data3 = res_get3.json()
    assert len(data3["cyber"]["active"]) == 1
    assert len(data3["cyber"]["completed"]) == 0


def test_remove_todo_keeps_calendar():
    # Add to todo and calendar
    client.post("/api/todo/1")
    client.post("/api/calendar/1")

    # Remove from todo
    res_del = client.delete("/api/todo/1")
    assert res_del.status_code == 200

    # Todo list should be empty
    todo_data = client.get("/api/todo").json()
    assert len(todo_data["cyber"]["active"]) == 0

    # Calendar should still contain opportunity 1
    cal_data = client.get("/api/calendar?month=2026-10").json()
    op_ids = [entry["opportunity_id"] for entry in cal_data["entries"]]
    assert 1 in op_ids


def test_remove_calendar_keeps_todo():
    # Add to todo and calendar
    client.post("/api/todo/1")
    client.post("/api/calendar/1")

    # Remove from calendar
    res_del = client.delete("/api/calendar/1")
    assert res_del.status_code == 200

    # Calendar should be empty
    cal_data = client.get("/api/calendar?month=2026-10").json()
    assert len(cal_data["entries"]) == 0

    # Todo list should still contain opportunity 1
    todo_data = client.get("/api/todo").json()
    assert len(todo_data["cyber"]["active"]) == 1


def test_calendar_shows_item_on_both_dates():
    # Add item 1 (event Oct 20, deadline Oct 12) to calendar
    client.post("/api/calendar/1")

    res_cal = client.get("/api/calendar?month=2026-10")
    assert res_cal.status_code == 200
    entries = res_cal.json()["entries"]

    # Should contain 2 entries for opportunity 1 (one event, one deadline)
    opp1_entries = [e for e in entries if e["opportunity_id"] == 1]
    assert len(opp1_entries) == 2

    kinds = {e["kind"] for e in opp1_entries}
    assert kinds == {"event", "deadline"}

    deadline_entry = next(e for e in opp1_entries if e["kind"] == "deadline")
    event_entry = next(e for e in opp1_entries if e["kind"] == "event")

    assert deadline_entry["date"] == "2026-10-12T10:00:00Z"
    assert event_entry["date"] == "2026-10-20T10:00:00Z"


def test_tag_color_change_does_not_modify_opportunity():
    # Fetch tags
    tags = client.get("/api/tags").json()
    tag_id = tags[0]["id"]

    # Modify tag color
    new_color = "#123456"
    res_patch = client.patch(f"/api/tags/{tag_id}", json={"color": new_color})
    assert res_patch.status_code == 200
    assert res_patch.json()["color"] == new_color

    # Verify opportunity is unaffected
    res_opp = client.get("/api/opportunities")
    assert res_opp.status_code == 200
    opps = res_opp.json()["items"]
    opp1 = next(o for o in opps if o["id"] == 1)
    assert opp1["title"] == "Cyber Hackathon"
    assert opp1["domain"] == "cyber"
