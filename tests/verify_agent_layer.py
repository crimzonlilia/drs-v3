import os
import sys
import asyncio
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.memory import ProjectMemory
from core.workflow.approval_gate import ApprovalGate, SESSION_CACHE, session_from_dict
from core.agents import CandidateGenerator
from server.routers.translation import check_report_to_validation_issues, calculate_editorial_metrics

async def main():
    # Set sys.stdout to handle UTF-8 print
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    
    print("Starting verification of DRS v3 Agent Layer...")
    
    # 1. Initialize project memory
    project_id = "demo_project"
    mem = ProjectMemory(project_id)
    print(f"ProjectMemory loaded successfully. Project: {mem.project_id}")
    print(f"Glossary terms count: {len(mem.glossary)}")
    print(f"Entities count: {len(mem.entities)}")
    
    # 2. Test session creation and auto-saving to R2
    gate = ApprovalGate(mem)
    doc_id = "ch001"
    source_text = "ジョンは先輩 và 陛下を見ました。"
    current_draft = "John đã nhìn thấy tiền bối và bệ hạ."
    audit_report = "Mock review note"
    
    session = gate.create_session(
        doc_id=doc_id,
        source_text=source_text,
        current_draft=current_draft,
        audit_report=audit_report,
        source_lang="ja",
        target_lang="vi",
        validation_issues=[],
        editorial_score={"accuracy": 1.0, "consistency": 1.0, "fluency": 1.0},
        editorial_feedback=["All good"],
        memory_proposals=[
            {
                "type": "glossary",
                "source_term": "陛下",
                "target_term": "Bệ hạ",
                "strictness": "fixed",
                "note": "Kính ngữ hoàng gia"
            }
        ]
    )
    
    session_id = session.session_id
    print(f"Session created with ID: {session_id}")
    
    # Check if files are written to mock R2
    r2_mock_dir = project_root / "memory_store" / "r2_mock" / "projects" / project_id / "docs" / doc_id
    draft_md = r2_mock_dir / "draft.md"
    draft_state_json = r2_mock_dir / "draft_state.json"
    
    print(f"Draft md exists in R2 mock: {draft_md.exists()}")
    print(f"Draft state json exists in R2 mock: {draft_state_json.exists()}")
    
    # 3. Test Cold Resume
    # Clear RAM cache
    if session_id in SESSION_CACHE:
        del SESSION_CACHE[session_id]
        
    print(f"Cleared cache. Session in RAM: {session_id in SESSION_CACHE}")
    
    # Reload using cold resume flow
    parts = session_id.split("-")
    p_id = parts[0]
    d_id = parts[1]
    
    from core.utils.r2 import read_text
    state_json = read_text(f"projects/{p_id}/docs/{d_id}/draft_state.json")
    if state_json:
        import json
        state_dict = json.loads(state_json)
        resumed_session = session_from_dict(state_dict)
        SESSION_CACHE[session_id] = resumed_session
        print(f"Cold Resume successful! Resumed session ID: {resumed_session.session_id}")
        print(f"Resumed draft: {resumed_session.current_draft}")
        print(f"Resumed proposals: {resumed_session.memory_proposals}")
    else:
        print("Failed to find draft_state.json on mock R2")
        
    # 4. Test Approve and promotion
    resumed_session.memory_proposals = [
        {
            "type": "glossary",
            "source_term": "テスト陛下",
            "target_term": "Bệ hạ Test",
            "strictness": "flexible",
            "note": "Test promotion"
        }
    ]
    
    print("Approving session and promoting rules...")
    promotion_result = await gate.approve(resumed_session, auto_promote=True)
    print(f"Promotion Result: Glossary={promotion_result.promoted_glossary}, Entities={promotion_result.promoted_entities}, Style={promotion_result.promoted_style}")
    
    # Verify promoted glossary term exists
    terms = mem.glossary.get_all(source_lang="ja", target_lang="vi")
    found_term = any(e.source_term == "テスト陛下" and e.strictness == "flexible" for e in terms)
    print(f"Promoted term 'テスト陛下' with flexible strictness exists: {found_term}")
    
    print("Verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
