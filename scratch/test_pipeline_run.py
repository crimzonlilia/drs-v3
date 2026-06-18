import asyncio
from server.routers.docs import run_image_translation_pipeline_task
from core.workflow.approval_gate import ApprovalSession

async def main():
    project_id = "demo_project"
    doc_id = "doc_test_export"
    asset_id = "HK7N-hSawAAS_xY.jpg"
    session_id = f"{project_id}_{doc_id}_{asset_id}"
    
    session = ApprovalSession(
        session_id=session_id,
        project_id=project_id,
        doc_id=doc_id,
        source_text="",
        current_draft="",
        source_lang="ja",
        target_lang="vi"
    )
    
    from core.memory import ProjectMemory
    mem = ProjectMemory(project_id)
    from core.workflow.approval_gate import ApprovalGate
    gate = ApprovalGate(mem)
    gate.save_translation_draft(session)
    
    print("--- Starting Pipeline Run ---")
    await run_image_translation_pipeline_task(
        project_id=project_id,
        doc_id=doc_id,
        asset_id=asset_id,
        session_id=session_id,
        source_lang="ja",
        target_lang="vi"
    )
    
    print("\n--- Pipeline Completed ---")
    # Fetch updated session
    session_dict = gate.load_translation_draft(session_id)
    print("Pipeline status:", session_dict.pipeline_status if session_dict else None)
    print("Pipeline error:", session_dict.pipeline_error if session_dict else None)
    
    # Check if rendered file exists in R2
    from core.utils.r2 import read_binary
    try:
        rendered_key = f"projects/{project_id}/docs/{doc_id}/rendered/{asset_id}"
        rendered_bytes = read_binary(rendered_key)
        print(f"SUCCESS: Rendered preview image exists in R2! Size: {len(rendered_bytes)} bytes.")
    except Exception as e:
        print("ERROR: Rendered preview image does not exist or failed to load:", e)
        
    # Check some segments in SQLite to make sure they are translated
    from core.utils.db import execute_query
    segments = await execute_query(
        "SELECT segment_id, source_text, target_text FROM segments WHERE project_id = ? AND doc_id = ? AND asset_id = ? LIMIT 5",
        [project_id, doc_id, asset_id]
    )
    print("\nSample translated segments:")
    for s in segments:
        print(f"  Segment: {s['segment_id']}")
        print(f"    Source (raw bytes): {ascii(s['source_text'])}")
        print(f"    Target (raw bytes): {ascii(s['target_text'])}")

if __name__ == "__main__":
    asyncio.run(main())
