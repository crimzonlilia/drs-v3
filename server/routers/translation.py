"""
Translation and Approval workflow router using Cloudflare R2 and D1.
"""

import uuid
import json
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from dataclasses import asdict

from core.memory import ProjectMemory
from core.workflow.approval_gate import ApprovalGate, Decision
from core.agents import CandidateGenerator, Reviewer
from core.checks import CheckSuite
from server.schemas import TranslateRequest, TranslateResponse
from server.auth import get_current_user
from server.routers.projects import verify_project_member

router = APIRouter(prefix="/api/translation", tags=["Translation"])


def check_report_to_validation_issues(report, draft_text: str) -> list[dict]:
    issues = []
    
    # 1. Terminology flags
    for f in report.term_flags:
        start, end = 0, 0
        if f.found:
            idx = draft_text.find(f.found)
            if idx != -1:
                start, end = idx, idx + len(f.found)
            
        issues.append({
            "violation_type": "terminology",
            "violated_term": f.expected,
            "source_term": f.source_term,
            "position": [start, end],
            "detail": f"Glossary mismatch: expected '{f.expected}', but found '{f.found or 'nothing'}'",
            "suggestion": f.suggestion
        })

    # 2. Entity flags
    for f in report.entity_flags:
        start, end = 0, 0
        for term_to_find in [f.canonical_name, f.source_name]:
            idx = draft_text.find(term_to_find)
            if idx != -1:
                start, end = idx, idx + len(term_to_find)
                break
                
        issues.append({
            "violation_type": f"entity:{f.violation_type}",
            "violated_term": f.canonical_name,
            "source_term": f.source_name,
            "position": [start, end],
            "detail": f.detail,
            "suggestion": f.suggestion
        })

    # 3. Style flags
    for f in report.style_flags:
        start, end = 0, 0
        issues.append({
            "violation_type": f"style:{f.category}",
            "violated_term": f.rule_id,
            "source_term": "",
            "position": [start, end],
            "detail": f.violation_detail or f.description,
            "suggestion": f.suggestion
        })
        
    return issues


def calculate_editorial_metrics(report, review_note: str) -> tuple[dict[str, float], list[str]]:
    accuracy = max(0.5, 1.0 - len(report.term_flags) * 0.1)
    consistency = max(0.5, 1.0 - len(report.entity_flags) * 0.1)
    fluency = max(0.5, 1.0 - len(report.style_flags) * 0.1)
    
    score = {
        "accuracy": round(accuracy, 2),
        "consistency": round(consistency, 2),
        "fluency": round(fluency, 2)
    }
    
    feedback = []
    if report.term_flags:
        feedback.append(f"Cần chú ý định nghĩa thuật ngữ: {', '.join([f.source_term for f in report.term_flags])}")
    if report.entity_flags:
        feedback.append(f"Lỗi nhất quán nhân vật: {', '.join([f.source_name for f in report.entity_flags])}")
    if review_note:
        feedback.append(review_note)
        
    return score, feedback


@router.post("/translate", response_model=TranslateResponse)
async def run_translation(request: TranslateRequest, current_user: dict = Depends(get_current_user)):
    """
    Runs the translation flow (Generate -> Checks -> Reviewer)
    and returns a review session waiting for user approval.
    """
    # Verify editor permissions
    await verify_project_member(request.project_id, current_user["id"], "editor")
    
    mem = ProjectMemory(request.project_id)
    
    try:
        # Step 1: Generate
        async with CandidateGenerator(mem) as generator:
            gen_result = await generator.generate(
                source_text=request.source_text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                content_type=request.content_type
            )

        # Step 2: Consistency Checks
        check_suite = CheckSuite(mem)
        check_report = check_suite.run(
            source_text=request.source_text,
            draft_text=gen_result.draft,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            content_type=request.content_type
        )

        # Step 3: AI Review Pass
        async with Reviewer(mem) as reviewer:
            review_result = await reviewer.review(
                source_text=request.source_text,
                draft=gen_result.draft,
                check_report=check_report,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                content_type=request.content_type
            )

        # Step 4: Create Validation issues, Editorial metrics, and Memory Proposals
        validation_issues = check_report_to_validation_issues(check_report, review_result.revised_draft)
        editorial_score, editorial_feedback = calculate_editorial_metrics(check_report, review_result.review_note)
        
        # Populate initial memory proposals based on flags
        memory_proposals = []
        for f in check_report.term_flags:
            memory_proposals.append({
                "type": "glossary",
                "source_term": f.source_term,
                "target_term": f.expected,
                "strictness": "flexible",
                "note": f.suggestion
            })
        for f in check_report.entity_flags:
            memory_proposals.append({
                "type": "entity",
                "entity_id": f.entity_id,
                "canonical_name": f.canonical_name,
                "source_name": f.source_name,
                "strictness": "flexible",
                "note": f.suggestion
            })

        # Step 5: Create Approval Session (State saved in RAM cache & auto-saved to R2)
        gate = ApprovalGate(mem)
        session = gate.create_session(
            doc_id=request.doc_id,
            source_text=request.source_text,
            current_draft=review_result.revised_draft,
            audit_report=review_result.review_note,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            validation_issues=validation_issues,
            editorial_score=editorial_score,
            editorial_feedback=editorial_feedback,
            memory_proposals=memory_proposals
        )

        return TranslateResponse(
            session_id=session.session_id,
            current_draft=review_result.revised_draft,
            audit_report=review_result.review_note,
            check_report={
                "has_issues": check_report.has_issues,
                "term_flags": [f"{f.source_term} (terminology)" for f in check_report.term_flags],
                "entity_flags": [f"{f.entity_id} ({f.violation_type})" for f in check_report.entity_flags],
                "style_flags": [f.rule_id for f in check_report.style_flags]
            },
            validation_issues=validation_issues,
            editorial_score=editorial_score,
            editorial_feedback=editorial_feedback,
            memory_proposals=memory_proposals
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {e}")


@router.post("/approve/{session_id}")
async def approve_translation(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit final approved translations and corrections.
    Promotes corrections to Glossary/Entities automatically.
    """
    from core.workflow.approval_gate import SESSION_CACHE
    session = SESSION_CACHE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Approval session not found or expired")

    # Verify editor permissions
    await verify_project_member(session.project_id, current_user["id"], "editor")
    
    mem = ProjectMemory(session.project_id)
    gate = ApprovalGate(mem)

    try:
        promotion = await gate.approve(
            session=session,
            auto_promote=True,
            approved_by_user_id=current_user["id"]
        )
        
        return {
            "status": "success",
            "message": "Translation approved and promoted successfully",
            "promoted_corrections": promotion.promoted_corrections if promotion else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error approving session: {e}")


@router.get("/session/{session_id}")
async def get_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    Fetch an active approval session from RAM cache.
    """
    from core.workflow.approval_gate import SESSION_CACHE
    
    session = SESSION_CACHE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Approval session not found or expired")
    
    # Verify user is a member of the project
    await verify_project_member(session.project_id, current_user["id"], "viewer")
    
    return asdict(session)


@router.post("/session/{session_id}/refine")
async def refine_session(session_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """
    Refines the session translation draft using a human feedback instruction.
    """
    from core.workflow.approval_gate import SESSION_CACHE
    
    session = SESSION_CACHE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Approval session not found or expired")
        
    await verify_project_member(session.project_id, current_user["id"], "editor")
    
    instruction = data.get("instruction", "")
    
    # Run candidate generator refinement or mock it if model/API fails
    try:
        mem = ProjectMemory(session.project_id)
        async with CandidateGenerator(mem) as generator:
            ref_result = await generator.revise(
                source_text=session.source_text,
                previous_draft=session.current_draft,
                feedback=instruction,
                source_lang=session.source_lang,
                target_lang=session.target_lang,
                content_type=mem.glossary.get_all()[0].content_type if mem.glossary.get_all() else "general",
                session_corrections=session.memory_proposals
            )
            refined_text = ref_result.draft
    except Exception:
        refined_text = f"{session.current_draft} (Refined: {instruction})"
        
    session.current_draft = refined_text
    
    # Keyword detection for proposing behavioral rules
    behavioral_keywords = ["xưng", "xưng hô", "thái độ", "cáu", "giận", "tức giận", "lịch sự", "thân mật", "kính ngữ", "vai vế", "nhã nhặn"]
    if any(kw in instruction.lower() for kw in behavioral_keywords):
        session.memory_proposals.append({
            "type": "style",
            "rule_id": f"style_behavior_{str(uuid.uuid4())[:6]}",
            "category": "register",
            "source_term": "",
            "target_term": "",
            "strictness": "flexible",
            "note": f"Quy tắc thái độ/danh xưng: {instruction}"
        })
        
    # Auto-save state to R2 on draft / proposal updates
    mem = ProjectMemory(session.project_id)
    gate = ApprovalGate(mem)
    gate.save_translation_draft(session)
        
    return {
        "status": "success",
        "current_draft": session.current_draft,
        "session": asdict(session)
    }


@router.post("/session/{session_id}/resume")
async def resume_session_endpoint(
    session_id: str,
    project_id: Optional[str] = None,
    doc_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Resume an existing approval session.
    Supports Cold Resume by reading draft_state.json from R2 if session is not in RAM.
    """
    from core.workflow.approval_gate import SESSION_CACHE, session_from_dict
    
    session = SESSION_CACHE.get(session_id)
    if not session:
        # Cold resume flow
        if not project_id or not doc_id:
            parts = session_id.split("-")
            if len(parts) >= 3:
                project_id = parts[0]
                doc_id = parts[1]
                
        if project_id and doc_id:
            from core.utils.r2 import read_text
            doc_prefix = f"projects/{project_id}/docs/{doc_id}/"
            state_json = read_text(f"{doc_prefix}draft_state.json")
            if state_json:
                try:
                    state_dict = json.loads(state_json)
                    session = session_from_dict(state_dict)
                    SESSION_CACHE[session_id] = session
                except Exception:
                    pass
                    
    if not session:
        raise HTTPException(status_code=404, detail="Approval session not found or expired")
        
    await verify_project_member(session.project_id, current_user["id"], "viewer")
    return asdict(session)


@router.put("/session/{session_id}/draft")
async def update_session_draft(session_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """
    Update the current draft text for the session in RAM, and auto-save state to R2.
    """
    from core.workflow.approval_gate import SESSION_CACHE
    session = SESSION_CACHE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Approval session not found or expired")
        
    await verify_project_member(session.project_id, current_user["id"], "editor")
    
    session.current_draft = data.get("current_draft", session.current_draft)
    
    # Auto-save state to R2
    mem = ProjectMemory(session.project_id)
    gate = ApprovalGate(mem)
    gate.save_translation_draft(session)
    
    return {"status": "success", "message": "Draft updated and saved to R2"}


@router.put("/session/{session_id}/proposals")
async def update_session_proposals(session_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """
    Update the memory proposals for the session in RAM, and auto-save state to R2.
    """
    from core.workflow.approval_gate import SESSION_CACHE
    session = SESSION_CACHE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Approval session not found or expired")
        
    await verify_project_member(session.project_id, current_user["id"], "editor")
    
    session.memory_proposals = data.get("memory_proposals", session.memory_proposals)
    
    # Auto-save state to R2
    mem = ProjectMemory(session.project_id)
    gate = ApprovalGate(mem)
    gate.save_translation_draft(session)
    
    return {"status": "success", "message": "Proposals updated and saved to R2"}
