import os
import sys
import json
import zipfile
import io
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from server.main import app
from server.auth import create_access_token
from core.utils.db import execute_query
from core.utils.r2 import write_text, read_text

def test_flow():
    # Set sys.stdout to handle UTF-8 print
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    print("Starting verification of DRS v3 Export and Document endpoints...")
    
    # 1. Initialize TestClient
    client = TestClient(app)
    
    # Generate mock JWT token for testing
    token = create_access_token(data={"sub": "admin", "id": 1, "role": "owner"})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Seed DB with a project member record
    # Note: Since database might already be seeded, we insert/replace
    import sqlite3
    db_path = project_root / "memory_store" / "d1_mock.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, username, hashed_password, created_at) VALUES (1, 'admin', 'mock_hash', '2026-06-06')")
    cursor.execute("INSERT OR IGNORE INTO projects (id, display_name, source_lang, target_lang, content_type, created_at) VALUES ('demo_project', 'Demo', 'ja', 'vi', 'general', '2026-06-06')")
    cursor.execute("INSERT OR REPLACE INTO project_members (user_id, project_id, role, joined_at) VALUES (1, 'demo_project', 'owner', '2026-06-06')")
    conn.commit()
    conn.close()

    # Seed mock document in R2
    doc_id = "doc_test_export"
    doc_prefix = f"projects/demo_project/docs/{doc_id}/"
    write_text(f"{doc_prefix}draft.md", "Dòng nháp của tài liệu kiểm thử.")
    
    # 2. Test export endpoint - TXT format
    print("\nTesting export to TXT...")
    resp = client.post(
        f"/api/docs/{doc_id}/export",
        json={"format": "txt", "project_id": "demo_project"},
        headers=headers
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "Dòng nháp của tài liệu kiểm thử." in resp.text
    print("TXT Export successful!")

    # 3. Test export endpoint - DOCX format
    print("\nTesting export to DOCX...")
    resp = client.post(
        f"/api/docs/{doc_id}/export",
        json={"format": "docx", "project_id": "demo_project"},
        headers=headers
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    # Verification of headers
    assert "vnd.openxmlformats-officedocument.wordprocessingml.document" in resp.headers["content-type"]
    print("DOCX Export successful!")

    # 4. Test export endpoint - ZIP format
    print("\nTesting export to ZIP...")
    resp = client.post(
        f"/api/docs/{doc_id}/export",
        json={"format": "zip", "project_id": "demo_project"},
        headers=headers
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    
    # Read zip bytes and check content
    zip_bytes = io.BytesIO(resp.content)
    with zipfile.ZipFile(zip_bytes, "r") as z:
        file_list = z.namelist()
        print(f"Zip files: {file_list}")
        assert f"{doc_id}_translation.txt" in file_list
        assert "page_001_overlay.png" in file_list
    print("ZIP Export successful!")

    # 5. Test Assets Upload endpoint
    print("\nTesting Assets Upload mock...")
    files = [
        ("files", ("page_001.png", b"\x89PNGmockbytes", "image/png")),
        ("files", ("page_002.png", b"\x89PNGmockbytes2", "image/png"))
    ]
    resp = client.post(
        f"/api/docs/{doc_id}/assets/upload?project_id=demo_project",
        files=files,
        headers=headers
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    resp_data = resp.json()
    assert resp_data["status"] == "success"
    assert "page_001.png" in resp_data["assets"]
    print("Assets Upload successful!")

    # 6. Test OCR Run endpoint
    print("\nTesting OCR Run mock...")
    resp = client.post(
        f"/api/docs/{doc_id}/ocr/run?project_id=demo_project",
        headers=headers
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    resp_data = resp.json()
    assert resp_data["status"] == "success"
    assert resp_data["detected_bubbles"] > 0
    print("OCR Run successful!")

    # 7. Test Dual routing compatibility for projects/docs
    print("\nTesting projects docs/chapters list dual routing...")
    resp_docs = client.get("/api/projects/demo_project/docs", headers=headers)
    resp_chapters = client.get("/api/projects/demo_project/chapters", headers=headers)
    assert resp_docs.status_code == 200
    assert resp_chapters.status_code == 200
    assert resp_docs.json() == resp_chapters.json()
    print("Dual routing check successful!")

    print("\nAll verifications in tests/verify_export_and_docs.py completed successfully!")

if __name__ == "__main__":
    test_flow()
