import os
import io
import sys
import time
import httpx
import asyncio
from PIL import Image

API_URL = "http://127.0.0.1:8000"

async def test_image_translation_flow():
    # Set stdout to handle UTF-8 printing
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    print("=== Starting E2E Image Translation Pipeline Test ===")
    
    username = f"e2e_test_user_{int(time.time())}"
    password = "securepassword123"
    project_id = f"e2e_proj_{int(time.time())}"
    doc_id = "test_doc_001"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Register User
        print(f"\n1. Registering user: {username}")
        resp = await client.post(
            f"{API_URL}/api/auth/register",
            json={"username": username, "password": password, "email": f"{username}@example.com"}
        )
        if resp.status_code != 201:
            print(f"Failed to register user: {resp.status_code} - {resp.text}")
            return False
        print("✓ User registered successfully.")

        # 2. Login User
        print("\n2. Logging in to retrieve JWT access token")
        resp = await client.post(
            f"{API_URL}/api/auth/login",
            data={"username": username, "password": password}
        )
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} - {resp.text}")
            return False
        
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✓ Login successful. JWT token received.")

        # 3. Create Project
        print(f"\n3. Creating project: {project_id}")
        resp = await client.post(
            f"{API_URL}/api/projects",
            headers=headers,
            json={
                "project_id": project_id,
                "description": "E2E Image Translation Test",
                "source_lang": "ja",
                "target_lang": "vi",
                "content_type": "manga",
                "tone_note": "Friendly tone"
            }
        )
        if resp.status_code != 200:
            print(f"Project creation failed: {resp.status_code} - {resp.text}")
            return False
        print("✓ Project created successfully.")

        # 4. Generate Dynamically a Test PNG Image
        print("\n4. Generating test PNG image in-memory")
        img = Image.new('RGB', (200, 200), color='white')
        
        # Optional: Add text to image to test OCR if API behaves normally
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "ハローワールド", fill=(0, 0, 0)) # "Hello World" in Japanese
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()
        
        # 5. Upload Image Asset
        filename = "test_page_01.png"
        print(f"\n5. Uploading asset: {filename}")
        files = {
            "files": (filename, img_data, "image/png")
        }
        resp = await client.post(
            f"{API_URL}/api/docs/{doc_id}/assets/upload?project_id={project_id}",
            headers=headers,
            files=files
        )
        if resp.status_code != 200:
            print(f"Upload failed: {resp.status_code} - {resp.text}")
            return False
        print("✓ Image asset uploaded and registered.")

        # 6. Trigger Translation Image Pipeline
        print(f"\n6. Triggering translation for asset: {filename}")
        resp = await client.post(
            f"{API_URL}/api/docs/{doc_id}/translate-image",
            headers=headers,
            json={
                "project_id": project_id,
                "asset_id": filename,
                "source_lang": "ja",
                "target_lang": "vi"
            }
        )
        if resp.status_code != 200:
            print(f"Translation pipeline trigger failed: {resp.status_code} - {resp.text}")
            return False
        
        session_id = resp.json()["session_id"]
        print(f"✓ Translation pipeline started. Session ID: {session_id}")

        # 7. Poll session status via /resume endpoint to check progress
        print("\n7. Polling background translation status...")
        max_attempts = 15
        pipeline_done = False
        for attempt in range(max_attempts):
            await asyncio.sleep(4.0)
            
            # Fetch session state
            session_resp = await client.post(
                f"{API_URL}/api/translation/session/{session_id}/resume?project_id={project_id}&doc_id={doc_id}",
                headers=headers
            )
            if session_resp.status_code == 200:
                session_data = session_resp.json()
                pipeline_status = session_data.get("pipeline_status", {})
                pipeline_error = session_data.get("pipeline_error", "")
                
                print(f"  [Attempt {attempt+1}/{max_attempts}] ocr: '{pipeline_status.get('ocr')}' | render: '{pipeline_status.get('render')}' | error: '{pipeline_error}'")
                
                if pipeline_status.get("render") == "success":
                    pipeline_done = True
                    break
                elif pipeline_error or any(v == "failed" for v in pipeline_status.values()):
                    print(f"[FAIL] Background pipeline failed: {pipeline_error}")
                    return False
            else:
                print(f"Failed to fetch session: {session_resp.status_code} - {session_resp.text}")
                
        if not pipeline_done:
            print("[FAIL] Pipeline timed out before completion.")
            return False
            
        # 8. Check generated segments in SQLite/D1
        print("\n8. Verifying translated segments from D1")
        seg_resp = await client.get(
            f"{API_URL}/api/docs/{doc_id}/segments?project_id={project_id}&asset_id={filename}",
            headers=headers
        )
        if seg_resp.status_code != 200:
            print(f"Failed to retrieve segments: {seg_resp.status_code} - {seg_resp.text}")
            return False
            
        segments = seg_resp.json()
        print(f"✓ Retrieved {len(segments)} segment(s) from D1:")
        for seg in segments:
            print(f"  - Segment {seg['segment_id']}: '{seg['source_text']}' → '{seg['target_text']}' (Approved by user ID: {seg['approved_by']})")
            
        print("\n=== E2E Image Translation Pipeline Test PASSED successfully! ===")
        return True

if __name__ == "__main__":
    asyncio.run(test_image_translation_flow())
