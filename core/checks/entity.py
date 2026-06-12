"""
Entity Checker — verify character names, pronouns, and proper nouns
are rendered consistently in a draft.

Two kinds of violations:
1. Wrong name: source name present but approved canonical name missing.
2. Pronoun drift: a character is referred to by an unapproved pronoun set.
"""

#Feedback: Alias logic is a bit tricky — we want to allow aliases to be used in the source text for matching against the original, since the original might use either the source name or an alias. But in the draft, we want to flag any use of an alias instead of the canonical name, since that indicates a consistency issue where the approved name isn't being used. So in the check_aliases function, we look for any aliases appearing in the draft and flag those as violations if the canonical name isn't also present. This way we can catch cases where the draft is using an unapproved name instead of the canonical one, while still allowing for flexibility in how characters are referred to in the source text.
#Pronoun drift is a bit noisy, a sentence may not always include a pronoun, and the approved set may not be exhaustive, but it's still a useful heuristic to catch potential consistency issues that can then be reviewed by a human. We can always refine the logic later if we find it's generating too many false positives or missing important cases, but for now it provides a way to surface potential pronoun inconsistencies for human review without requiring perfect accuracy.


from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from core.memory import EntityRegistry, Entity


@dataclass
class EntityFlag:
    entity_id: str
    source_name: str
    canonical_name: str
    violation_type: str         # "wrong_name" | "pronoun_drift" | "alias_leak"
    detail: str = ""
    context_snippet: str = ""
    suggestion: str = ""


class EntityChecker:
    """
    Check a draft for entity name and pronoun consistency.

    Usage:
        checker = EntityChecker(registry)
        flags = checker.check(source_text, draft_text, "ja", "vi")
    """

    def __init__(self, registry: EntityRegistry):
        self.registry = registry

    def check(
        self,
        source_text: str,
        draft_text: str,
        source_lang: str,
        target_lang: str,
    ) -> list[EntityFlag]:
        flags: list[EntityFlag] = []
        entities = self.registry.get_all(source_lang=source_lang, target_lang=target_lang)

        for entity in entities:
            # 1. Name check: if source_name appears in source, canonical must appear in draft
            if entity.source_name in source_text:
                flags += self._check_name(entity, draft_text)

            # 2. Alias leak: aliases should not appear in draft — canonical should
            flags += self._check_aliases(entity, draft_text)

            # 3. Pronoun drift: if pronouns are defined, check none are violated
            if entity.pronouns:
                flags += self._check_pronouns(entity, draft_text)

        return flags

    # ------------------------------------------------------------------ #

    def _check_name(self, entity: Entity, draft_text: str) -> list[EntityFlag]:
        if entity.canonical_name.lower() in draft_text.lower():
            return []
        # canonical name missing — wrong name or untranslated
        snippet = self._extract_snippet(draft_text, entity.source_name)
        return [EntityFlag(
            entity_id=entity.entity_id,
            source_name=entity.source_name,
            canonical_name=entity.canonical_name,
            violation_type="wrong_name",
            detail=f"'{entity.canonical_name}' not found in draft",
            context_snippet=snippet,
            suggestion=f"Use approved name: '{entity.canonical_name}'",
        )]

    def _check_aliases(self, entity: Entity, draft_text: str) -> list[EntityFlag]:
        flags = []
        for alias in entity.aliases:
            if alias.lower() in draft_text.lower() and entity.canonical_name.lower() not in draft_text.lower():
                snippet = self._extract_snippet(draft_text, alias)
                flags.append(EntityFlag(
                    entity_id=entity.entity_id,
                    source_name=entity.source_name,
                    canonical_name=entity.canonical_name,
                    violation_type="alias_leak",
                    detail=f"Alias '{alias}' used instead of canonical '{entity.canonical_name}'",
                    context_snippet=snippet,
                    suggestion=f"Replace '{alias}' with '{entity.canonical_name}'",
                ))
        return flags

    def _check_pronouns(self, entity: Entity, draft_text: str) -> list[EntityFlag]:
        """
        Approved pronouns are stored as comma-separated string, e.g. "anh/hắn".
        We can't exhaustively check all Vietnamese pronouns, but we flag if
        the entity appears in draft without any approved pronoun nearby.

        This is a lightweight heuristic — enough for human review prompting.
        """
        if entity.canonical_name.lower() not in draft_text.lower():
            return []  # entity not mentioned, nothing to check

        approved = [p.strip() for p in re.split(r"[/,]", entity.pronouns) if p.strip()]
        # find positions of canonical name and check window around each
        flags = []
        for match in re.finditer(re.escape(entity.canonical_name), draft_text, re.IGNORECASE):
            start = max(0, match.start() - 60)
            end = min(len(draft_text), match.end() + 60)
            window = draft_text[start:end]
            if not any(p.lower() in window.lower() for p in approved):
                # no approved pronoun nearby — possible drift, surface for human
                flags.append(EntityFlag(
                    entity_id=entity.entity_id,
                    source_name=entity.source_name,
                    canonical_name=entity.canonical_name,
                    violation_type="pronoun_drift",
                    detail=f"No approved pronoun ({entity.pronouns}) near '{entity.canonical_name}'",
                    context_snippet=f"...{window}...",
                    suggestion=f"Verify pronoun — approved set: {entity.pronouns}",
                ))
                break  # one flag per entity per check is enough
        return flags

    def _extract_snippet(self, text: str, term: str, window: int = 50) -> str:
        idx = text.find(term)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(term) + window)
        return f"...{text[start:end]}..."

    def format_report(self, flags: list[EntityFlag]) -> str:
        if not flags:
            return "✓ No entity consistency issues found."
        lines = [f"⚠ {len(flags)} entity issue(s):"]
        for f in flags:
            lines.append(f"  • [{f.violation_type}] {f.source_name} → {f.canonical_name}")
            lines.append(f"    {f.detail}")
            if f.context_snippet:
                lines.append(f"    context: {f.context_snippet}")
            lines.append(f"    → {f.suggestion}")
        return "\n".join(lines)