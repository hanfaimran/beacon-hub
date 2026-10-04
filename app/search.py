import os
import hashlib
import json
import sqlite3
import logging
from typing import List, Dict, Any
import httpx
from dotenv import load_dotenv

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
CACHE_DIR = "cache"

def get_db_connection():
    if not DATABASE_URL:
        conn = sqlite3.connect("beacon_hub.db")
        conn.row_factory = sqlite3.Row
        return conn
    else:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def get_search_count() -> int:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if not DATABASE_URL:
            cursor.execute("SELECT COUNT(*) FROM searches_log WHERE cached = 0")
            count = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT COUNT(*) FROM searches_log WHERE cached = FALSE")
            res = cursor.fetchone()
            count = res["count"] if isinstance(res, dict) else res[0]
        return count
    finally:
        conn.close()

def _log_search(query: str, cached: bool):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if not DATABASE_URL:
            cursor.execute("INSERT INTO searches_log (query, cached) VALUES (?, ?)", (query, 1 if cached else 0))
        else:
            cursor.execute("INSERT INTO searches_log (query, cached) VALUES (%s, %s)", (query, cached))
        conn.commit()
    finally:
        conn.close()

def search_serpapi(query: str) -> List[Dict[str, Any]]:
    os.makedirs(CACHE_DIR, exist_ok=True)
    query_hash = hashlib.sha1(query.encode("utf-8")).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{query_hash}.json")

    if os.path.exists(cache_path):
        _log_search(query, cached=True)
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        if get_search_count() >= 200:
            raise RuntimeError("SerpApi search limit reached (200 non-cached searches).")
        
        if not SERPAPI_KEY:
            raise ValueError("SERPAPI_KEY is not set.")

        params = {
            "q": query,
            "api_key": SERPAPI_KEY,
            "engine": "google"
        }
        
        response = httpx.get("https://serpapi.com/search", params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        _log_search(query, cached=False)

    results = []
    for item in data.get("organic_results", []):
        results.append({
            "title": item.get("title"),
            "url": item.get("link"),
            "snippet": item.get("snippet")
        })

    return results
