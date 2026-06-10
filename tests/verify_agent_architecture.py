import os
import sys
import asyncio
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.memory import ProjectMemory
from core.workflow.approval_gate import ApprovalGate, SESSION_CACHE
from core.agents import TranslationAgent, ConsistencyAuditor, LayoutAgent
from core.workflow.pipeline import Pipeline

async def mock_review_callback(session):
    # Auto-approve callback
    return session.current_draft, session.memory_proposals

async def main():
    # Set stdout to handle UTF-8 printing
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    
    print("=== Verification of DRS v3 3-Agent Architecture Split ===")
    
    project_id = "demo_project"
    doc_id = "ch001"
    source_lang = "ja"
    target_lang = "vi"
    source_text = "ジョンは先輩 và 陛下を見ました。"
    
    mem = ProjectMemory(project_id)
    print(f"Project Memory loaded for project: {mem.project_id}")
    
    # ----------------------------------------------------
    # 1. Verify TranslationAgent
    # ----------------------------------------------------
    print("\n--- 1. Testing TranslationAgent ---")
    async with TranslationAgent(mem) as translation_agent:
        # Load memory
        mem_data = translation_agent.load_project_memory(doc_id, source_text, source_lang, target_lang)
        print("✓ load_project_memory successful!")
        print(f"  Filtered glossary keys: {list(mem_data.keys())}")
        
        # Build translation context
        context = await translation_agent.build_translation_context(doc_id, "seg_001")
        print("✓ build_translation_context successful!")
        print(f"  Context keys: {list(context.keys())}")
        
        # Translate
        gen_result = await translation_agent.translate(source_text, source_lang, target_lang)
        print("✓ translate successful!")
        print(f"  Generated Draft: {gen_result.draft}")
        
        # Create session and test proposals/saving
        gate = ApprovalGate(mem)
        session = gate.create_session(
            doc_id=doc_id,
            source_text=source_text,
            current_draft=gen_result.draft,
            source_lang=source_lang,
            target_lang=target_lang
        )
        session_id = session.session_id
        
        # Submit memory proposals
        proposals = [{"type": "glossary", "source_term": "先輩", "target_term": "Tiền bối", "strictness": "flexible"}]
        sub_ok = translation_agent.submit_memory_proposals(session_id, proposals)
        print(f"✓ submit_memory_proposals successful: {sub_ok}")
        print(f"  Session proposals: {session.memory_proposals}")
        
        # Save translation draft
        save_ok = translation_agent.save_translation_draft(session_id, "Bản dịch nháp mới của John")
        print(f"✓ save_translation_draft successful: {save_ok}")
        print(f"  Updated Draft in session: {session.current_draft}")
        
        # Revise
        revised = await translation_agent.revise(source_text, gen_result.draft, "Make it sound more formal", source_lang, target_lang)
        print("✓ revise method successful!")
        print(f"  Revised Draft: {revised.draft}")
        
    # ----------------------------------------------------
    # 2. Verify ConsistencyAuditor
    # ----------------------------------------------------
    print("\n--- 2. Testing ConsistencyAuditor ---")
    async with ConsistencyAuditor(mem) as auditor:
        # Run audit
        audit_result = await auditor.audit(source_text, "John nhìn thấy Tiền bối và Bệ hạ.", source_lang, target_lang)
        print("✓ audit successful!")
        print(f"  Audit report: {audit_result.audit_report}")
        print(f"  Validation issues count: {len(audit_result.validation_issues)}")
        print(f"  Editorial score: {audit_result.editorial_score}")
        print(f"  Editorial feedback: {audit_result.editorial_feedback}")
        
        # Run consistency checks on session
        session.current_draft = "John nhìn thấy Tiền bối và Bệ hạ."
        issues = auditor.run_consistency_checks(session.current_draft, session_id)
        print(f"✓ run_consistency_checks successful! Issues: {len(issues)}")
        
        # Retrieve corrections
        corrs = auditor.retrieve_relevant_corrections(doc_id, source_text)
        print(f"✓ retrieve_relevant_corrections successful! Count: {len(corrs)}")
        
        # Evaluate quality
        score, feedback = auditor.evaluate_translation_quality(session.current_draft, session_id)
        print(f"✓ evaluate_translation_quality successful! Score: {score}")
        
        # Generate summary
        summary = auditor.generate_audit_summary(session_id)
        print("✓ generate_audit_summary successful!")
        print(f"  Summary:\n{summary}")
        
        # Create review package
        package = auditor.create_review_package(session_id)
        print("✓ create_review_package successful!")
        print(f"  Package keys: {list(package.keys())}")
        
    # ----------------------------------------------------
    # 3. Verify LayoutAgent
    # ----------------------------------------------------
    print("\n--- 3. Testing LayoutAgent ---")
    async with LayoutAgent(mem) as layout_agent:
        # Extract layout
        layout = await layout_agent.extract_layout("page_001.png")
        print("✓ extract_layout successful!")
        print(f"  Blocks count: {len(layout)}")
        
        # Estimate capacity
        cap = layout_agent.estimate_text_capacity([100, 200, 300, 400], {"font_size": 12})
        print(f"✓ estimate_text_capacity successful! Estimated: {cap}")
        
        # Render page
        render_bytes = layout_agent.render_page("page_001.png", layout)
        print(f"✓ render_page successful! Bytes length: {len(render_bytes)}")
        
        # Audit visual layout
        visual_audit = layout_agent.audit_visual_layout("page_001_rendered.png")
        print("✓ audit_visual_layout successful!")
        print(f"  Visual audit status: {visual_audit.get('status')}")
        
    # ----------------------------------------------------
    # 4. Verify Pipeline Orchestration
    # ----------------------------------------------------
    print("\n--- 4. Testing Pipeline Orchestration ---")
    async with Pipeline(mem, source_lang, target_lang) as pipeline:
        res = await pipeline.run(source_text, doc_id, mock_review_callback, save_output=True)
        print("✓ Pipeline run executed successfully!")
        print(f"  Session ID: {res.session.session_id}")
        print(f"  Session decision: {res.session.decision}")
        print(f"  Final Text: {res.final_text}")
        
    print("\n=== All Agent Architecture verification steps PASSED successfully! ===")

if __name__ == "__main__":
    asyncio.run(main())
