"""
Approval Gate — in-memory session caching and Cloudflare R2/D1 promotion flow.
Defines Decision, Correction, and Promotion types.
"""

from __future__ import annotations

import json
import yaml
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from core.memory import (
    ProjectMemory,
    GlossaryEntry,
    StyleRule,
    Entity
)
from core.utils.db import execute_query
from core.utils.r2 import read_text, write_text

class Decision(str, Enum):
    APPROVED = "approved"       # accept draft as-is
    EDITED = "edited"           # accept with human edits
    REJECTED = "rejected"       # discard draft entirely

class CorrectionType(str, Enum):
    TERMINOLOGY = "terminology"   # wrong term translation
    ENTITY = "entity"             # wrong name/pronoun
    STYLE = "style"               # tone/register issue
    FACTUAL = "factual"           # wrong in-world fact
    OTHER = "other"

@dataclass
class ApprovalSession:
    session_id: str
    project_id: str
    doc_id: str                  # Changed from chapter_or_doc
    source_text: str
    current_draft: str           # Changed from draft
    audit_report: str = ""       # Changed from review_note
    source_lang: str = "ja"
    target_lang: str = "vi"
    decision: Optional[Decision] = None
    final_text: str = ""
    decided_at: str = ""
    validation_issues: List[Dict[str, Any]] = field(default_factory=list)
    editorial_score: Dict[str, float] = field(default_factory=dict)
    editorial_feedback: List[str] = field(default_factory=list)
    memory_proposals: List[Dict[str, Any]] = field(default_factory=list) # Changed from corrections
    pipeline_status: Dict[str, str] = field(default_factory=lambda: {
        "upload": "idle",
        "ocr": "idle",
        "context_retrieval": "idle",
        "draft_translation": "idle",
        "review": "idle",
        "approve": "idle",
        "render": "idle"
    })
    pipeline_error: str = ""
    model_name: str = ""

    def is_complete(self) -> bool:
        return self.decision is not None

def session_from_dict(d: dict) -> ApprovalSession:
    decision_val = d.get("decision")
    decision = Decision(decision_val) if decision_val else None
    
    # Set default pipeline status if missing
    default_status = {
        "upload": "idle",
        "ocr": "idle",
        "context_retrieval": "idle",
        "draft_translation": "idle",
        "review": "idle",
        "approve": "idle",
        "render": "idle"
    }
    
    return ApprovalSession(
        session_id=d["session_id"],
        project_id=d["project_id"],
        doc_id=d["doc_id"],
        source_text=d["source_text"],
        current_draft=d["current_draft"],
        audit_report=d.get("audit_report", ""),
        source_lang=d.get("source_lang", "ja"),
        target_lang=d.get("target_lang", "vi"),
        decision=decision,
        final_text=d.get("final_text", ""),
        decided_at=d.get("decided_at", ""),
        validation_issues=d.get("validation_issues", []),
        editorial_score=d.get("editorial_score", {}),
        editorial_feedback=d.get("editorial_feedback", []),
        memory_proposals=d.get("memory_proposals", []),
        pipeline_status=d.get("pipeline_status", default_status),
        pipeline_error=d.get("pipeline_error", ""),
        model_name=d.get("model_name", "")
    )

@dataclass
class PromotionResult:
    promoted_glossary: int = 0
    promoted_entities: int = 0
    promoted_style: int = 0
    promoted_corrections: int = 0

# Ephemeral RAM session cache (keyed by session_id)
SESSION_CACHE: Dict[str, ApprovalSession] = {}

class ApprovalGate:
    """
    Manages the in-memory human review sessions and cloud Promotion Flow.
    """

    def __init__(self, memory: ProjectMemory):
        self.memory = memory

    # ------------------------------------------------------------------ #
    # Session lifecycle                                                    #
    # ------------------------------------------------------------------ #

    def create_session(
        self,
        doc_id: str,
        source_text: str,
        current_draft: str,
        audit_report: str = "",
        source_lang: str = "ja",
        target_lang: str = "vi",
        validation_issues: List[Dict[str, Any]] = None,
        editorial_score: Dict[str, float] = None,
        editorial_feedback: List[str] = None,
        memory_proposals: List[Dict[str, Any]] = None,
        model_name: str = ""
    ) -> ApprovalSession:
        session_id = f"{self.memory.project_id}-{doc_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        session = ApprovalSession(
            session_id=session_id,
            project_id=self.memory.project_id,
            doc_id=doc_id,
            source_text=source_text,
            current_draft=current_draft,
            audit_report=audit_report,
            source_lang=source_lang,
            target_lang=target_lang,
            validation_issues=validation_issues if validation_issues is not None else [],
            editorial_score=editorial_score if editorial_score is not None else {},
            editorial_feedback=editorial_feedback if editorial_feedback is not None else [],
            memory_proposals=memory_proposals if memory_proposals is not None else [],
            model_name=model_name
        )
        # Store in RAM cache
        SESSION_CACHE[session_id] = session
        
        # Save to R2 initially
        self.save_translation_draft(session)
        
        return session

    def load_session(self, session_id: str) -> Optional[ApprovalSession]:
        return SESSION_CACHE.get(session_id)

    def save_translation_draft(self, session: ApprovalSession) -> None:
        """
        Saves current_draft and full GraphState to R2 for cold-resume support.
        """
        doc_prefix = f"projects/{session.project_id}/docs/{session.doc_id}/"
        # 1. Save plain-text draft.md preview
        write_text(f"{doc_prefix}draft.md", session.current_draft)
        # 2. Save full JSON draft_state.json
        state_data = asdict(session)
        write_text(f"{doc_prefix}draft_state.json", json.dumps(state_data, ensure_ascii=False, indent=2))

    async def approve(
        self,
        session: ApprovalSession,
        auto_promote: bool = True,
        approved_by_user_id: int = 1
    ) -> PromotionResult:
        """
        Finalizes draft, pushes changes to R2 memory, D1 database segments,
        master_index and output versions, and purges the session.
        """
        final_text = session.current_draft
        session.decision = Decision.APPROVED
        session.final_text = final_text
        session.decided_at = datetime.now().isoformat(timespec="seconds")

        result = PromotionResult()
        
        # 1. Promote memory proposals into R2
        if session.memory_proposals and auto_promote:
            for p in session.memory_proposals:
                p_type = p.get("type")
                source_term = p.get("source_term", "")
                target_term = p.get("target_term", "")
                strictness = p.get("strictness", "flexible")
                note = p.get("note", "")
                
                if strictness not in ["fixed", "flexible", "context_dependent"]:
                    strictness = "flexible"

                if p_type == "glossary":
                    entry = GlossaryEntry(
                        source_term=source_term,
                        target_term=target_term,
                        source_lang=session.source_lang,
                        target_lang=session.target_lang,
                        content_type="general",
                        strictness=strictness,
                        context_note=note or "Auto-promoted from UI review",
                    )
                    self.memory.glossary.add_entry(entry)
                    result.promoted_glossary += 1
                    result.promoted_corrections += 1
                elif p_type == "entity":
                    entity_id = p.get("entity_id") or f"ent_{str(uuid.uuid4())[:8]}"
                    entity = Entity(
                        entity_id=entity_id,
                        canonical_name=target_term,
                        source_name=source_term,
                        entity_type=p.get("entity_type", "character"),
                        source_lang=session.source_lang,
                        target_lang=session.target_lang,
                        pronouns=p.get("pronouns", ""),
                        notes=note or p.get("notes", "")
                    )
                    self.memory.entities.add_entity(entity)
                    result.promoted_entities += 1
                    result.promoted_corrections += 1
                elif p_type == "style":
                    rule_id = p.get("rule_id") or f"style_{str(uuid.uuid4())[:8]}"
                    rule = StyleRule(
                        rule_id=rule_id,
                        category=p.get("category", "general"),
                        description=note or f"Translate '{source_term}' as '{target_term}'",
                        example_before=source_term,
                        example_after=target_term,
                        source_lang=session.source_lang,
                        target_lang=session.target_lang
                    )
                    self.memory.style.add_rule(rule)
                    result.promoted_style += 1
                    result.promoted_corrections += 1

        # Save style corrections if user changed the initial draft (can check against draft or source)
        # Note: If no style corrections, we can still record human corrections for future learning
        self.memory.add_style_correction(
            doc_id=session.doc_id,
            segment_id=f"{session.doc_id}_seg_{datetime.now().strftime('%M%S')}",
            original_draft=session.source_text,  # Fallback reference
            approved_version=final_text,
            note=f"Corrected via approval session {session.session_id}",
            approved_by=str(approved_by_user_id),
            approved_at=session.decided_at
        )

        # 2. Write to D1 database segments (idempotent INSERT OR REPLACE)
        segment_id = f"seg_{datetime.now().strftime('%H%M%S')}"
        sql = """
        INSERT OR REPLACE INTO segments 
        (project_id, doc_id, segment_id, segment_type, source_text, target_text, approved_by, approved_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await execute_query(sql, [
            session.project_id,
            session.doc_id,
            segment_id,
            "paragraph",
            session.source_text,
            final_text,
            approved_by_user_id,
            session.decided_at
        ])

        # 3. Update master_index/{doc_id}.yaml in R2
        master_index_path = f"projects/{session.project_id}/memory/master_index/{session.doc_id}.yaml"
        segments_data = await execute_query(
            "SELECT segment_id, source_text FROM segments WHERE project_id = ? AND doc_id = ?",
            [session.project_id, session.doc_id]
        )
        
        entities_list = self.memory.entities.get_all(source_lang=session.source_lang, target_lang=session.target_lang)
        glossary_list = self.memory.glossary.get_all(source_lang=session.source_lang, target_lang=session.target_lang)
        
        entities_index = {}
        terms_index = {}
        
        for seg in segments_data:
            text = seg["source_text"]
            seg_id = seg["segment_id"]
            
            for ent in entities_list:
                if ent.source_name in text:
                    entities_index.setdefault(ent.entity_id, {}).setdefault("segment_ids", []).append(seg_id)
            for g in glossary_list:
                if g.source_term in text:
                    terms_index.setdefault(g.source_term, {}).setdefault("segment_ids", []).append(seg_id)
                    
        master_index = {
            "doc_id": session.doc_id,
            "entities": entities_index,
            "terms": terms_index
        }
        write_text(master_index_path, yaml.dump(master_index, allow_unicode=True, sort_keys=False))

        # 4. Save progressive outputs/translation_v{n}.json in R2
        output_prefix = f"projects/{session.project_id}/docs/{session.doc_id}/outputs/"
        all_keys = list_keys_with_prefix(output_prefix)
        v_num = 1
        for key in all_keys:
            if "translation_v" in key and key.endswith(".json"):
                try:
                    num = int(key.split("translation_v")[-1].split(".json")[0])
                    if num >= v_num:
                        v_num = num + 1
                except Exception:
                    pass
                    
        output_data = {
            "doc_id": session.doc_id,
            "version": v_num,
            "approved_text": final_text,
            "source_text": session.source_text,
            "decided_at": session.decided_at
        }
        write_text(f"{output_prefix}translation_v{v_num}.json", json.dumps(output_data, ensure_ascii=False, indent=2))

        # 5. Overwrite outputs/metadata.json in R2
        latest_meta = {
            "latest_version": v_num,
            "approved_by": str(approved_by_user_id),
            "approved_at": session.decided_at,
            "segment_count": len(segments_data)
        }
        write_text(f"{output_prefix}metadata.json", json.dumps(latest_meta, ensure_ascii=False, indent=2))

        # Index approved content into knowledge_base in background
        import asyncio
        from core.utils.kb_service import index_document_in_kb
        asyncio.create_task(index_document_in_kb(session.project_id, session.doc_id, final_text))

        # 6. Purge session from RAM cache and delete temporary draft_state
        if session.session_id in SESSION_CACHE:
            del SESSION_CACHE[session.session_id]

        # Delete temporary draft files from R2
        doc_prefix = f"projects/{session.project_id}/docs/{session.doc_id}/"
        from core.utils.r2 import delete_file
        delete_file(f"{doc_prefix}draft.md")
        delete_file(f"{doc_prefix}draft_state.json")

        return result

    def reject(self, session: ApprovalSession) -> None:
        session.decision = Decision.REJECTED
        session.final_text = ""
        session.decided_at = datetime.now().isoformat(timespec="seconds")
        if session.session_id in SESSION_CACHE:
            del SESSION_CACHE[session.session_id]

        # Delete temporary draft files from R2
        doc_prefix = f"projects/{session.project_id}/docs/{session.doc_id}/"
        from core.utils.r2 import delete_file
        delete_file(f"{doc_prefix}draft.md")
        delete_file(f"{doc_prefix}draft_state.json")


def list_keys_with_prefix(prefix: str) -> List[str]:
    """
    Helper to list R2/Mock keys starting with a prefix.
    """
    from core.utils.r2 import list_files
    return list_files(prefix)