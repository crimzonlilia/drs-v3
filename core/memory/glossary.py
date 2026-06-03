"""
Glossary — per-project, per-language-pair terminology store.

Approved terms only live here. Working/draft suggestions stay in workspace,
never written here until user explicitly approves.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
from typing import Optional

#feedback: usage_count +=1 in lookup but never saved back to file — should we save after each lookup to persist usage counts? or is it enough to have it in-memory for the current run?

@dataclass
class GlossaryEntry:
    source_term: str          # Original term (e.g. "先輩", "nakama", "师兄")
    target_term: str          # Approved translation (e.g. "senpai", "đồng đội")
    source_lang: str          # e.g. "ja", "zh", "ko"
    target_lang: str          # e.g. "vi", "en"
    content_type: str         # "manga" | "fanfic" | "novel" | "general"
    context_note: str = ""    # e.g. "giữ nguyên không dịch vì fandom quen"
    approved_at: str = ""
    approved_by: str = "human"
    usage_count: int = 0      # track how often this term appears across runs

    def __post_init__(self):
        if not self.approved_at:
            self.approved_at = datetime.now().isoformat(timespec="seconds")


class Glossary:
    """
    Load, query, and save approved glossary for one project.

    File lives at: memory_store/glossaries/{project_id}.yaml
    Only GlossaryEntry objects approved by user are stored here.
    """

    def __init__(self, project_id: str, store_root: str | Path = "memory_store/glossaries"):
        self.project_id = project_id
        self.path = Path(store_root) / f"{project_id}.yaml"
        self._entries: list[GlossaryEntry] = []
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or []
        self._entries = [GlossaryEntry(**e) for e in raw]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(e) for e in self._entries]
        self.path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Write (approval-gated — caller must confirm before calling)         #
    # ------------------------------------------------------------------ #

    def add_entry(self, entry: GlossaryEntry) -> None:
        """Add or overwrite an approved entry. Call only after human approval."""
        # overwrite if same source+lang pair already exists
        self._entries = [
            e for e in self._entries
            if not (
                e.source_term == entry.source_term
                and e.source_lang == entry.source_lang
                and e.target_lang == entry.target_lang
            )
        ]
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
                return e
        return None

    def lookup_fuzzy(
        self,
        partial: str,
        source_lang: str,
        target_lang: str,
    ) -> list[GlossaryEntry]:
        """Return entries where source_term contains `partial` (case-insensitive)."""
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

    def as_prompt_context(self, source_lang: str, target_lang: str) -> str:
        """
        Format glossary as a compact block to inject into LLM prompts.
        e.g.:
            先輩 → senpai  (giữ nguyên, fandom quen)
            仲間 → đồng đội
        """
        entries = self.get_all(source_lang=source_lang, target_lang=target_lang)
        if not entries:
            return ""
        lines = ["[Glossary]"]
        for e in entries:
            note = f"  ({e.context_note})" if e.context_note else ""
            lines.append(f"  {e.source_term} → {e.target_term}{note}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"<Glossary project={self.project_id!r} entries={len(self)}>"