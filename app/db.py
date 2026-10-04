import os
import sqlite3
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

def get_db_connection():
    if not DATABASE_URL:
        conn = sqlite3.connect("beacon_hub.db")
        conn.row_factory = sqlite3.Row
        return conn
    else:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    domain TEXT CHECK(domain IN ('cyber', 'ai', 'cloud')),
    category TEXT CHECK(category IN ('event', 'hackathon', 'course', 'internship', 'certification', 'other')),
    mode TEXT CHECK(mode IN ('virtual', 'in_person', 'hybrid') OR mode IS NULL),
    organization TEXT,
    location TEXT,
    about TEXT,
    event_date_utc TEXT,
    deadline_utc TEXT,
    rewards TEXT,
    entry_fee TEXT,
    source_domain TEXT,
    verified INTEGER DEFAULT 0,
    dates_missing INTEGER DEFAULT 0,
    source_text_snippet TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS todo_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER UNIQUE NOT NULL,
    status TEXT CHECK(status IN ('active', 'done')) DEFAULT 'active',
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS calendar_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    is_default INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS calendar_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER UNIQUE NOT NULL,
    tag_id INTEGER,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES calendar_tags(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS searches_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    ts TEXT DEFAULT CURRENT_TIMESTAMP,
    cached INTEGER DEFAULT 0
);
"""

SEED_TAGS = [
    ("Cybersecurity", "#EF4444", 1),
    ("AI", "#8B5CF6", 1),
    ("Cloud", "#3B82F6", 1)
]

def init_db():
    if not DATABASE_URL:
        db_path = "beacon_hub.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executescript(CREATE_TABLES_SQL)
        
        # Migration for dates_missing column
        cursor.execute("PRAGMA table_info(opportunities)")
        columns = [column[1] for column in cursor.fetchall()]
        if "dates_missing" not in columns:
            cursor.execute("ALTER TABLE opportunities ADD COLUMN dates_missing INTEGER DEFAULT 0")
        
        cursor.execute("SELECT COUNT(*) FROM calendar_tags")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO calendar_tags (name, color, is_default) VALUES (?, ?, ?)",
                SEED_TAGS
            )
        conn.commit()
        conn.close()
    else:
        import psycopg
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                pg_sql = CREATE_TABLES_SQL.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
                pg_sql = pg_sql.replace("INTEGER DEFAULT 0", "BOOLEAN DEFAULT FALSE")
                pg_sql = pg_sql.replace("INTEGER DEFAULT 1", "BOOLEAN DEFAULT TRUE")
                cursor.execute(pg_sql)
                
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='opportunities' AND column_name='dates_missing'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE opportunities ADD COLUMN dates_missing BOOLEAN DEFAULT FALSE")
                
                cursor.execute("SELECT COUNT(*) FROM calendar_tags")
                if cursor.fetchone()[0] == 0:
                    cursor.executemany(
                        "INSERT INTO calendar_tags (name, color, is_default) VALUES (%s, %s, %s)",
                        [(t[0], t[1], True if t[2] else False) for t in SEED_TAGS]
                    )
                conn.commit()


if __name__ == "__main__":
    init_db()
