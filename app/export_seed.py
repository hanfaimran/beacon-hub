"""
Dump the opportunities table to seed/opportunities.json.
Run as: python -m app.export_seed
No secrets, no todo/calendar rows are exported.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

# Resolve seed dir relative to project root (parent of this file's package)
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
SEED_DIR = _ROOT / "seed"
SEED_FILE = SEED_DIR / "opportunities.json"

COLUMNS = [
    "title", "url", "domain", "category", "mode", "organization", "location",
    "about", "event_date_utc", "deadline_utc", "rewards", "entry_fee",
    "source_domain", "verified", "dates_missing", "source_text_snippet", "created_at",
]


def main():
    from app.db import DATABASE_URL, get_db_connection

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        col_list = ", ".join(COLUMNS)
        cursor.execute(f"SELECT {col_list} FROM opportunities ORDER BY id ASC")
        rows = cursor.fetchall()
    finally:
        conn.close()

    records = []
    for row in rows:
        if isinstance(row, dict):
            record = {c: row[c] for c in COLUMNS}
        else:
            record = dict(zip(COLUMNS, row))
        # Normalise booleans to plain int so JSON round-trips cleanly
        record["verified"] = 1 if record.get("verified") else 0
        record["dates_missing"] = 1 if record.get("dates_missing") else 0
        records.append(record)

    SEED_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEED_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(records)} opportunities to {SEED_FILE}")


if __name__ == "__main__":
    main()
