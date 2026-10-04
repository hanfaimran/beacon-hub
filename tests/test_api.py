import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import CREATE_TABLES_SQL, SEED_TAGS, get_db_connection

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "test_beacon_hub.db")
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
    
    # Seed 15 opportunities
    # 5 with future deadline (ascending), 5 with past deadline, 5 with null deadline
    opportunities = []
    # 5 Future: 2026-10-10, 2026-10-11, 2026-10-12, 2026-10-13, 2026-10-14
    for i in range(1, 6):
        opportunities.append((
            f"Future Opp {i}",
            f"https://example.com/future/{i}",
            "cyber",
            "event",
            "virtual",
            f"2026-10-1{i}T10:00:00Z"
        ))
    # 5 Null deadline
    for i in range(1, 6):
        opportunities.append((
            f"Null Deadline Opp {i}",
            f"https://example.com/null/{i}",
            "cyber",
            "event",
            "virtual",
            None
        ))
    # 5 Past: 2025-01-01 to 2025-01-05
    for i in range(1, 6):
        opportunities.append((
            f"Past Opp {i}",
            f"https://example.com/past/{i}",
            "cyber",
            "event",
            "virtual",
            f"2025-01-0{i}T10:00:00Z"
        ))
        
    for title, url, domain, cat, mode, dline in opportunities:
        cursor.execute(
            """INSERT INTO opportunities (title, url, domain, category, mode, deadline_utc)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, url, domain, cat, mode, dline)
        )
    conn.commit()
    conn.close()

def test_get_opportunities_pagination_and_order():
    # Page 1, page_size 10
    response = client.get("/api/opportunities?domain=cyber&page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 10
    assert data["total_pages"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 10
    
    # Check ordering: 5 future deadlines ascending followed by 5 null deadlines
    items = data["items"]
    deadlines = [item["deadline_utc"] for item in items]
    assert deadlines[:5] == [
        "2026-10-11T10:00:00Z",
        "2026-10-12T10:00:00Z",
        "2026-10-13T10:00:00Z",
        "2026-10-14T10:00:00Z",
        "2026-10-15T10:00:00Z"
    ] or deadlines[:5] == [
        "2026-10-11T10:00:00Z",
        "2026-10-12T10:00:00Z",
        "2026-10-13T10:00:00Z",
        "2026-10-14T10:00:00Z",
        "2026-10-15T10:00:00Z"
    ]
    # Check that past deadlines are excluded
    for d in deadlines[:5]:
        assert d >= "2026-10-04"
    for d in deadlines[5:]:
        assert d is None

def test_pagination_pages():
    # Page size 6 -> Total 10 valid items -> Page 1 has 6, Page 2 has 4
    res1 = client.get("/api/opportunities?domain=cyber&page=1&page_size=6")
    assert res1.status_code == 200
    d1 = res1.json()
    assert len(d1["items"]) == 6
    assert d1["total_pages"] == 2
    assert d1["page"] == 1
    
    res2 = client.get("/api/opportunities?domain=cyber&page=2&page_size=6")
    assert res2.status_code == 200
    d2 = res2.json()
    assert len(d2["items"]) == 4
    assert d2["page"] == 2
