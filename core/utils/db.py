import os
import sqlite3
import json
import httpx
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cloudflare D1 Credentials
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_DATABASE_ID = os.getenv("CF_DATABASE_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")

LOCAL_DB_PATH = Path("memory_store/d1_mock.db")

def is_cloud_mode() -> bool:
    return bool(CF_ACCOUNT_ID and CF_DATABASE_ID and CF_API_TOKEN)

def get_local_connection() -> sqlite3.Connection:
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(LOCAL_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

async def execute_query(sql: str, params: List[Any] = None) -> List[Dict[str, Any]]:
    """
    Executes a SQL query against Cloudflare D1 (if credentials are set)
    or the local SQLite database.
    Returns a list of dicts representing rows.
    """
    if params is None:
        params = []
    
    # Normalize params (convert boolean to int for SQLite compatibility)
    norm_params = []
    for p in params:
        if isinstance(p, bool):
            norm_params.append(1 if p else 0)
        else:
            norm_params.append(p)

    if is_cloud_mode():
        url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{CF_DATABASE_ID}/query"
        headers = {
            "Authorization": f"Bearer {CF_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "sql": sql,
            "params": norm_params
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result_data = response.json()
            if not result_data.get("success"):
                errors = result_data.get("errors", [])
                err_msg = ", ".join([e.get("message", "") for e in errors])
                raise RuntimeError(f"Cloudflare D1 query failed: {err_msg}")
            
            # Cloudflare D1 response payload format:
            # result: [ { "results": [ { ...rows... } ], "success": true } ]
            results = result_data.get("result", [])
            if results and isinstance(results, list):
                # The first item contains results
                rows = results[0].get("results", [])
                return [dict(r) for r in rows]
            return []
    else:
        # Local Mode using sqlite3
        conn = get_local_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, norm_params)
            if sql.strip().upper().startswith(("SELECT", "PRAGMA")):
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            else:
                conn.commit()
                return []
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

async def execute_batch(statements: List[Tuple[str, List[Any]]]) -> None:
    """
    Executes multiple SQL statements in a single batch.
    """
    if is_cloud_mode():
        url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{CF_DATABASE_ID}/query"
        headers = {
            "Authorization": f"Bearer {CF_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            for sql, params in statements:
                norm_params = [1 if isinstance(p, bool) else p for p in (params or [])]
                payload = {
                    "sql": sql,
                    "params": norm_params
                }
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result_data = response.json()
                if not result_data.get("success"):
                    errors = result_data.get("errors", [])
                    err_msg = ", ".join([e.get("message", "") for e in errors])
                    raise RuntimeError(f"Cloudflare D1 batch query failed: {err_msg}")
    else:
        conn = get_local_connection()
        cursor = conn.cursor()
        try:
            for sql, params in statements:
                norm_params = [1 if isinstance(p, bool) else p for p in (params or [])]
                cursor.execute(sql, norm_params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

async def init_db() -> None:
    """
    Runs schema migrations on startup to ensure tables exist.
    """
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        username         TEXT NOT NULL UNIQUE,
        hashed_password  TEXT NOT NULL,
        email            TEXT,
        created_at       TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS projects (
        id            TEXT PRIMARY KEY,
        display_name  TEXT NOT NULL,
        description   TEXT,
        source_lang   TEXT NOT NULL,
        target_lang   TEXT NOT NULL,
        content_type  TEXT NOT NULL,
        created_at    TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS project_members (
        user_id     INTEGER NOT NULL REFERENCES users(id),
        project_id  TEXT NOT NULL REFERENCES projects(id),
        role        TEXT NOT NULL CHECK(role IN ('owner','editor','viewer')),
        joined_at   TEXT NOT NULL,
        PRIMARY KEY (user_id, project_id)
    );

    CREATE TABLE IF NOT EXISTS segments (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id    TEXT NOT NULL,
        doc_id        TEXT NOT NULL,
        segment_id    TEXT NOT NULL,
        segment_type  TEXT NOT NULL DEFAULT 'paragraph',
        source_text   TEXT NOT NULL,
        target_text   TEXT,
        asset_id      TEXT,
        bbox          TEXT,
        approved_by   INTEGER REFERENCES users(id),
        approved_at   TEXT,
        UNIQUE(project_id, doc_id, segment_id)
    );

    CREATE TABLE IF NOT EXISTS assets (
        asset_id    TEXT PRIMARY KEY,
        project_id  TEXT NOT NULL,
        doc_id      TEXT NOT NULL,
        asset_type  TEXT NOT NULL,
        mime_type   TEXT NOT NULL,
        r2_path     TEXT NOT NULL,
        checksum    TEXT NOT NULL,
        width       INTEGER,
        height      INTEGER,
        created_at  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS r2_emulated_files (
        key          TEXT PRIMARY KEY,
        content_text TEXT,
        content_blob BLOB,
        mime_type    TEXT,
        updated_at   TEXT
    );
    """
    
    # Split schema by semicolon to run individually on SQLite/D1
    statements = []
    for stmt in schema.split(";"):
        clean_stmt = stmt.strip()
        if clean_stmt:
            statements.append((clean_stmt, []))
            
    await execute_batch(statements)
    
    # Attempt to gracefully add description column for backward compatibility
    try:
        await execute_batch([("ALTER TABLE projects ADD COLUMN description TEXT;", [])])
    except Exception:
        pass  # Column likely already exists
        
    # Create indexes
    idx_statements = [
        ("CREATE INDEX IF NOT EXISTS idx_segments_doc ON segments(project_id, doc_id);", []),
        ("CREATE INDEX IF NOT EXISTS idx_assets_doc ON assets(project_id, doc_id);", []),
    ]
    await execute_batch(idx_statements)
