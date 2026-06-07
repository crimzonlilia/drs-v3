"""
core/memory — approved memory modules for DRS v3 using Cloudflare R2 object storage.

Usage:
    from core.memory import ProjectMemory

    mem = ProjectMemory("one-piece-vi")
    mem.glossary.as_prompt_context("ja", "vi")
    mem.style.as_prompt_context()
    mem.entities.as_prompt_context("ja", "vi")
"""

from .glossary import Glossary, GlossaryEntry
from .style_profile import StyleMemory, StyleRule, StyleProfile
from .entity_registry import EntityRegistry, Entity
import yaml
from core.utils.r2 import read_text, write_text

class ProjectMemory:
    """
    Convenience wrapper: one object, all memory stores for a project.
    All stores use Cloudflare R2 (or local mock) as persistence.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.glossary = Glossary(project_id)
        self.style = StyleMemory(project_id)
        self.entities = EntityRegistry(project_id)

    def load_style_corrections(self) -> list:
        """
        Loads style corrections from R2.
        """
        path = f"projects/{self.project_id}/memory/style_corrections.yaml"
        content = read_text(path)
        if not content:
            return []
        try:
            return yaml.safe_load(content) or []
        except Exception:
            return []

    def save_style_corrections(self, corrections: list) -> None:
        """
        Saves style corrections to R2.
        """
        path = f"projects/{self.project_id}/memory/style_corrections.yaml"
        write_text(path, yaml.dump(corrections, allow_unicode=True, sort_keys=False))

    def add_style_correction(
        self,
        doc_id: str,
        segment_id: str,
        original_draft: str,
        approved_version: str,
        note: str = "",
        approved_by: str = "human",
        approved_at: str = ""
    ) -> None:
        """
        Appends a style correction entry to style_corrections.yaml in R2.
        Only called when original_draft != approved_version.
        """
        if original_draft == approved_version:
            return
            
        from datetime import datetime
        if not approved_at:
            approved_at = datetime.now().isoformat(timespec="seconds")
            
        corrections = self.load_style_corrections()
        
        # Check if correction for this segment already exists
        corrections = [c for c in corrections if c.get("segment_id") != segment_id]
        
        corr_id = f"corr_{len(corrections) + 1}_{datetime.now().strftime('%M%S')}"
        corrections.append({
            "correction_id": corr_id,
            "doc_id": doc_id,
            "segment_id": segment_id,
            "original_draft": original_draft,
            "approved_version": approved_version,
            "note": note,
            "approved_by": approved_by,
            "approved_at": approved_at
        })
        self.save_style_corrections(corrections)

    def build_prompt_context(self, source_lang: str, target_lang: str) -> str:
        """
        Assemble all approved memory into one context block for LLM injection.
        """
        parts = [
            self.glossary.as_prompt_context(source_lang, target_lang),
            self.style.as_prompt_context(),
            self.entities.as_prompt_context(source_lang, target_lang),
        ]
        return "\n\n".join(p for p in parts if p)

    def build_filtered_prompt_context(self, source_lang: str, target_lang: str, source_text: str) -> str:
        """
        Assemble all approved memory filtered by keywords in the source_text.
        """
        parts = [
            self.glossary.as_prompt_context(source_lang, target_lang, source_text),
            self.style.as_prompt_context(),
            self.entities.as_prompt_context(source_lang, target_lang, source_text),
        ]
        return "\n\n".join(p for p in parts if p)

    def __repr__(self) -> str:
        return (
            f"<ProjectMemory project={self.project_id!r} "
            f"glossary={len(self.glossary)} "
            f"entities={len(self.entities)}>"
        )

__all__ = [
    "ProjectMemory",
    "Glossary", "GlossaryEntry",
    "StyleMemory", "StyleRule", "StyleProfile",
    "EntityRegistry", "Entity",
]