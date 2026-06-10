from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from core.memory import ProjectMemory
from core.agents.candidate_generator import CandidateGenerator, GenerationResult
from core.workflow.approval_gate import SESSION_CACHE, ApprovalSession
from core.utils.db import execute_query

class TranslationAgent:
    """
    TranslationAgent handles project memory loading, context building,
    memory proposal submission, draft saving, and generating translations.
    """
    
    def __init__(self, memory: ProjectMemory, model: str | None = None):
        self.memory = memory
        self.generator = CandidateGenerator(memory, model=model)
        
    async def translate(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
    ) -> GenerationResult:
        """
        Produce a high-quality translation draft.
        """
        return await self.generator.generate(
            source_text=source_text,
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
        )

    def load_project_memory(
        self,
        doc_id: str,
        source_text: str,
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, Any]:
        """
        Load glossary, entities, styles, and style corrections.
        Filters glossary and entities to only those actually present in the source text.
        """
        # Filtered glossary
        filtered_glossary = [
            {
                "source_term": g.source_term,
                "target_term": g.target_term,
                "strictness": getattr(g, "strictness", "flexible"),
                "context_note": g.context_note
            }
            for g in self.memory.glossary.get_all(source_lang=source_lang, target_lang=target_lang)
            if g.source_term in source_text
        ]
        
        # Fallback to top 5 glossary items by usage count if none matched
        if not filtered_glossary:
            all_glossary = self.memory.glossary.get_all(source_lang=source_lang, target_lang=target_lang)
            sorted_glossary = sorted(all_glossary, key=lambda x: getattr(x, "usage_count", 0), reverse=True)
            filtered_glossary = [
                {
                    "source_term": g.source_term,
                    "target_term": g.target_term,
                    "strictness": getattr(g, "strictness", "flexible"),
                    "context_note": g.context_note
                }
                for g in sorted_glossary[:5]
            ]

        # Filtered entities
        filtered_entities = [
            {
                "entity_id": e.entity_id,
                "canonical_name": e.canonical_name,
                "source_name": e.source_name,
                "entity_type": e.entity_type,
                "pronouns": e.pronouns,
                "notes": e.notes
            }
            for e in self.memory.entities.get_all(source_lang=source_lang, target_lang=target_lang)
            if e.source_name in source_text
        ]
        
        # Fallback to top 5 entities if none matched
        if not filtered_entities:
            all_entities = self.memory.entities.get_all(source_lang=source_lang, target_lang=target_lang)
            sorted_entities = sorted(all_entities, key=lambda x: getattr(x, "mention_count", 0), reverse=True)
            filtered_entities = [
                {
                    "entity_id": e.entity_id,
                    "canonical_name": e.canonical_name,
                    "source_name": e.source_name,
                    "entity_type": e.entity_type,
                    "pronouns": e.pronouns,
                    "notes": e.notes
                }
                for e in sorted_entities[:5]
            ]

        # Styles
        project_styles = [
            {
                "rule_id": s.rule_id,
                "category": s.category,
                "description": s.description
            }
            for s in self.memory.style.get_rules()
        ]

        # Style Corrections
        style_corrections = self.memory.load_style_corrections()

        return {
            "filtered_glossary": filtered_glossary,
            "filtered_entities": filtered_entities,
            "project_styles": project_styles,
            "style_corrections": style_corrections
        }

    async def build_translation_context(
        self,
        doc_id: str,
        segment_id: str,
    ) -> Dict[str, Any]:
        """
        Returns sliding window context (3-5 segments before) and history.
        """
        recent_segments = []
        try:
            rows = await execute_query(
                "SELECT segment_id, source_text, target_text FROM segments "
                "WHERE project_id = ? AND doc_id = ? ORDER BY id DESC LIMIT 5",
                [self.memory.project_id, doc_id]
            )
            if rows:
                recent_segments = [dict(r) for r in reversed(rows)]
        except Exception:
            pass

        return {
            "sliding_window": recent_segments,
            "entity_history": [],
            "term_history": []
        }

    def submit_memory_proposals(
        self,
        session_id: str,
        memory_proposals: List[Dict[str, Any]],
    ) -> bool:
        """
        Write proposals into Session state in RAM.
        """
        session = SESSION_CACHE.get(session_id)
        if not session:
            return False
        session.memory_proposals = memory_proposals
        return True

    def save_translation_draft(
        self,
        session_id: str,
        current_draft: str,
    ) -> bool:
        """
        Store draft into Session in RAM, and auto-save to R2.
        """
        session = SESSION_CACHE.get(session_id)
        if not session:
            return False
        session.current_draft = current_draft
        
        # Flush to R2
        from core.workflow.approval_gate import ApprovalGate
        gate = ApprovalGate(self.memory)
        gate.save_translation_draft(session)
        return True
    async def revise(
        self,
        source_text: str,
        previous_draft: str,
        feedback: str,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
        session_corrections: list[dict] | None = None,
    ) -> GenerationResult:
        """
        Revise draft using feedback and style corrections.
        """
        return await self.generator.revise(
            source_text=source_text,
            previous_draft=previous_draft,
            feedback=feedback,
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
            session_corrections=session_corrections,
        )

    async def close(self):
        await self.generator.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
