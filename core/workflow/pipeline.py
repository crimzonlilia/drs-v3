"""
Pipeline — orchestrates the full DRS v3 localization workflow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Awaitable, Tuple, List

from config import cfg
from core.memory import ProjectMemory
from core.checks import CheckSuite, CheckReport
from core.agents import CandidateGenerator, GenerationResult, Reviewer, ReviewResult
from core.workflow.approval_gate import ApprovalGate, ApprovalSession, PromotionResult
from core.utils.r2 import write_text


@dataclass
class PipelineResult:
    session: ApprovalSession
    generation: GenerationResult
    check_report: CheckReport
    review: ReviewResult
    promotion: Optional[PromotionResult] = None

    @property
    def approved(self) -> bool:
        from core.workflow.approval_gate import Decision
        return self.session.decision in (Decision.APPROVED, Decision.EDITED)

    @property
    def final_text(self) -> str:
        return self.session.final_text

    def summary(self) -> str:
        lines = [
            f"{'='*55}",
            f"Pipeline run: {self.session.session_id}",
            f"{'='*55}",
            f"  Generation model : {self.generation.model}",
            f"  Tokens used      : {self.generation.prompt_tokens}p + {self.generation.completion_tokens}c",
            f"  Check issues     : {len(self.check_report.term_flags)} term / "
            f"{len(self.check_report.entity_flags)} entity / "
            f"{len(self.check_report.style_flags)} style",
            f"  Review note      : {self.review.review_note}",
            f"  Decision         : {self.session.decision}",
        ]
        if self.promotion:
            lines.append(f"  Corrections logged: {self.promotion.promoted_corrections}")
        return "\n".join(lines)


class Pipeline:
    """
    Full localization pipeline for one chunk of text (chapter, page, scene).
    """

    def __init__(
        self,
        memory: ProjectMemory,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
    ):
        self.memory = memory
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.content_type = content_type

        from core.agents.translation_agent import TranslationAgent
        from core.agents.consistency_auditor import ConsistencyAuditor
        self.translation_agent = TranslationAgent(memory)
        self.consistency_auditor = ConsistencyAuditor(memory)
        self.gate = ApprovalGate(memory)

    # ------------------------------------------------------------------ #
    # Main run                                                             #
    # ------------------------------------------------------------------ #

    async def run(
        self,
        source_text: str,
        doc_id: str,
        review_callback: Callable[[ApprovalSession], Awaitable[Tuple[str, List[Dict[str, Any]]]]],
        save_output: bool = True
    ) -> PipelineResult:

        # Step 1: Generate candidate
        print(f"[1/4] Generating draft ({self.translation_agent.generator.model})...")
        gen_result = await self.translation_agent.translate(
            source_text, self.source_lang, self.target_lang, self.content_type
        )

        # Step 2 & 3: Consistency checks & AI Review pass via ConsistencyAuditor
        print("[2/4] and [3/4] Running ConsistencyAuditor checks and review...")
        audit_result = await self.consistency_auditor.audit(
            source_text=source_text,
            current_draft=gen_result.draft,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            content_type=self.content_type
        )

        # Step 4: Human review via callback
        print("[4/4] Awaiting human review...")
        
        # Populate initial memory proposals based on audit or source text match
        memory_proposals = []
        # Fallback flags for backward compatibility of PipelineResult
        check_report = self.consistency_auditor.check_suite.run(
            source_text=source_text,
            draft_text=gen_result.draft,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            content_type=self.content_type,
        )
        
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

        session = self.gate.create_session(
            doc_id=doc_id,
            source_text=source_text,
            current_draft=gen_result.draft,
            audit_report=audit_result.audit_report,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            validation_issues=audit_result.validation_issues,
            editorial_score=audit_result.editorial_score,
            editorial_feedback=audit_result.editorial_feedback,
            memory_proposals=memory_proposals
        )

        final_text, callback_proposals = await review_callback(session)

        if final_text:
            session.current_draft = final_text
            session.memory_proposals = callback_proposals
            promotion = await self.gate.approve(session)
        else:
            self.gate.reject(session)
            promotion = None

        from core.agents import ReviewResult
        # Fake a ReviewResult for PipelineResult backward compatibility
        mock_review_result = ReviewResult(
            revised_draft=gen_result.draft,
            review_note=audit_result.audit_report,
            model=self.consistency_auditor.reviewer.model
        )

        result = PipelineResult(
            session=session,
            generation=gen_result,
            check_report=check_report,
            review=mock_review_result,
            promotion=promotion,
        )


        # Save approved output to R2
        if save_output and result.approved:
            self._save_output_r2(result, doc_id)

        print(result.summary())
        return result

    # ------------------------------------------------------------------ #
    # Output persistence to R2                                             #
    # ------------------------------------------------------------------ #

    def _save_output_r2(
        self,
        result: PipelineResult,
        doc_id: str
    ) -> None:
        doc_prefix = f"projects/{self.memory.project_id}/docs/{doc_id}/"
        
        # draft for reference
        write_text(f"{doc_prefix}draft.md", result.generation.draft)

        # review log
        log_lines = [
            f"# Review Log — {doc_id}",
            f"Run: {result.session.session_id}",
            f"Date: {result.session.decided_at}",
            f"Decision: {result.session.decision}",
            "",
            "## Check Report",
            result.check_report.summary(),
            "",
            "## Review Note",
            result.review.review_note,
        ]
        if result.session.memory_proposals:
            log_lines += ["", "## Memory Proposals Logged"]
            for p in result.session.memory_proposals:
                log_lines.append(
                    f"- [{p.get('type')}] '{p.get('source_term')}' → '{p.get('target_term')}' (strictness: {p.get('strictness', 'flexible')})"
                )

        write_text(f"{doc_prefix}review_log.md", "\n".join(log_lines))

    # ------------------------------------------------------------------ #
    # Context manager                                                      #
    # ------------------------------------------------------------------ #

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.translation_agent.close()
        await self.consistency_auditor.close()


# Alias for Orchestration role
Orchestrator = Pipeline