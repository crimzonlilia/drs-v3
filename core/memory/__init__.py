"""
core/memory — approved memory modules for DRS v3.

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
from .correction_log import CorrectionLog, Correction, CorrectionType, CorrectionStatus


class ProjectMemory:
    """
    Convenience wrapper: one object, all four memory stores for a project.

    mem = ProjectMemory("my-project")
    mem.glossary   → Glossary
    mem.style      → StyleMemory
    mem.entities   → EntityRegistry
    mem.corrections → CorrectionLog
    """

    def __init__(self, project_id: str, store_root: str = "memory_store"):
        self.project_id = project_id
        self.glossary = Glossary(project_id, f"{store_root}/glossaries")
        self.style = StyleMemory(project_id, f"{store_root}/styles")
        self.entities = EntityRegistry(project_id, f"{store_root}/entities")
        self.corrections = CorrectionLog(project_id, f"{store_root}/corrections")

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

    def __repr__(self) -> str:
        return (
            f"<ProjectMemory project={self.project_id!r} "
            f"glossary={len(self.glossary)} "
            f"entities={len(self.entities)} "
            f"corrections={len(self.corrections)}>"
        )


__all__ = [
    "ProjectMemory",
    "Glossary", "GlossaryEntry",
    "StyleMemory", "StyleRule", "StyleProfile",
    "EntityRegistry", "Entity",
    "CorrectionLog", "Correction", "CorrectionType", "CorrectionStatus",
]