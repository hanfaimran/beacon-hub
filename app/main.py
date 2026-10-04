from fastapi import FastAPI, Query
from typing import Optional, Dict, Any, List
import math
import logging
from datetime import datetime, timezone
from app.db import get_db_connection, DATABASE_URL

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(title="Beacon Hub API")

@app.get("/api/opportunities")
def get_opportunities(
    domain: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
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
            "total_pages": total_pages
        }
    finally:
        conn.close()
