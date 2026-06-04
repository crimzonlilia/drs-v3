"""
Translation and Approval workflow router.
"""

from pathlib import Path
from typing import Dict, Any
import uuid
from fastapi import APIRouter, HTTPException, Depends

from core.memory import ProjectMemory, Correction, CorrectionType
from core.workflow import ApprovalGate
from core.agents import CandidateGenerator, Reviewer
from core.checks import CheckSuite
from server.schemas import TranslateRequest, TranslateResponse, ApproveRequest
from server.auth import get_current_user

router = APIRouter(prefix="/api/translation", tags=["Translation"])


@router.post("/translate", response_model=TranslateResponse)
async def run_translation(request: TranslateRequest, current_user: dict = Depends(get_current_user)):
    """
    Runs the translation flow (Generate -> Checks -> Reviewer)
    and returns a review session waiting for user approval.
    """
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

        # Step 4: Create Approval Session (State saved in workspace/sessions)
        gate = ApprovalGate(mem)
        session = gate.create_session(
            chapter_or_doc=request.chapter_or_doc,
            source_text=request.source_text,
            draft=review_result.revised_draft,
            review_note=review_result.review_note
        )

        return TranslateResponse(
            session_id=session.session_id,
            draft=review_result.revised_draft,
            review_note=review_result.review_note,
            check_report={
                "has_issues": check_report.has_issues,
                "term_flags": [f"{f.term} ({f.flag_type})" for f in check_report.term_flags],
                "entity_flags": [f"{f.entity_id} ({f.flag_type})" for f in check_report.entity_flags],
                "style_flags": [f.rule_id for f in check_report.style_flags]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {e}")


@router.post("/approve/{project_id}/{session_id}")
async def approve_translation(project_id: str, session_id: str, data: ApproveRequest, current_user: dict = Depends(get_current_user)):
    """
    Submit final approved translations and corrections.
    Promotes corrections to Glossary/Entities automatically.
    """
    mem = ProjectMemory(project_id)
    gate = ApprovalGate(mem)

    session = gate.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Approval session not found or expired")

    # Map inputs to Correction schema
    corrections = []
    for c in data.corrections:
        corrections.append(Correction(
            correction_id=str(uuid.uuid4())[:8],
            project_id=project_id,
            chapter_or_doc=session.chapter_or_doc,
            source_lang=session.source_lang if hasattr(session, "source_lang") else "ja",
            target_lang=session.target_lang if hasattr(session, "target_lang") else "vi",
            correction_type=CorrectionType(c.correction_type),
            source_term=c.source_term,
            original_text=c.original_text,
            corrected_text=c.corrected_text,
            note=c.note
        ))

    try:
        promotion = gate.approve(session, data.final_text, corrections)
        
        # Save output to projects folder
        chapter_path = Path("projects") / project_id / "chapters" / session.chapter_or_doc
        chapter_path.mkdir(parents=True, exist_ok=True)
        (chapter_path / "approved.md").write_text(data.final_text, encoding="utf-8")
        
        return {
            "status": "success",
            "message": "Translation approved and saved successfully",
            "promoted_corrections": promotion.promoted_corrections if promotion else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error approving session: {e}")
