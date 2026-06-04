"""
Pipeline — orchestrates the full DRS v3 localization workflow.

Flow:
    source_text
        → CandidateGenerator   (LLM draft with memory context)
        → CheckSuite           (rule-based consistency checks)
        → Reviewer             (LLM fix pass, only if issues found)
        → ApprovalGate         (human review + memory promotion)
        → approved output saved to project/chapters/

Each step produces a typed result. The pipeline is async end-to-end.
"""
from __future__ import annotations

# Feedback: review_callback rất đúng nhưng type hint thiếu, tôi cần Callable[
#     [ApprovalSession],
#     Awaitable[tuple[str, list[Correction]]]
# ]
# để rõ ràng hơn về kiểu dữ liệu của callback. Điều này sẽ giúp người dùng hiểu rõ hơn về cách định nghĩa hàm callback và đảm bảo rằng họ cung cấp đúng kiểu dữ liệu khi sử dụng pipeline. Ngoài ra, chúng ta cũng nên thêm docstring chi tiết cho review_callback để giải thích rõ hơn về mục đích của nó, các tham số đầu vào và giá trị trả về, để người dùng có thể dễ dàng triển khai hàm callback phù hợp với nhu cầu của họ.
# _save_output() path lệch với folder architecture?

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config import cfg
from core.memory import ProjectMemory
from core.checks import CheckSuite, CheckReport
from core.agents import CandidateGenerator, GenerationResult, Reviewer, ReviewResult
from core.workflow.approval_gate import ApprovalGate, ApprovalSession, PromotionResult


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

    Usage:
        mem = ProjectMemory("one-piece-vi")
        pipeline = Pipeline(mem, source_lang="ja", target_lang="vi", content_type="manga")

        async with pipeline:
            result = await pipeline.run(
                source_text=raw_text,
                chapter_or_doc="ch001",
                review_callback=my_human_review_fn,   # see below
            )

    review_callback signature:
        async def my_review(session: ApprovalSession) -> tuple[str, list[Correction]]:
            # present draft to human, get back final_text + corrections
            return final_text, corrections
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

        self.generator = CandidateGenerator(memory)
        self.reviewer = Reviewer(memory)
        self.check_suite = CheckSuite(memory)
        self.gate = ApprovalGate(memory)

    # ------------------------------------------------------------------ #
    # Main run                                                             #
    # ------------------------------------------------------------------ #

    async def run(
        self,
        source_text: str,
        chapter_or_doc: str,
        review_callback,   # async (ApprovalSession) -> (str, list[Correction])
        save_output: bool = True,
        output_dir: str | Path = "projects",
    ) -> PipelineResult:

        # Step 1: Generate candidate
        print(f"[1/4] Generating draft ({self.generator.model})...")
        gen_result = await self.generator.generate(
            source_text, self.source_lang, self.target_lang, self.content_type
        )

        # Step 2: Rule-based checks
        print("[2/4] Running consistency checks...")
        check_report = self.check_suite.run(
            source_text=source_text,
            draft_text=gen_result.draft,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            content_type=self.content_type,
        )
        print(check_report.summary())

        # Step 3: AI review pass (skipped if no issues)
        if check_report.has_issues:
            print(f"[3/4] Reviewer pass ({self.reviewer.model})...")
        else:
            print("[3/4] No issues — skipping reviewer pass.")
        review_result = await self.reviewer.review(
            source_text=source_text,
            draft=gen_result.draft,
            check_report=check_report,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            content_type=self.content_type,
        )

        # Step 4: Human review via callback
        print("[4/4] Awaiting human review...")
        session = self.gate.create_session(
            chapter_or_doc=chapter_or_doc,
            source_text=source_text,
            draft=review_result.revised_draft,
            review_note=review_result.review_note,
        )

        final_text, corrections = await review_callback(session)

        if final_text:
            promotion = self.gate.approve(session, final_text, corrections)
        else:
            self.gate.reject(session)
            promotion = None

        result = PipelineResult(
            session=session,
            generation=gen_result,
            check_report=check_report,
            review=review_result,
            promotion=promotion,
        )

        # Save approved output
        if save_output and result.approved:
            self._save_output(result, chapter_or_doc, output_dir)

        print(result.summary())
        return result

    # ------------------------------------------------------------------ #
    # Output persistence                                                   #
    # ------------------------------------------------------------------ #

    def _save_output(
        self,
        result: PipelineResult,
        chapter_or_doc: str,
        output_dir: str | Path,
    ) -> None:
        chapter_path = (
            Path(output_dir)
            / self.memory.project_id
            / "chapters"
            / chapter_or_doc
        )
        chapter_path.mkdir(parents=True, exist_ok=True)

        # approved output
        (chapter_path / "approved.md").write_text(
            result.final_text, encoding="utf-8"
        )

        # draft for reference
        (chapter_path / "draft.md").write_text(
            result.generation.draft, encoding="utf-8"
        )

        # review log
        log_lines = [
            f"# Review Log — {chapter_or_doc}",
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
        if result.session.corrections:
            log_lines += ["", "## Corrections Logged"]
            for c in result.session.corrections:
                log_lines.append(
                    f"- [{c.correction_type}] '{c.original_text}' → '{c.corrected_text}'"
                )

        (chapter_path / "review_log.md").write_text(
            "\n".join(log_lines), encoding="utf-8"
        )

    # ------------------------------------------------------------------ #
    # Context manager                                                      #
    # ------------------------------------------------------------------ #

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.generator.close()
        await self.reviewer.close()


# Alias for Orchestration role
Orchestrator = Pipeline