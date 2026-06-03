"""
core/checks — rule-based consistency checks for DRS v3.

Runs before human review. Catches violations that don't need LLM judgment.
LLM-level review lives in core/agents/reviewer.py.

Usage:
    from core.checks import CheckSuite
    from core.memory import ProjectMemory

    mem = ProjectMemory("one-piece-vi")
    suite = CheckSuite(mem)
    report = suite.run(source_text, draft_text, source_lang="ja", target_lang="vi", content_type="manga")
    print(report.summary())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from core.memory import ProjectMemory
from .terminology import TerminologyChecker, TermFlag
from .entity import EntityChecker, EntityFlag
from .style import StyleChecker, StyleFlag


@dataclass
class CheckReport:
    term_flags: list[TermFlag] = field(default_factory=list)
    entity_flags: list[EntityFlag] = field(default_factory=list)
    style_flags: list[StyleFlag] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.term_flags or self.entity_flags or self.style_flags)

    @property
    def needs_llm_review(self) -> bool:
        return any(f.requires_llm_review for f in self.style_flags)

    def summary(self) -> str:
        lines = []
        total = len(self.term_flags) + len(self.entity_flags) + len(self.style_flags)
        if not total:
            return "✓ All checks passed."
        lines.append(f"{'='*50}")
        lines.append(f"Check Report — {total} issue(s) found")
        lines.append(f"{'='*50}")
        if self.term_flags:
            lines.append(f"\n[Terminology] {len(self.term_flags)} issue(s)")
            for f in self.term_flags:
                lines.append(f"  • {f.source_term} → expected '{f.expected}'")
                lines.append(f"    → {f.suggestion}")
        if self.entity_flags:
            lines.append(f"\n[Entities] {len(self.entity_flags)} issue(s)")
            for f in self.entity_flags:
                lines.append(f"  • [{f.violation_type}] {f.source_name}: {f.detail}")
                lines.append(f"    → {f.suggestion}")
        if self.style_flags:
            rule_only = [f for f in self.style_flags if not f.requires_llm_review]
            llm_needed = [f for f in self.style_flags if f.requires_llm_review]
            if rule_only:
                lines.append(f"\n[Style] {len(rule_only)} rule violation(s)")
                for f in rule_only:
                    lines.append(f"  • [{f.category}] {f.violation_detail}")
                    lines.append(f"    → {f.suggestion}")
            if llm_needed:
                lines.append(f"\n[Style — LLM Review needed] {len(llm_needed)} item(s)")
                for f in llm_needed:
                    lines.append(f"  [Bot] [{f.category}] {f.description}")
        return "\n".join(lines)


class CheckSuite:
    """Run all three checkers in one call."""

    def __init__(self, memory: ProjectMemory):
        self.term_checker = TerminologyChecker(memory.glossary)
        self.entity_checker = EntityChecker(memory.entities)
        self.style_checker = StyleChecker(memory.style)

    def run(
        self,
        source_text: str,
        draft_text: str,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
    ) -> CheckReport:
        return CheckReport(
            term_flags=self.term_checker.check(source_text, draft_text, source_lang, target_lang),
            entity_flags=self.entity_checker.check(source_text, draft_text, source_lang, target_lang),
            style_flags=self.style_checker.check(draft_text, content_type, source_lang),
        )


__all__ = [
    "CheckSuite", "CheckReport",
    "TerminologyChecker", "TermFlag",
    "EntityChecker", "EntityFlag",
    "StyleChecker", "StyleFlag",
]