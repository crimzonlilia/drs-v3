"""
Style Checker — verify a draft respects approved style rules.

Unlike terminology/entity checks (which are exact-match based),
style checks are a mix of:
- rule-based pattern checks (e.g. honorifics that should be kept)
- heuristic checks (e.g. register signals)
- LLM-delegated checks (flagged for AI reviewer, not handled here)

This module handles the rule-based layer only.
LLM-level style review lives in core/agents/reviewer.py.
"""

#Feedback: flaw: currently the style checker only handles rule-based checks that can be implemented with simple pattern matching, but many style issues are more subjective and require human judgment (e.g. tone, register, voice consistency). For those cases, we flag them as requires_llm_review=True and pass them to the reviewer agent, but we could potentially enhance the style checker in the future to include some more advanced NLP techniques for detecting certain stylistic issues that are more complex than simple patterns. For now, though, it's probably best to keep it focused on the low-hanging fruit of clear rule violations and let the LLM handle the more subjective stuff until we have a better sense of what specific patterns or signals we could reliably detect for those cases.
#Honorific logic could be expanded in the future to handle more complex cases, such as partial honorifics (e.g. "Tanaka-san" where "Tanaka" is the name and "-san" is the honorific), or cases where the honorific is attached to a different part of the name in the target language. For now, we can start with a simple heuristic that looks for known honorific patterns in the draft text and flags potential issues based on whether the style rule says to keep or remove them. We can always refine this logic later if we find that it's generating too many false positives or missing important cases, but it provides a starting point for catching common honorific handling issues in manga translations.
#actually we dont really need honorific that much but it still affect the feel of translation and it need to convert to the same level of politeness in target language, so it's worth having at least a basic check for it. We can always expand the logic later to handle more complex cases or different languages, but for now it provides a way to catch potential honorific consistency issues that can then be reviewed by a human.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from core.memory import StyleMemory, StyleRule


@dataclass
class StyleFlag:
    rule_id: str
    category: str
    description: str
    violation_detail: str = ""
    context_snippet: str = ""
    suggestion: str = ""
    requires_llm_review: bool = False   # if True, pass to reviewer agent


class StyleChecker:
    """
    Check a draft against approved style rules.

    Rule-based checks run here.
    Soft/subjective checks are flagged as requires_llm_review=True
    and passed to the reviewer agent by the pipeline.

    Usage:
        checker = StyleChecker(style_memory)
        flags = checker.check(draft_text, content_type="manga")
    """

    # Honorific patterns that should survive into target if rule says "keep"
    HONORIFIC_PATTERNS = {
        "ja": ["-san", "-kun", "-chan", "-sama", "-senpai", "-sensei", "-dono", "-tan"],
        "ko": ["-ssi", "-nim", "-oppa", "-unni", "-hyung", "-noona"],
        "zh": ["学长", "学姐", "师兄", "师姐", "大人", "公子"],
    }

    def __init__(self, style_memory: StyleMemory):
        self.style_memory = style_memory

    def check(
        self,
        draft_text: str,
        content_type: str = "general",
        source_lang: Optional[str] = None,
    ) -> list[StyleFlag]:
        flags: list[StyleFlag] = []
        rules = self.style_memory.get_rules(content_type=content_type)

        for rule in rules:
            new_flags = self._apply_rule(rule, draft_text, source_lang)
            flags.extend(new_flags)

        return flags

    # ------------------------------------------------------------------ #

    def _apply_rule(
        self,
        rule: StyleRule,
        draft_text: str,
        source_lang: Optional[str],
    ) -> list[StyleFlag]:
        """Dispatch to the right check method based on category."""

        if rule.category == "honorific":
            return self._check_honorific_rule(rule, draft_text, source_lang)

        if rule.category == "register":
            # Register is subjective — defer to LLM reviewer
            return [StyleFlag(
                rule_id=rule.rule_id,
                category=rule.category,
                description=rule.description,
                violation_detail="Register check requires LLM review",
                suggestion=rule.description,
                requires_llm_review=True,
            )]

        if rule.category == "formatting":
            return self._check_formatting_rule(rule, draft_text)

        if rule.category == "sfx":
            return self._check_sfx_rule(rule, draft_text, source_lang)

        # default: flag for LLM review
        return [StyleFlag(
            rule_id=rule.rule_id,
            category=rule.category,
            description=rule.description,
            violation_detail="Rule requires LLM review",
            requires_llm_review=True,
        )]

    def _check_honorific_rule(
        self,
        rule: StyleRule,
        draft_text: str,
        source_lang: Optional[str],
    ) -> list[StyleFlag]:
        """
        If the rule says keep honorifics, check that known honorifics are present.
        If the rule says remove them, check they don't appear.
        """
        keep_honorifics = "keep" in rule.description.lower() or "giữ" in rule.description.lower()
        lang = source_lang or ""
        patterns = self.HONORIFIC_PATTERNS.get(lang, [])

        flags = []
        for pattern in patterns:
            present = pattern in draft_text
            if keep_honorifics and not present:
                # Could be legit (term just not in this chunk), so soft flag
                flags.append(StyleFlag(
                    rule_id=rule.rule_id,
                    category="honorific",
                    description=rule.description,
                    violation_detail=f"Honorific '{pattern}' may have been dropped",
                    suggestion=f"Check if '{pattern}' should be preserved per style rule",
                    requires_llm_review=True,
                ))
            elif not keep_honorifics and present:
                snippet = self._extract_snippet(draft_text, pattern)
                flags.append(StyleFlag(
                    rule_id=rule.rule_id,
                    category="honorific",
                    description=rule.description,
                    violation_detail=f"Honorific '{pattern}' should be localized, not kept",
                    context_snippet=snippet,
                    suggestion=f"Localize or remove '{pattern}' per style rule",
                ))
        return flags

    def _check_formatting_rule(self, rule: StyleRule, draft_text: str) -> list[StyleFlag]:
        """
        Simple pattern-based formatting checks.
        Example: ellipsis should be "…" not "..." 
        """
        flags = []

        # Common formatting: wrong ellipsis
        if "ellipsis" in rule.description.lower() or "…" in (rule.example_after or ""):
            if "..." in draft_text and "…" not in draft_text:
                flags.append(StyleFlag(
                    rule_id=rule.rule_id,
                    category="formatting",
                    description=rule.description,
                    violation_detail='Used "..." instead of "…"',
                    suggestion='Replace "..." with "…"',
                ))

        # Dash style: em dash vs double hyphen
        if "dash" in rule.description.lower() or "—" in (rule.example_after or ""):
            if "--" in draft_text and "—" not in draft_text:
                flags.append(StyleFlag(
                    rule_id=rule.rule_id,
                    category="formatting",
                    description=rule.description,
                    violation_detail='Used "--" instead of "—"',
                    suggestion='Replace "--" with "—"',
                ))

        return flags

    def _check_sfx_rule(
        self,
        rule: StyleRule,
        draft_text: str,
        source_lang: Optional[str],
    ) -> list[StyleFlag]:
        """
        SFX (sound effects) handling: keep original, translate, or annotate.
        This is manga-specific. Heuristic: if source lang is ja and
        katakana/onomatopoeia appear in draft, flag for review.
        """
        if source_lang != "ja":
            return []

        # Simple heuristic: detect untranslated katakana blocks in draft
        katakana_pattern = re.compile(r"[\u30A0-\u30FF]{2,}")
        matches = katakana_pattern.findall(draft_text)
        if not matches:
            return []

        return [StyleFlag(
            rule_id=rule.rule_id,
            category="sfx",
            description=rule.description,
            violation_detail=f"Possible untranslated SFX in draft: {matches[:3]}",
            suggestion="Verify SFX handling per style rule: " + rule.description,
            requires_llm_review=True,
        )]

    def _extract_snippet(self, text: str, term: str, window: int = 40) -> str:
        idx = text.find(term)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(term) + window)
        return f"...{text[start:end]}..."

    def format_report(self, flags: list[StyleFlag]) -> str:
        if not flags:
            return "✓ No style violations found."
        rule_flags = [f for f in flags if not f.requires_llm_review]
        llm_flags = [f for f in flags if f.requires_llm_review]
        lines = [f"⚠ {len(flags)} style issue(s) ({len(llm_flags)} need LLM review):"]
        for f in flags:
            marker = "🤖" if f.requires_llm_review else "⚠"
            lines.append(f"  {marker} [{f.category}] {f.description}")
            if f.violation_detail:
                lines.append(f"    {f.violation_detail}")
            if f.context_snippet:
                lines.append(f"    context: {f.context_snippet}")
            lines.append(f"    → {f.suggestion}")
        return "\n".join(lines)