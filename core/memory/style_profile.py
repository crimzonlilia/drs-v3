"""
Style Profile — per-project tone, register, and localization preferences using Cloudflare R2.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from core.utils.r2 import read_text, write_text

@dataclass
class StyleRule:
    rule_id: str              # short slug, e.g. "honorific-handling"
    category: str             # "register" | "honorific" | "sfx" | "dialogue" | "formatting" | "other"
    description: str          # human-readable rule
    example_before: str = ""  # violation / original
    example_after: str = ""   # approved rendering
    content_type: str = "general"
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
    tone_note: str = ""
    rules: list[StyleRule] = field(default_factory=list)


class StyleMemory:
    """
    Load, query, and save approved style profile for one project using Cloudflare R2.
    Files live at: projects/{project_id}/memory/{source_lang}_{target_lang}_styles.yaml
    """

    def __init__(self, project_id: str, source_lang: Optional[str] = None, target_lang: Optional[str] = None):
        self.project_id = project_id
        self.source_lang = source_lang.lower() if source_lang else None
        self.target_lang = target_lang.lower() if target_lang else None
        self._profile: Optional[StyleProfile] = None
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        from core.utils.r2 import list_files, read_text
        import re

        if self.source_lang and self.target_lang:
            r2_key = f"projects/{self.project_id}/memory/{self.source_lang}_{self.target_lang}_styles.yaml"
            content = read_text(r2_key)
            if content:
                try:
                    raw = yaml.safe_load(content) or {}
                    rules = [StyleRule(**r) for r in raw.pop("rules", [])]
                    self._profile = StyleProfile(**raw, rules=rules)
                    return
                except Exception:
                    pass
            
            # Legacy fallback
            legacy_key = f"projects/{self.project_id}/memory/styles.yaml"
            legacy_content = read_text(legacy_key)
            if legacy_content:
                try:
                    raw = yaml.safe_load(legacy_content) or {}
                    rules = [StyleRule(**r) for r in raw.pop("rules", [])]
                    legacy_profile = StyleProfile(**raw, rules=rules)
                    
                    # Filter rules and keep tone_note
                    filtered_rules = [
                        r for r in legacy_profile.rules 
                        if r.source_lang.lower() == self.source_lang 
                        and r.target_lang.lower() == self.target_lang
                    ]
                    
                    self._profile = StyleProfile(
                        project_id=self.project_id,
                        source_lang=self.source_lang,
                        target_lang=self.target_lang,
                        content_type=legacy_profile.content_type,
                        tone_note=legacy_profile.tone_note,
                        rules=filtered_rules
                    )
                    self.save()
                except Exception:
                    self._profile = None
            else:
                self._profile = None
        else:
            # Load all
            prefix = f"projects/{self.project_id}/memory/"
            all_files = list_files(prefix)
            self._profile = None
            loaded_pairs = set()
            merged_rules = []
            tone_notes = []
            content_type = "general"
            
            for file_key in all_files:
                filename = file_key.split("/")[-1]
                match = re.match(r"^([a-zA-Z0-9\-]+)_([a-zA-Z0-9\-]+)_styles\.yaml$", filename)
                if match:
                    src_l, tgt_l = match.group(1).lower(), match.group(2).lower()
                    loaded_pairs.add((src_l, tgt_l))
                    content = read_text(file_key)
                    if content:
                        try:
                            raw = yaml.safe_load(content) or {}
                            rules = [StyleRule(**r) for r in raw.pop("rules", [])]
                            prof = StyleProfile(**raw, rules=rules)
                            merged_rules.extend(prof.rules)
                            if prof.tone_note:
                                tone_notes.append(prof.tone_note)
                            content_type = prof.content_type
                        except Exception:
                            pass
                            
            # Legacy fallback
            legacy_key = f"projects/{self.project_id}/memory/styles.yaml"
            legacy_content = read_text(legacy_key)
            if legacy_content:
                try:
                    raw = yaml.safe_load(legacy_content) or {}
                    rules = [StyleRule(**r) for r in raw.pop("rules", [])]
                    legacy_profile = StyleProfile(**raw, rules=rules)
                    
                    non_migrated_rules = [
                        r for r in legacy_profile.rules
                        if (r.source_lang.lower(), r.target_lang.lower()) not in loaded_pairs
                    ]
                    
                    if non_migrated_rules or ((legacy_profile.source_lang.lower(), legacy_profile.target_lang.lower()) not in loaded_pairs):
                        merged_rules.extend(non_migrated_rules)
                        if legacy_profile.tone_note:
                            tone_notes.append(legacy_profile.tone_note)
                        content_type = legacy_profile.content_type
                        
                        # Migrate
                        by_pair = {}
                        for r in non_migrated_rules:
                            by_pair.setdefault((r.source_lang.lower(), r.target_lang.lower()), []).append(r)
                        
                        # Also check the profile's main source/target pair
                        main_pair = (legacy_profile.source_lang.lower(), legacy_profile.target_lang.lower())
                        if main_pair not in loaded_pairs:
                            by_pair.setdefault(main_pair, [])
                            
                        for (sl, tl), pair_rules in by_pair.items():
                            p_key = f"projects/{self.project_id}/memory/{sl}_{tl}_styles.yaml"
                            p_data = asdict(StyleProfile(
                                project_id=self.project_id,
                                source_lang=sl,
                                target_lang=tl,
                                content_type=content_type,
                                tone_note=legacy_profile.tone_note if (sl == legacy_profile.source_lang.lower() and tl == legacy_profile.target_lang.lower()) else "",
                                rules=pair_rules
                            ))
                            write_text(p_key, yaml.dump(p_data, allow_unicode=True, sort_keys=False))
                except Exception:
                    pass
            
            # Create a merged profile for in-memory read representation
            self._profile = StyleProfile(
                project_id=self.project_id,
                source_lang="multi",
                target_lang="multi",
                content_type=content_type,
                tone_note=" | ".join(tone_notes),
                rules=merged_rules
            )

    def save(self) -> None:
        if not self._profile:
            return
            
        if self.source_lang and self.target_lang:
            r2_key = f"projects/{self.project_id}/memory/{self.source_lang}_{self.target_lang}_styles.yaml"
            data = asdict(self._profile)
            write_text(r2_key, yaml.dump(data, allow_unicode=True, sort_keys=False))
        else:
            by_pair = {}
            for r in self._profile.rules:
                key = (r.source_lang.lower() if r.source_lang else "ja", r.target_lang.lower() if r.target_lang else "vi")
                by_pair.setdefault(key, []).append(r)
                
            for (sl, tl), rules in by_pair.items():
                r2_key = f"projects/{self.project_id}/memory/{sl}_{tl}_styles.yaml"
                data = asdict(StyleProfile(
                    project_id=self.project_id,
                    source_lang=sl,
                    target_lang=tl,
                    content_type=self._profile.content_type,
                    tone_note=self._profile.tone_note,
                    rules=rules
                ))
                write_text(r2_key, yaml.dump(data, allow_unicode=True, sort_keys=False))

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
            self.init_profile(
                source_lang=rule.source_lang or self.source_lang or "ja",
                target_lang=rule.target_lang or self.target_lang or "vi",
                content_type=rule.content_type or "general"
            )
        self._profile.rules = [r for r in self._profile.rules if r.rule_id != rule.rule_id]
        self._profile.rules.append(rule)
        
        sl = (rule.source_lang or self.source_lang or "ja").lower()
        tl = (rule.target_lang or self.target_lang or "vi").lower()
        
        pair_rules = [
            r for r in self._profile.rules 
            if (r.source_lang.lower() if r.source_lang else "ja") == sl 
            and (r.target_lang.lower() if r.target_lang else "vi") == tl
        ]
        r2_key = f"projects/{self.project_id}/memory/{sl}_{tl}_styles.yaml"
        data = asdict(StyleProfile(
            project_id=self.project_id,
            source_lang=sl,
            target_lang=tl,
            content_type=rule.content_type or self._profile.content_type,
            tone_note=self._profile.tone_note,
            rules=pair_rules
        ))
        write_text(r2_key, yaml.dump(data, allow_unicode=True, sort_keys=False))

    def remove_rule(self, rule_id: str) -> bool:
        if not self._profile:
            return False
        before = len(self._profile.rules)
        rule_to_remove = next((r for r in self._profile.rules if r.rule_id == rule_id), None)
        if not rule_to_remove:
            return False
            
        sl = (rule_to_remove.source_lang or self.source_lang or "ja").lower()
        tl = (rule_to_remove.target_lang or self.target_lang or "vi").lower()
        
        self._profile.rules = [r for r in self._profile.rules if r.rule_id != rule_id]
        
        if len(self._profile.rules) < before:
            pair_rules = [
                r for r in self._profile.rules 
                if (r.source_lang.lower() if r.source_lang else "ja") == sl 
                and (r.target_lang.lower() if r.target_lang else "vi") == tl
            ]
            r2_key = f"projects/{self.project_id}/memory/{sl}_{tl}_styles.yaml"
            data = asdict(StyleProfile(
                project_id=self.project_id,
                source_lang=sl,
                target_lang=tl,
                content_type=self._profile.content_type,
                tone_note=self._profile.tone_note,
                rules=pair_rules
            ))
            write_text(r2_key, yaml.dump(data, allow_unicode=True, sort_keys=False))
            return True
        return False

    def update_tone_note(self, note: str) -> None:
        if not self._profile:
            self.init_profile(
                source_lang=self.source_lang or "ja",
                target_lang=self.target_lang or "vi",
                content_type="general",
                tone_note=note
            )
        else:
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