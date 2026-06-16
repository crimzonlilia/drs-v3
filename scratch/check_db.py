import asyncio
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force stdout to use UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from core.utils.db import execute_query

async def main():
    print("--- Database Mode ---")
    from core.utils.db import is_cloud_mode
    print("Cloud Mode:", is_cloud_mode())
    
    print("\n--- Projects ---")
    projects = await execute_query("SELECT id, display_name, source_lang, target_lang FROM projects")
    for p in projects:
        print(p)
        
    print("\n--- Assets ---")
    assets = await execute_query("SELECT asset_id, project_id, doc_id, mime_type, created_at FROM assets ORDER BY created_at DESC LIMIT 5")
    for a in assets:
        print(a)
        
    print("\n--- Segments ---")
    segments = await execute_query("SELECT segment_id, doc_id, source_text, target_text, asset_id FROM segments LIMIT 10")
    for s in segments:
        print(s)

    print("\n--- Chat History ---")
    chat = await execute_query("SELECT id, sender, text, status, is_image_workflow, asset_id, created_at FROM chat_history ORDER BY created_at DESC LIMIT 10")
    for c in chat:
        print(c)

if __name__ == "__main__":
    asyncio.run(main())
