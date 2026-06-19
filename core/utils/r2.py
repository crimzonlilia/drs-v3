import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Cloudflare R2 Credentials
CF_R2_ACCOUNT_ID = os.getenv("CF_R2_ACCOUNT_ID")
CF_R2_ACCESS_KEY_ID = os.getenv("CF_R2_ACCESS_KEY_ID")
CF_R2_SECRET_ACCESS_KEY = os.getenv("CF_R2_SECRET_ACCESS_KEY")
CF_R2_BUCKET = os.getenv("CF_R2_BUCKET")

LOCAL_R2_ROOT = Path("memory_store/r2_mock")

# Try to import boto3 for actual R2 S3 compatibility
BOTO3_AVAILABLE = False
try:
    import boto3
    from botocore.client import Config
    BOTO3_AVAILABLE = True
except ImportError:
    pass

def is_cloud_mode() -> bool:
    return bool(
        BOTO3_AVAILABLE 
        and CF_R2_ACCOUNT_ID 
        and CF_R2_ACCESS_KEY_ID 
        and CF_R2_SECRET_ACCESS_KEY 
        and CF_R2_BUCKET
    )

_S3_CLIENT = None

def _get_s3_client():
    global _S3_CLIENT
    if _S3_CLIENT is None:
        endpoint_url = f"https://{CF_R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        _S3_CLIENT = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=CF_R2_ACCESS_KEY_ID,
            aws_secret_access_key=CF_R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto"
        )
    return _S3_CLIENT

# ------------------------------------------------------------------ #
# D1 Database Fallback for file storage                              #
# Allows persistence in deployed environments without adding a card   #
# ------------------------------------------------------------------ #

def _run_db_query_sync(sql: str, params: list = None) -> list:
    import sqlite3
    import httpx
    
    if params is None:
        params = []
        
    cf_acc = os.getenv("CF_ACCOUNT_ID")
    cf_db = os.getenv("CF_DATABASE_ID")
    cf_token = os.getenv("CF_API_TOKEN")
    
    norm_params = [1 if isinstance(p, bool) else p for p in params]
    
    if cf_acc and cf_db and cf_token:
        url = f"https://api.cloudflare.com/client/v4/accounts/{cf_acc}/d1/database/{cf_db}/query"
        headers = {
            "Authorization": f"Bearer {cf_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "sql": sql,
            "params": norm_params
        }
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=15.0)
            if resp.status_code == 200:
                result_data = resp.json()
                if result_data.get("success"):
                    results = result_data.get("result", [])
                    if results and isinstance(results, list):
                        return [dict(r) for r in results[0].get("results", [])]
        except Exception:
            pass
    else:
        db_path = Path("memory_store/d1_mock.db")
        if not db_path.exists():
            return []
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, norm_params)
            if sql.strip().upper().startswith(("SELECT", "PRAGMA")):
                rows = cursor.fetchall()
                res = [dict(r) for r in rows]
            else:
                conn.commit()
                res = []
            conn.close()
            return res
        except Exception:
            pass
    return []

# ------------------------------------------------------------------ #
# Core Storage Interface                                               #
# ------------------------------------------------------------------ #

_MEMORY_CACHE = {}  # key -> (content, timestamp)

def read_text(key: str) -> Optional[str]:
    key = key.lstrip("/")
    
    is_memory_file = "/memory/" in key
    if is_memory_file:
        import time
        now = time.time()
        if key in _MEMORY_CACHE:
            cached_content, timestamp = _MEMORY_CACHE[key]
            if now - timestamp < 5.0:  # 5 seconds TTL
                return cached_content

    content = None
    if is_cloud_mode():
        try:
            s3 = _get_s3_client()
            response = s3.get_object(Bucket=CF_R2_BUCKET, Key=key)
            content = response["Body"].read().decode("utf-8")
        except Exception:
            pass
            
    if content is None:
        # Try D1 database fallback first
        try:
            rows = _run_db_query_sync("SELECT content_text FROM r2_emulated_files WHERE key = ?", [key])
            if rows and rows[0]["content_text"] is not None:
                content = rows[0]["content_text"]
        except Exception:
            pass
        
    if content is None:
        # Local filesystem fallback
        file_path = LOCAL_R2_ROOT / key
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                pass

    if is_memory_file and content is not None:
        import time
        _MEMORY_CACHE[key] = (content, time.time())
        
    return content

def write_text(key: str, text: str) -> None:
    key = key.lstrip("/")
    if "/memory/" in key:
        _MEMORY_CACHE.pop(key, None)
    
    if is_cloud_mode():
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=CF_R2_BUCKET,
            Key=key,
            Body=text.encode("utf-8"),
            ContentType="text/plain"
        )
        return

    # Write to D1 database fallback
    try:
        updated_at = datetime.now().isoformat()
        _run_db_query_sync(
            "INSERT OR REPLACE INTO r2_emulated_files (key, content_text, mime_type, updated_at) VALUES (?, ?, ?, ?)",
            [key, text, "text/plain", updated_at]
        )
    except Exception:
        pass

    # Write to local file as additional backup
    file_path = LOCAL_R2_ROOT / key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")

def read_binary(key: str) -> Optional[bytes]:
    key = key.lstrip("/")
    
    if is_cloud_mode():
        try:
            s3 = _get_s3_client()
            response = s3.get_object(Bucket=CF_R2_BUCKET, Key=key)
            return response["Body"].read()
        except Exception:
            return None

    # Try D1 database fallback
    try:
        rows = _run_db_query_sync("SELECT content_blob FROM r2_emulated_files WHERE key = ?", [key])
        if rows and rows[0]["content_blob"] is not None:
            return rows[0]["content_blob"]
    except Exception:
        pass

    # Local filesystem fallback
    file_path = LOCAL_R2_ROOT / key
    if file_path.exists():
        try:
            return file_path.read_bytes()
        except Exception:
            pass
    return None

def write_binary(key: str, data: bytes, mime_type: str = "application/octet-stream") -> None:
    key = key.lstrip("/")
    
    if is_cloud_mode():
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=CF_R2_BUCKET,
            Key=key,
            Body=data,
            ContentType=mime_type
        )
        return

    # Write to D1 database fallback
    try:
        updated_at = datetime.now().isoformat()
        _run_db_query_sync(
            "INSERT OR REPLACE INTO r2_emulated_files (key, content_blob, mime_type, updated_at) VALUES (?, ?, ?, ?)",
            [key, data, mime_type, updated_at]
        )
    except Exception:
        pass

    # Local filesystem backup
    file_path = LOCAL_R2_ROOT / key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(data)

def delete_file(key: str) -> bool:
    key = key.lstrip("/")
    if "/memory/" in key:
        _MEMORY_CACHE.pop(key, None)
        
    if is_cloud_mode():
        try:
            s3 = _get_s3_client()
            s3.delete_object(Bucket=CF_R2_BUCKET, Key=key)
            return True
        except Exception:
            return False

    # Delete from D1 fallback
    db_success = False
    try:
        _run_db_query_sync("DELETE FROM r2_emulated_files WHERE key = ?", [key])
        db_success = True
    except Exception:
        pass

    # Delete from local file
    file_path = LOCAL_R2_ROOT / key
    file_success = False
    if file_path.exists():
        try:
            file_path.unlink()
            file_success = True
        except Exception:
            pass
            
    return db_success or file_success

def list_files(prefix: str) -> List[str]:
    prefix = prefix.lstrip("/")
    
    if is_cloud_mode():
        try:
            s3 = _get_s3_client()
            response = s3.list_objects_v2(Bucket=CF_R2_BUCKET, Prefix=prefix)
            keys = []
            for obj in response.get("Contents", []):
                keys.append(obj["Key"])
            return keys
        except Exception:
            return []

    # Get from D1 database fallback
    keys_set = set()
    try:
        rows = _run_db_query_sync("SELECT key FROM r2_emulated_files WHERE key LIKE ?", [f"{prefix}%"])
        for r in rows:
            keys_set.add(r["key"])
    except Exception:
        pass

    # Get from local filesystem
    target_dir = LOCAL_R2_ROOT / prefix
    if not target_dir.exists():
        search_dir = LOCAL_R2_ROOT
        glob_pattern = f"{prefix}*"
    else:
        search_dir = target_dir
        glob_pattern = "**/*"
        
    if search_dir.exists():
        for p in search_dir.glob(glob_pattern):
            if p.is_file():
                rel_path = p.relative_to(LOCAL_R2_ROOT)
                keys_set.add(str(rel_path).replace("\\", "/"))
                
    return sorted(list(keys_set))
