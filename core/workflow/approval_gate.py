"""
Approval Gate — the boundary between working state and approved memory.

This is the core DRS thesis:
- Drafts and AI suggestions live in workspace/ (temporary, not trusted)
- Only human-approved content gets written to memory_store/ (persistent, trusted)

The gate handles:
1. Presenting a draft to the human for review
2. Recording the human's decision (approve / reject / edit)
3. Promoting approved corrections into the right memory store
"""

#Feedback: promote_*() luôn mà không check nếu correction_id đã tồn tại trong glossary/entity/style trước đó, có thể dẫn đến duplicates hoặc conflicts nếu cùng một correction được promoted nhiều lần. Chúng ta nên thêm một check để đảm bảo rằng correction_id chưa tồn tại trong target store trước khi thêm, và nếu đã tồn tại thì có thể log một warning hoặc skip promotion để tránh ghi đè hoặc tạo bản sao không cần thiết. Điều này sẽ giúp duy trì tính nhất quán và sạch sẽ của memory store khi có nhiều corrections được promoted theo thời gian.


from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from core.memory import (
    ProjectMemory,
    GlossaryEntry,
    StyleRule,
    Entity,
    Correction,
    CorrectionType,
)


class Decision(str, Enum):
    APPROVED = "approved"       # accept draft as-is
    EDITED = "edited"           # accept with human edits
    REJECTED = "rejected"       # discard draft entirely


@dataclass
class ApprovalSession:
    session_id: str
    project_id: str
    chapter_or_doc: str
    source_text: str
    draft: str                          # AI draft (post-review)
    review_note: str = ""               # from reviewer agent
    decision: Optional[Decision] = None
    final_text: str = ""                # approved output (draft or edited version)
    corrections: list[Correction] = field(default_factory=list)
    decided_at: str = ""

    def is_complete(self) -> bool:
        return self.decision is not None


@dataclass
class PromotionResult:
    promoted_glossary: int = 0
    promoted_entities: int = 0
    promoted_style: int = 0
    promoted_corrections: int = 0


class ApprovalGate:
    """
    Manages the human review step and memory promotion.

    Usage (in pipeline):
        gate = ApprovalGate(memory)
        session = gate.create_session(...)

        # present to human via CLI or UI
        final_text, corrections = human_review(session)

        result = gate.approve(session, final_text, corrections)
        # or: gate.reject(session)
    """

    def __init__(self, memory: ProjectMemory):
        self.memory = memory

    # ------------------------------------------------------------------ #
    # Session lifecycle                                                    #
    # ------------------------------------------------------------------ #

    def create_session(
        self,
        chapter_or_doc: str,
        source_text: str,
        draft: str,
        review_note: str = "",
    ) -> ApprovalSession:
        session_id = f"{self.memory.project_id}-{chapter_or_doc}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return ApprovalSession(
            session_id=session_id,
            project_id=self.memory.project_id,
            chapter_or_doc=chapter_or_doc,
            source_text=source_text,
            draft=draft,
            review_note=review_note,
        )

    def approve(
        self,
        session: ApprovalSession,
        final_text: str,
        corrections: list[Correction] | None = None,
        auto_promote: bool = True,
    ) -> PromotionResult:
        """
        Human approved — finalize, log, and optionally auto-promote corrections.
        """
        session.decision = Decision.APPROVED if final_text == session.draft else Decision.EDITED
        session.final_text = final_text
        session.decided_at = datetime.now().isoformat(timespec="seconds")

        result = PromotionResult()

        if corrections:
            for c in corrections:
                # Log the correction first
                self.memory.corrections.log(c)
                session.corrections.append(c)
                result.promoted_corrections += 1
                
                if auto_promote:
                    if c.correction_type == CorrectionType.TERMINOLOGY:
                        entry = GlossaryEntry(
                            source_term=c.source_term,
                            target_term=c.corrected_text,
                            source_lang=c.source_lang,
                            target_lang=c.target_lang,
                            content_type="general",
                            context_note=c.note or "Auto-promoted from UI review",
                        )
                        self.memory.glossary.add_entry(entry)
                        self.memory.corrections.promote(c.correction_id, "glossary")
                        result.promoted_glossary += 1
                    elif c.correction_type == CorrectionType.ENTITY:
                        entity = Entity(
                            entity_id=c.correction_id,
                            canonical_name=c.corrected_text,
                            source_name=c.source_term or c.original_text,
                            entity_type="character",
                            source_lang=c.source_lang,
                            target_lang=c.target_lang,
                        )
                        self.memory.entities.add_entity(entity)
                        self.memory.corrections.promote(c.correction_id, "entity")
                        result.promoted_entities += 1
                    elif c.correction_type == CorrectionType.STYLE:
                        if self.memory.style.profile:
                            rule = StyleRule(
                                rule_id=c.correction_id,
                                category="general",
                                description=c.note or f"Translate '{c.original_text}' as '{c.corrected_text}'",
                                example_before=c.original_text,
                                example_after=c.corrected_text,
                            )
                            self.memory.style.add_rule(rule)
                            self.memory.corrections.promote(c.correction_id, "style")
                            result.promoted_style += 1

        return result

    def reject(self, session: ApprovalSession) -> None:
        session.decision = Decision.REJECTED
        session.final_text = ""
        session.decided_at = datetime.now().isoformat(timespec="seconds")

    # ------------------------------------------------------------------ #
    # Memory promotion (explicit — always human-triggered)                #
    # ------------------------------------------------------------------ #

    def _is_pending(self, correction_id: str) -> bool:
        existing = next((c for c in self.memory.corrections._corrections if c.correction_id == correction_id), None)
        return existing is not None and existing.status == "pending"

    def promote_correction_to_glossary(
        self,
        correction_id: str,
        source_term: str,
        target_term: str,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
        context_note: str = "",
    ) -> bool:
        """Promote a logged correction into the approved glossary."""
        if not self._is_pending(correction_id):
            return False
        entry = GlossaryEntry(
            source_term=source_term,
            target_term=target_term,
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
            context_note=context_note,
        )
        self.memory.glossary.add_entry(entry)
        self.memory.corrections.promote(correction_id, "glossary")
        return True

    def promote_correction_to_entity(
        self,
        correction_id: str,
        entity: Entity,
    ) -> bool:
        """Promote a logged correction into the entity registry."""
        if not self._is_pending(correction_id):
            return False
        self.memory.entities.add_entity(entity)
        self.memory.corrections.promote(correction_id, "entity")
        return True

    def promote_correction_to_style(
        self,
        correction_id: str,
        rule: StyleRule,
    ) -> bool:
        """Promote a logged correction into the style profile."""
        if not self._is_pending(correction_id):
            return False
        if not self.memory.style.profile:
            raise RuntimeError("Style profile not initialized for this project.")
        self.memory.style.add_rule(rule)
        self.memory.corrections.promote(correction_id, "style")
        return True

    def get_pending_promotions(self) -> dict:
        """
        Show corrections still pending promotion — useful for CLI review prompt.
        Groups by correction_type for easy triage.
        """
        pending = self.memory.corrections.get_pending()
        grouped: dict[str, list] = {}
        for c in pending:
            grouped.setdefault(c.correction_type, []).append(c)
        return grouped

    def get_repeated_patterns(self, min_count: int = 2) -> dict:
        """Surface repeated corrections that are strong candidates for promotion."""
        return self.memory.corrections.get_repeated_patterns(min_count)