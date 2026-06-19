"""
Entity Registry — track characters, proper nouns, relationships, and
world-specific facts across chapters/documents using Cloudflare R2.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List

from core.utils.r2 import read_text, write_text

@dataclass
class Entity:
    entity_id: str              # slug, e.g. "luffy", "izumi-sensei"
    canonical_name: str         # approved rendered name in target lang
    source_name: str            # original name in source
    entity_type: str            # "character" | "place" | "title" | "faction" | "term" | "ship"
    source_lang: str
    target_lang: str
    pronouns: str = ""          # e.g. "anh/hắn", "cô/nàng"
    aliases: list[str] = field(default_factory=list)
    notes: str = ""
    content_type: str = "general"
    approved_at: str = ""
    approved_by: str = "human"
    mention_count: int = 0      # incremented during consistency checks

    def __post_init__(self):
        if not self.approved_at:
            self.approved_at = datetime.now().isoformat(timespec="seconds")
        if self.aliases is None:
            self.aliases = []


class EntityRegistry:
    """
    Load, query, and save approved entities for one project using Cloudflare R2.
    File lives at: projects/{project_id}/memory/entities.yaml
    Internal structure uses dictionary mapping entity_id -> Entity for O(1) access.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.r2_key = f"projects/{project_id}/memory/entities.yaml"
        self._entities: dict[str, Entity] = {}   # keyed by entity_id
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        content = read_text(self.r2_key)
        if not content:
            self._entities = {}
            return
        try:
            raw = yaml.safe_load(content) or []
            self._entities = {}
            for item in raw:
                e = Entity(**item)
                self._entities[e.entity_id] = e
        except Exception:
            self._entities = {}

    def save(self) -> None:
        data = [asdict(e) for e in self._entities.values()]
        write_text(self.r2_key, yaml.dump(data, allow_unicode=True, sort_keys=False))

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def add_entity(self, entity: Entity) -> None:
        """Add or overwrite entity by entity_id. Human approval expected before calling."""
        self._entities[entity.entity_id] = entity
        self.save()

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id in self._entities:
            del self._entities[entity_id]
            self.save()
            return True
        return False

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def get(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def find_by_source_name(self, source_name: str, source_lang: str) -> Optional[Entity]:
        """Match against source_name or any alias."""
        for e in self._entities.values():
            if e.source_lang != source_lang:
                continue
            if e.source_name == source_name or source_name in e.aliases:
                e.mention_count += 1
                return e
        return None

    def search(self, query: str) -> list[Entity]:
        """Fuzzy search across canonical_name, source_name, aliases."""
        q = query.lower()
        results = []
        for e in self._entities.values():
            haystack = [e.canonical_name, e.source_name] + e.aliases
            if any(q in h.lower() for h in haystack):
                results.append(e)
        return results

    def get_all(
        self,
        entity_type: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
    ) -> list[Entity]:
        result = list(self._entities.values())
        if entity_type:
            result = [e for e in result if e.entity_type == entity_type]
        if source_lang:
            result = [e for e in result if e.source_lang == source_lang]
        if target_lang:
            result = [e for e in result if e.target_lang == target_lang]
        return result

    def as_prompt_context(self, source_lang: str, target_lang: str, source_text: Optional[str] = None) -> str:
        """
        Compact block for LLM prompt injection.
        If source_text is provided, only entities whose source_name or aliases appear in the text are included.
        """
        entities = self.get_all(source_lang=source_lang, target_lang=target_lang)
        if source_text:
            filtered = []
            for e in entities:
                if e.source_name in source_text or any(a in source_text for a in e.aliases):
                    filtered.append(e)
            entities = filtered
            
        if not entities:
            return ""

        grouped: dict[str, list[Entity]] = {}
        for e in entities:
            grouped.setdefault(e.entity_type, []).append(e)

        lines = ["[Entities]"]
        for etype, items in grouped.items():
            lines.append(f"  [{etype}]")
            for e in items:
                pronoun_note = f" | pronouns: {e.pronouns}" if e.pronouns else ""
                note = f" | {e.notes}" if e.notes else ""
                lines.append(f"    - '{e.source_name}' -> '{e.canonical_name}'{pronoun_note}{note}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._entities)

    def __repr__(self) -> str:
        return f"<EntityRegistry project={self.project_id!r} entities={len(self)}>"