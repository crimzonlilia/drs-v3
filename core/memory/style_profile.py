"""
Style Profile — per-project tone, register, and localization preferences.

Covers things like:
- honorific handling (giữ nguyên vs Việt hoá)
- dialogue register (formal / casual / slang)
- fandom-specific conventions
- content-type-specific rules (manga SFX, fanfic POV voice, etc.)
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
from typing import Optional


@dataclass
class StyleRule:
    rule_id: str              # short slug, e.g. "honorific-handling"
    category: str             # "register" | "honorific" | "sfx" | "dialogue" | "formatting" | "other"
    description: str          # human-readable rule
    example_before: str = ""  # what NOT to do / original
    example_after: str = ""   # approved rendering
    content_type: str = "general"   # "manga" | "fanfic" | "novel" | "general"
    source_lang: str = ""
    target_lang: str = ""
    approved_at: str = ""
    approved_by: str = "human"

    def __post_init__(self):
        if not self.approved_at:
            self.approved_at = datetime.now().isoformat(timespec="seconds")


@dataclass
class StyleProfile:
    project_id: str
    source_lang: str
    target_lang: str
    content_type: str
    # top-level tone note — free text, injected into every prompt
    tone_note: str = ""
    rules: list[StyleRule] = field(default_factory=list)


class StyleMemory:
    """
    Load, query, and save approved style profile for one project.

    File lives at: memory_store/styles/{project_id}.yaml
    """

    def __init__(self, project_id: str, store_root: str | Path = "memory_store/styles"):
        self.project_id = project_id
        self.path = Path(store_root) / f"{project_id}.yaml"
        self._profile: Optional[StyleProfile] = None
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        rules = [StyleRule(**r) for r in raw.pop("rules", [])]
        self._profile = StyleProfile(**raw, rules=rules)

    def save(self) -> None:
        if not self._profile:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self._profile)
        self.path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def init_profile(
        self,
        source_lang: str,
        target_lang: str,
        content_type: str,
        tone_note: str = "",
    ) -> StyleProfile:
        """Create a fresh profile if none exists yet."""
        self._profile = StyleProfile(
            project_id=self.project_id,
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
            tone_note=tone_note,
        )
        self.save()
        return self._profile

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def add_rule(self, rule: StyleRule) -> None:
        """Add or replace a rule by rule_id. Human approval expected before calling."""
        if not self._profile:
            raise RuntimeError("Profile not initialized. Call init_profile first.")
        self._profile.rules = [r for r in self._profile.rules if r.rule_id != rule.rule_id]
        self._profile.rules.append(rule)
        self.save()

    def remove_rule(self, rule_id: str) -> bool:
        if not self._profile:
            return False
        before = len(self._profile.rules)
        self._profile.rules = [r for r in self._profile.rules if r.rule_id != rule_id]
        if len(self._profile.rules) < before:
            self.save()
            return True
        return False

    def update_tone_note(self, note: str) -> None:
        if not self._profile:
            raise RuntimeError("Profile not initialized.")
        self._profile.tone_note = note
        self.save()

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    @property
    def profile(self) -> Optional[StyleProfile]:
        return self._profile

    def get_rules(
        self,
        category: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> list[StyleRule]:
        if not self._profile:
            return []
        rules = self._profile.rules
        if category:
            rules = [r for r in rules if r.category == category]
        if content_type:
            rules = [r for r in rules if r.content_type in (content_type, "general")]
        return rules

    def as_prompt_context(self) -> str:
        """
        Format style profile as a block to inject into LLM prompts.
        """
        if not self._profile:
            return ""

        lines = ["[Style Guide]"]

        if self._profile.tone_note:
            lines.append(f"  Tone: {self._profile.tone_note}")

        for r in self._profile.rules:
            lines.append(f"  [{r.category}] {r.description}")
            if r.example_before and r.example_after:
                lines.append(f"    ✗ {r.example_before}")
                lines.append(f"    ✓ {r.example_after}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        n = len(self._profile.rules) if self._profile else 0
        return f"<StyleMemory project={self.project_id!r} rules={n}>"