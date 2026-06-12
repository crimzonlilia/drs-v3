"""
Terminology Checker — scan a translated draft for glossary violations.

Looks for approved source terms that appear in the original text but whose
approved target rendering is missing or inconsistent in the draft.
"""

#Feedback: if entry.target_term in draft_text raw substring match is too strict — we should do a more flexible check that allows for some variation (e.g. honorifics, particles, slight rephrasing) while still flagging cases where the approved term is not used at all. Maybe we can use a simple fuzzy matching approach or check for the presence of key components of the approved term rather than an exact match? We want to catch cases where the term is basically correct but has minor deviations that might be acceptable, while still flagging cases where the term is missing or significantly altered.
#_find_nearby() kinda weak, but it's just a heuristic to see if the source term leaked into the draft untranslated, which is a common error. For more complex cases of incorrect terminology, we might not be able to reliably detect what the incorrect term was without more advanced NLP techniques, so for now we'll just flag that the approved term is missing and optionally show the nearby context from the source text to help the human reviewer identify what went wrong. The main goal is to catch cases where the approved term is not used at all, which is a strong signal of a potential issue, while allowing for some flexibility in how the term is rendered in the draft.


from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from core.memory import Glossary, GlossaryEntry


@dataclass
class TermFlag:
    source_term: str
    expected: str           # approved target term
    found: Optional[str]    # what appeared in draft (None = missing entirely)
    context_snippet: str = ""
    suggestion: str = ""


class TerminologyChecker:
    """
    Check a draft translation against the project glossary.

    Usage:
        checker = TerminologyChecker(glossary)
        flags = checker.check(source_text, draft_text, "ja", "vi")
    """

    def __init__(self, glossary: Glossary):
        self.glossary = glossary

    def check(
        self,
        source_text: str,
        draft_text: str,
        source_lang: str,
        target_lang: str,
    ) -> list[TermFlag]:
        """
        For every approved glossary entry whose source_term appears in source_text,
        verify the approved target_term appears in draft_text.
        Returns a list of TermFlag for any violations.
        """
        entries = self.glossary.get_all(source_lang=source_lang, target_lang=target_lang)
        flags: list[TermFlag] = []

        for entry in entries:
            if entry.source_term not in source_text:
                continue  # term not present in this chunk, skip

            if entry.target_term.lower() in draft_text.lower():
                continue  # correct — approved term used

            # violation: approved term missing from draft
            found = self._find_nearby(draft_text, entry.source_term)
            snippet = self._extract_snippet(source_text, entry.source_term)

            flags.append(TermFlag(
                source_term=entry.source_term,
                expected=entry.target_term,
                found=found,
                context_snippet=snippet,
                suggestion=f'Replace with approved term: "{entry.target_term}"',
            ))

        return flags

    def _find_nearby(self, text: str, source_term: str) -> Optional[str]:
        """
        Heuristic: check if the source term itself leaked into the draft
        (untranslated) or find nothing.
        """
        if source_term in text:
            return source_term  # term was left untranslated
        return None

    def _extract_snippet(self, text: str, term: str, window: int = 40) -> str:
        idx = text.find(term)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(term) + window)
        return f"...{text[start:end]}..."

    def format_report(self, flags: list[TermFlag]) -> str:
        if not flags:
            return "✓ No terminology violations found."
        lines = [f"⚠ {len(flags)} terminology issue(s):"]
        for f in flags:
            lines.append(f"  • '{f.source_term}' → expected '{f.expected}'")
            if f.found:
                lines.append(f"    found: '{f.found}'")
            if f.context_snippet:
                lines.append(f"    context: {f.context_snippet}")
            lines.append(f"    → {f.suggestion}")
        return "\n".join(lines)