import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from core.utils.db import execute_query

async def main():
    asset_id = 'HKkmC_ab0AA7fg8.png'
    print(f"--- Segments for asset {asset_id} ---")
    segments = await execute_query(
        "SELECT id, segment_id, source_text, target_text, bbox FROM segments WHERE asset_id = ?",
        [asset_id]
    )
    print("Number of segments found:", len(segments))
    for s in segments:
        print(s)
        
    print(f"\n--- Checking session cache or drafts in D1/R2 ---")
    # Let's check if there are drafts in D1 or R2
    # In R2, the draft path is projects/demo_project/docs/doc_test_export/draft.md or draft_state.json
    from core.utils.r2 import read_text, list_files
    print("\nFiles in R2 doc folder:")
    files = list_files("projects/demo_project/docs/doc_test_export/")
    for f in files:
        print(f)
        
    draft_state = read_text("projects/demo_project/docs/doc_test_export/draft_state.json")
    if draft_state:
        print("\nDraft State:")
        try:
            state_data = json.loads(draft_state)
            print("session_id:", state_data.get("session_id"))
            print("pipeline_status:", state_data.get("pipeline_status"))
            print("pipeline_error:", state_data.get("pipeline_error"))
        except Exception as e:
            print("Error parsing draft_state:", e)

if __name__ == "__main__":
    import json
    asyncio.run(main())
