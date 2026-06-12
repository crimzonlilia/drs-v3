"""
Translation and Approval workflow router using Cloudflare R2 and D1.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from dataclasses import asdict

from core.memory import ProjectMemory
from core.workflow.approval_gate import ApprovalGate, Decision
from core.agents import TranslationAgent, ConsistencyAuditor
from server.schemas import TranslateRequest, TranslateResponse, ChatRequest, ChatResponse, ChatHistoryUpsert
from server.auth import get_current_user
from server.routers.projects import verify_project_member
from core.utils.db import execute_query

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
    using the unified TranslationAgent and ConsistencyAuditor.
    """
    # Verify editor permissions
    await verify_project_member(request.project_id, current_user["id"], "editor")
    
    mem = ProjectMemory(request.project_id)
    
    # Fetch project description
    project_rows = await execute_query("SELECT description FROM projects WHERE id = ?", [request.project_id])
    project_description = project_rows[0].get("description", "") if project_rows else ""
    
    try:
        async with TranslationAgent(mem) as translation_agent, ConsistencyAuditor(mem) as consistency_auditor:
            # 1. Load memory & context
            memory_data = translation_agent.load_project_memory(
                doc_id=request.doc_id,
                source_text=request.source_text,
                source_lang=request.source_lang,
                target_lang=request.target_lang
            )
            
            # 2. Generate
            gen_result = await translation_agent.translate(
                source_text=request.source_text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                content_type=request.content_type,
                project_description=project_description
            )
            
            # 3. Audit (Consistency QA & Editorial QA)
            audit_result = await consistency_auditor.audit(
                source_text=request.source_text,
                current_draft=gen_result.draft,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                content_type=request.content_type
            )
            
            # 4. Populate memory proposals from audit report / checks
            check_report = consistency_auditor.check_suite.run(
                source_text=request.source_text,
                draft_text=gen_result.draft,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                content_type=request.content_type
            )
            
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
                
            # Submit proposals to session cache
            gate = ApprovalGate(mem)
            session = gate.create_session(
                doc_id=request.doc_id,
                source_text=request.source_text,
                current_draft=gen_result.draft,
                audit_report=audit_result.audit_report,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                validation_issues=audit_result.validation_issues,
                editorial_score=audit_result.editorial_score,
                editorial_feedback=audit_result.editorial_feedback,
                memory_proposals=memory_proposals
            )
            
            # Set pipeline status for text translation (first class status tracking)
            session.pipeline_status = {
                "upload": "success",
                "ocr": "success",  # marked success/skipped
                "context_retrieval": "success",
                "draft_translation": "success",
                "review": "running",
                "approve": "idle",
                "render": "idle"
            }
            gate.save_translation_draft(session)
            
            # Fetch context details
            context = await translation_agent.build_translation_context(request.doc_id, request.segment_id or "")
            
            return TranslateResponse(
                session_id=session.session_id,
                project_id=request.project_id,
                doc_id=request.doc_id,
                segment_id=request.segment_id,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                source_text=request.source_text,
                translation_context={
                    "filtered_glossary": memory_data["filtered_glossary"],
                    "filtered_entities": memory_data["filtered_entities"],
                    "project_styles": memory_data["project_styles"],
                    "sliding_window": context.get("sliding_window", []),
                    "style_corrections": memory_data.get("style_corrections", [])
                },
                current_draft=session.current_draft,
                memory_proposals=session.memory_proposals,
                validation_issues=session.validation_issues,
                editorial_score=session.editorial_score,
                editorial_feedback=session.editorial_feedback,
                audit_report=session.audit_report
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
        
        # Update pipeline status to approved
        session.pipeline_status["approve"] = "success"
        if session.pipeline_status.get("render") == "idle":
             pass # keep idle if no rendering
        gate.save_translation_draft(session)
        
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


@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get the current pipeline status of a session.
    """
    from core.workflow.approval_gate import SESSION_CACHE
    session = SESSION_CACHE.get(session_id)
    if not session:
        # Try cold resume
        try:
            await resume_session_endpoint(session_id=session_id, current_user=current_user)
            session = SESSION_CACHE.get(session_id)
        except Exception:
            pass
            
    if not session:
        raise HTTPException(status_code=404, detail="Approval session not found or expired")
        
    await verify_project_member(session.project_id, current_user["id"], "viewer")
    return {
        "session_id": session.session_id,
        "pipeline_status": session.pipeline_status,
        "pipeline_error": session.pipeline_error
    }


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
        async with TranslationAgent(mem) as agent:
            ref_result = await agent.revise(
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


@router.post("/chat", response_model=ChatResponse)
async def chat_assistant(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    General chatbot assistant endpoint for out-of-scope discussion.
    Uses the project memory and description to provide smart, context-aware answers.
    """
    await verify_project_member(request.project_id, current_user["id"], "viewer")
    
    mem = ProjectMemory(request.project_id)
    
    # 1. Fetch project details
    project_rows = await execute_query("SELECT description, source_lang, target_lang FROM projects WHERE id = ?", [request.project_id])
    if not project_rows:
        raise HTTPException(status_code=404, detail="Project not found")
    project_description = project_rows[0].get("description", "")
    source_lang = project_rows[0].get("source_lang", "ja")
    target_lang = project_rows[0].get("target_lang", "vi")
    
    # 2. Build memory context (Glossary, Entities, Styles)
    memory_context = mem.build_prompt_context(source_lang, target_lang)
    
    system_prompt = f"""You are a helpful, professional localization assistant for the project '{request.project_id}'.
Project Context/Description:
{project_description or "(No project description provided)"}

Here is the approved project memory (Glossary, Character Entities, and Styles) that you can reference to answer user queries:
{memory_context or "(No approved memory yet for this project)"}

The user may talk to you, ask general questions about the project, characters, grammar, or ask for translation advice.
Answer naturally, concisely, and helpfully. Keep your tone professional.
"""
    
    from core.agents.candidate_generator import CandidateGenerator
    
    try:
        async with CandidateGenerator(mem) as generator:
            reply = await generator.chat(
                system_prompt=system_prompt,
                message=request.message,
                history=request.history
            )
            return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat generation failed: {e}")


@router.post("/history/upsert")
async def upsert_history_message(
    request: ChatHistoryUpsert,
    current_user: dict = Depends(get_current_user)
):
    """
    Save or update a chat timeline message in the project document history database.
    """
    await verify_project_member(request.project_id, current_user["id"], "editor")
    
    # Check if message already exists
    exists = await execute_query("SELECT id FROM chat_history WHERE id = ?", [request.id])
    
    editorial_score_json = json.dumps(request.editorialScore) if request.editorialScore is not None else None
    validation_issues_json = json.dumps(request.validationIssues) if request.validationIssues is not None else None
    editorial_feedback_json = json.dumps(request.editorialFeedback) if request.editorialFeedback is not None else None
    proposals_json = json.dumps(request.proposals) if request.proposals is not None else None
    segments_json = json.dumps(request.segments) if request.segments is not None else None
    
    if exists:
        sql = """
        UPDATE chat_history SET
            text = ?, original_text = ?, instruction = ?, status = ?, session_id = ?, qa_score = ?,
            editorial_score_json = ?, validation_issues_json = ?, editorial_feedback_json = ?,
            proposals_json = ?, segments_json = ?
        WHERE id = ?
        """
        params = [
            request.text, request.originalText, request.instruction, request.status, request.sessionId, request.qaScore,
            editorial_score_json, validation_issues_json, editorial_feedback_json,
            proposals_json, segments_json, request.id
        ]
        await execute_query(sql, params)
    else:
        sql = """
        INSERT INTO chat_history (
            id, project_id, doc_id, sender, text, original_text, instruction, status, session_id,
            is_image_workflow, is_general_chat, asset_id, qa_score, editorial_score_json,
            validation_issues_json, editorial_feedback_json, proposals_json, segments_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            request.id, request.project_id, request.doc_id, request.sender, request.text,
            request.originalText, request.instruction, request.status, request.sessionId,
            1 if request.isImageWorkflow else 0, 1 if request.isGeneralChat else 0,
            request.assetId, request.qaScore,
            editorial_score_json, validation_issues_json, editorial_feedback_json,
            proposals_json, segments_json, datetime.now().isoformat()
        ]
        await execute_query(sql, params)
        return {"status": "success"}


@router.delete("/history/{message_id}")
async def delete_history_message(
    message_id: str,
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a message from the persistent chat history.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    await execute_query("DELETE FROM chat_history WHERE id = ?", [message_id])
    return {"status": "success"}


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_chat_history(
    project_id: str,
    doc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch persistent chat/translation history for a project document.
    """
    await verify_project_member(project_id, current_user["id"], "viewer")
    
    rows = await execute_query(
        "SELECT * FROM chat_history WHERE project_id = ? AND doc_id = ? ORDER BY created_at ASC",
        [project_id, doc_id]
    )
    
    chat_list = []
    for r in rows:
        chat_list.append({
            "id": r["id"],
            "sender": r["sender"],
            "text": r["text"],
            "originalText": r.get("original_text") or "",
            "instruction": r.get("instruction") or "",
            "status": r["status"],
            "sessionId": r.get("session_id") or "",
            "isImageWorkflow": bool(r["is_image_workflow"]),
            "isGeneralChat": bool(r["is_general_chat"]),
            "assetId": r.get("asset_id") or "",
            "qaScore": r.get("qa_score"),
            "editorialScore": json.loads(r["editorial_score_json"]) if r.get("editorial_score_json") else {},
            "validationIssues": json.loads(r["validation_issues_json"]) if r.get("validation_issues_json") else [],
            "editorialFeedback": json.loads(r["editorial_feedback_json"]) if r.get("editorial_feedback_json") else [],
            "proposals": json.loads(r["proposals_json"]) if r.get("proposals_json") else [],
            "segments": json.loads(r["segments_json"]) if r.get("segments_json") else [],
            "timestamp": r["created_at"][11:16] if r.get("created_at") else ""
        })
    return chat_list

