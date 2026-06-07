"""
Glossary — per-project, per-language-pair terminology store.
Only approved terms are stored here, using Cloudflare R2 as backend.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.utils.r2 import read_text, write_text

@dataclass
class GlossaryEntry:
    source_term: str          # Original term (e.g. "先輩", "海賊王")
    target_term: str          # Approved default translation (e.g. "senpai", "Vua Hải Tặc")
    source_lang: str          # e.g. "ja"
    target_lang: str          # e.g. "vi"
    content_type: str         # "manga" | "fanfic" | "novel" | "general"
    strictness: str = "fixed" # "fixed" | "flexible" | "context_dependent"
    context_variants: List[Dict[str, str]] = field(default_factory=list) # e.g. [{"context": "formal", "target_term": "tiền bối"}]
    context_note: str = ""    # e.g. "Giữ nguyên senpai cho đúng không khí"
    approved_at: str = ""
    approved_by: str = "human"
    usage_count: int = 0      # track usage across runs

    def __post_init__(self):
        if not self.approved_at:
            self.approved_at = datetime.now().isoformat(timespec="seconds")
        if self.context_variants is None:
            self.context_variants = []


class Glossary:
    """
    Load, query, and save approved glossary for one project using Cloudflare R2.
    File lives at R2: projects/{project_id}/memory/glossary.yaml
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.r2_key = f"projects/{project_id}/memory/glossary.yaml"
        self._entries: list[GlossaryEntry] = []
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        content = read_text(self.r2_key)
        if not content:
            self._entries = []
            return
        try:
            raw = yaml.safe_load(content) or []
            self._entries = [GlossaryEntry(**e) for e in raw]
        except Exception:
            self._entries = []

    def save(self) -> None:
        data = [asdict(e) for e in self._entries]
        write_text(self.r2_key, yaml.dump(data, allow_unicode=True, sort_keys=False))

    # ------------------------------------------------------------------ #
    # Write (approval-gated — caller must confirm before calling)         #
    # ------------------------------------------------------------------ #

    def add_entry(self, entry: GlossaryEntry) -> None:
        """Add or merge an approved entry. Dedupes by source_term + source_lang + target_lang."""
        existing = None
        for e in self._entries:
            if (
                e.source_term == entry.source_term
                and e.source_lang == entry.source_lang
                and e.target_lang == entry.target_lang
            ):
                existing = e
                break

        if existing:
            # Merge variants and update usage
            existing.usage_count = max(existing.usage_count, entry.usage_count) + 1
            existing.approved_at = datetime.now().isoformat(timespec="seconds")
            existing.strictness = entry.strictness
            existing.context_note = entry.context_note or existing.context_note
            existing.target_term = entry.target_term or existing.target_term
            
            # Merge context variants
            existing_contexts = {v["context"]: v["target_term"] for v in existing.context_variants}
            for v in entry.context_variants:
                existing_contexts[v["context"]] = v["target_term"]
            existing.context_variants = [{"context": k, "target_term": v} for k, v in existing_contexts.items()]
        else:
            self._entries.append(entry)
            
        self.save()

    def remove_entry(self, source_term: str, source_lang: str, target_lang: str) -> bool:
        before = len(self._entries)
        self._entries = [
            e for e in self._entries
            if not (
                e.source_term == source_term
                and e.source_lang == source_lang
                and e.target_lang == target_lang
            )
        ]
        if len(self._entries) < before:
            self.save()
            return True
        return False

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def lookup(
        self,
        source_term: str,
        source_lang: str,
        target_lang: str,
    ) -> Optional[GlossaryEntry]:
        for e in self._entries:
            if (
                e.source_term == source_term
                and e.source_lang == source_lang
                and e.target_lang == target_lang
            ):
                e.usage_count += 1
                self.save()
                return e
        return None

    def lookup_fuzzy(
        self,
        partial: str,
        source_lang: str,
        target_lang: str,
    ) -> list[GlossaryEntry]:
        p = partial.lower()
        return [
            e for e in self._entries
            if p in e.source_term.lower()
            and e.source_lang == source_lang
            and e.target_lang == target_lang
        ]

    def get_all(
        self,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> list[GlossaryEntry]:
        result = self._entries
        if source_lang:
            result = [e for e in result if e.source_lang == source_lang]
        if target_lang:
            result = [e for e in result if e.target_lang == target_lang]
        if content_type:
            result = [e for e in result if e.content_type == content_type]
        return result

    def as_prompt_context(self, source_lang: str, target_lang: str, source_text: Optional[str] = None) -> str:
        """
        Format glossary as a prompt context block.
        If source_text is provided, only terms matching the text are included.
        """
        entries = self.get_all(source_lang=source_lang, target_lang=target_lang)
        if source_text:
            entries = [e for e in entries if e.source_term in source_text]
            
        if not entries:
            return ""
        lines = ["[Glossary]"]
        for e in entries:
            note = f" ({e.context_note})" if e.context_note else ""
            if e.strictness == "fixed":
                lines.append(f"  - Term: '{e.source_term}' -> '{e.target_term}' [Strictness: fixed]{note}")
            elif e.strictness == "flexible":
                variants_str = ", ".join([f"if {v['context']}: '{v['target_term']}'" for v in e.context_variants])
                v_desc = f" (Variants: {variants_str})" if variants_str else ""
                lines.append(f"  - Term: '{e.source_term}' -> default: '{e.target_term}' [Strictness: flexible]{v_desc}{note}")
            elif e.strictness == "context_dependent":
                lines.append(f"  - Term: '{e.source_term}' -> [Strictness: context_dependent] (requires manual translation review){note}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"<Glossary project={self.project_id!r} entries={len(self)}>"