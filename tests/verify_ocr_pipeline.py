import os
import sys
import asyncio
import hashlib
import json
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Force Mock OCR for testing
os.environ["MOCK_OCR"] = "true"

from core.ocr.router import OCRRouter
from core.ocr.manga_ocr import MangaOCRProvider
from core.ocr.paddle_ocr import PaddleOCRProvider
from core.utils.db import execute_query, execute_batch, init_db

async def main():
    # Set stdout to handle UTF-8 printing
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    
    print("=== Verification of DRS v3 OCR Pipeline ===")
    
    # 1. Initialize DB schema (ensure SQLite tables exist locally)
    await init_db()
    print("✓ Local SQLite DB initialized.")

    # 2. Test Router Dispatching
    print("\n--- 1. Testing OCR Router ---")
    provider_ja = OCRRouter.get_provider("ja")
    provider_en = OCRRouter.get_provider("en")
    provider_vi = OCRRouter.get_provider("vi")
    
    assert isinstance(provider_ja, MangaOCRProvider), "JA should route to MangaOCRProvider"
    assert isinstance(provider_en, PaddleOCRProvider), "EN should route to PaddleOCRProvider"
    assert isinstance(provider_vi, PaddleOCRProvider), "VI should route to PaddleOCRProvider"
    print("✓ OCR Router correctly dispatches providers based on language.")

    # 3. Test Providers in Mock Mode
    print("\n--- 2. Testing Providers (Mock Mode) ---")
    # We pass a dummy path since it will fallback to mock
    blocks_ja = await provider_ja.extract("dummy_page.png")
    blocks_en = await provider_en.extract("dummy_page.png")
    
    print(f"  MangaOCR mock blocks count: {len(blocks_ja)}")
    for idx, b in enumerate(blocks_ja):
        print(f"    [{idx}] Text: {b.text} | Bbox: {b.bbox} | Conf: {b.confidence}")
        assert len(b.bbox) == 4, "Bbox must contain 4 coordinates"
        assert all(0.0 <= c <= 1.0 for c in b.bbox), "Bbox coordinates must be normalized (0.0 to 1.0)"

    print(f"  PaddleOCR mock blocks count: {len(blocks_en)}")
    for idx, b in enumerate(blocks_en):
        print(f"    [{idx}] Text: {b.text} | Bbox: {b.bbox} | Conf: {b.confidence}")
        assert len(b.bbox) == 4, "Bbox must contain 4 coordinates"
        assert all(0.0 <= c <= 1.0 for c in b.bbox), "Bbox coordinates must be normalized (0.0 to 1.0)"
    
    print("✓ OCR Providers return valid normalized OCRBlock data.")

    # 4. Test Coordinate Hashing (Segment ID Generation)
    print("\n--- 3. Testing Segment ID Generation (SHA1 coordinate hash) ---")
    asset_id = "page001"
    for b in blocks_ja:
        coord_str = "".join(f"{round(c, 3):.3f}" for c in b.bbox)
        h = hashlib.sha1(coord_str.encode('utf-8')).hexdigest()[:6]
        segment_id = f"{asset_id}_{h}"
        print(f"    Bbox: {b.bbox} -> Rounded Str: {coord_str} -> Segment ID: {segment_id}")
        assert len(segment_id) == len(asset_id) + 1 + 6, "Segment ID format must be asset_id_xxxxxx"
        
    print("✓ Segment ID coordinate hashing works deterministically.")

    # 5. Test Database Operations (Delete and Bulk Insert)
    print("\n--- 4. Testing D1 Segments Import & Overwrite Transaction ---")
    project_id = "test_ocr_project"
    doc_id = "test_doc_001"
    
    # Pre-register dummy asset in database
    created_at = "2026-06-10T12:00:00Z"
    await execute_query(
        """
        INSERT OR REPLACE INTO assets (
            asset_id, project_id, doc_id, asset_type, mime_type, r2_path, checksum, width, height, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ["page001.png", project_id, doc_id, "manga_page", "image/png", "projects/test/docs/page001.png", "dummychecksum", 1000, 1500, created_at]
    )
    print("✓ Dummy asset registered in 'assets' table.")
    
    # Simulate first OCR run
    db_statements_1 = [
        ("DELETE FROM segments WHERE project_id = ? AND doc_id = ?", [project_id, doc_id])
    ]
    for b in blocks_ja:
        coord_str = "".join(f"{round(c, 3):.3f}" for c in b.bbox)
        h = hashlib.sha1(coord_str.encode('utf-8')).hexdigest()[:6]
        segment_id = f"page001_{h}"
        db_statements_1.append((
            """
            INSERT INTO segments (
                project_id, doc_id, segment_id, segment_type, source_text, target_text, asset_id, bbox
            ) VALUES (?, ?, ?, 'bubble', ?, '', ?, ?)
            """,
            [project_id, doc_id, segment_id, b.text, "page001.png", json.dumps(b.bbox)]
        ))
    
    await execute_batch(db_statements_1)
    
    # Verify records exist in DB
    rows = await execute_query("SELECT segment_id, source_text, bbox FROM segments WHERE project_id = ? AND doc_id = ?", [project_id, doc_id])
    print(f"  Inserted segments count: {len(rows)}")
    assert len(rows) == len(blocks_ja), "D1 segments count should match OCR blocks count"
    
    # Simulate OCR re-run (should clear old and write new)
    db_statements_2 = [
        ("DELETE FROM segments WHERE project_id = ? AND doc_id = ?", [project_id, doc_id])
    ]
    # We will simulate re-running with PaddleOCR blocks
    for b in blocks_en:
        coord_str = "".join(f"{round(c, 3):.3f}" for c in b.bbox)
        h = hashlib.sha1(coord_str.encode('utf-8')).hexdigest()[:6]
        segment_id = f"page001_{h}"
        db_statements_2.append((
            """
            INSERT INTO segments (
                project_id, doc_id, segment_id, segment_type, source_text, target_text, asset_id, bbox
            ) VALUES (?, ?, ?, 'bubble', ?, '', ?, ?)
            """,
            [project_id, doc_id, segment_id, b.text, "page001.png", json.dumps(b.bbox)]
        ))
        
    await execute_batch(db_statements_2)
    
    # Verify old records are removed and new ones are inserted
    rows_after = await execute_query("SELECT segment_id, source_text FROM segments WHERE project_id = ? AND doc_id = ?", [project_id, doc_id])
    print(f"  After re-run segments count: {len(rows_after)}")
    assert len(rows_after) == len(blocks_en), "Old segments must be overwritten by new segments"
    for r in rows_after:
        print(f"    Segment: {r['segment_id']} | Text: {r['source_text']}")
        
    # Cleanup test records
    await execute_query("DELETE FROM segments WHERE project_id = ?", [project_id])
    await execute_query("DELETE FROM assets WHERE project_id = ?", [project_id])
    print("✓ Cleanup completed.")
    
    print("\n=== All OCR Pipeline verification steps PASSED successfully! ===")

if __name__ == "__main__":
    asyncio.run(main())
