"""
Reviewer — AI self-review pass that runs after rule-based checks.

Takes the draft + check report and asks the model to:
1. Fix any rule violations flagged by checks.
2. Evaluate soft style issues (register, tone) that need LLM judgment.
3. Produce a revised draft + short review note.

This is NOT the human approval step. It reduces noise before
the draft reaches the human reviewer.
"""

#Feedback:
#Flaw 1: Parser a bit brittle — relies on the model following the exact response format. We should add some error handling to detect if the expected sections are missing or malformed, and have a fallback mechanism (e.g. return the original draft with a note that parsing failed) to ensure that we don't lose the draft or block the workflow if the model doesn't respond as expected.


from __future__ import annotations

import httpx
from dataclasses import dataclass
from config import cfg
from core.memory import ProjectMemory
from core.checks import CheckReport


@dataclass
class ReviewResult:
    revised_draft: str
    review_note: str          # short summary of what was changed / flagged
    model: str
    has_remaining_issues: bool = False   # true if reviewer still flagged something for human
    prompt_tokens: int = 0
    completion_tokens: int = 0


from core.utils.prompt_loader import load_prompt_template

DEFAULT_SYSTEM_TEMPLATE = """\
You are a senior localization reviewer.
You will receive a translation draft and a list of issues found by automated checks.

Your tasks:
1. Fix all fixable issues listed in the check report.
2. Evaluate any soft style issues (register, tone, honorifics) that require judgment.
3. Return a revised draft and a short review note.

Follow the approved memory exactly — do not introduce new terms or names.

Source language: {source_lang}
Target language: {target_lang}
Content type: {content_type}

{memory_context}

Respond in this exact format:

REVISED_DRAFT:
<revised translation here>

REVIEW_NOTE:
<1-3 sentences summarizing what you changed or flagged for the human reviewer>

REMAINING_ISSUES:
<"none" or a brief list of issues you could not resolve and need human judgment>
"""

DEFAULT_USER_TEMPLATE = """\
ORIGINAL SOURCE:
{source_text}

CURRENT DRAFT:
{draft}

CHECK REPORT:
{check_report}
"""


class Reviewer:
    """
    AI review pass — fixes rule violations, evaluates soft style issues.

    Usage:
        mem = ProjectMemory("one-piece-vi")
        reviewer = Reviewer(mem)
        result = await reviewer.review(source, draft, check_report, "ja", "vi", "manga")
    """

    def __init__(self, memory: ProjectMemory, model: str | None = None):
        self.memory = memory
        self.model = model or cfg.reviewer_model
        self._client = httpx.AsyncClient(
            base_url=cfg.base_url,
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "HTTP-Referer": "https://github.com/drs-v3",
                "X-Title": "DRS v3",
            },
            timeout=60.0,
        )

    async def review(
        self,
        source_text: str,
        draft: str,
        check_report: CheckReport,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
    ) -> ReviewResult:


        memory_context = self.memory.build_prompt_context(source_lang, target_lang)
        system_tmpl = load_prompt_template("reviewer_system", content_type, DEFAULT_SYSTEM_TEMPLATE)
        user_tmpl = load_prompt_template("reviewer_user", content_type, DEFAULT_USER_TEMPLATE)

        system_prompt = system_tmpl.format(
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
            memory_context=memory_context or "(No approved memory yet)",
        )

        user_prompt = user_tmpl.format(
            source_text=source_text,
            draft=draft,
            check_report=check_report.summary(),
        )

        payload = {
            "model": self.model,
            "max_tokens": cfg.review_max_tokens,
            "temperature": cfg.review_temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        print("\n=== RAW MODEL OUTPUT ===")
        print(content)
        print("========================\n")
        usage = data.get("usage", {})

        revised_draft, review_note, remaining = self._parse_response(content, draft)

        return ReviewResult(
            revised_draft=revised_draft,
            review_note=review_note,
            model=self.model,
            has_remaining_issues=remaining.lower() != "none" and bool(remaining),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    def _parse_response(self, content: str, fallback_draft: str) -> tuple[str, str, str]:
        """Parse the structured response into (revised_draft, review_note, remaining_issues)."""
        sections = {"REVISED_DRAFT": "", "REVIEW_NOTE": "", "REMAINING_ISSUES": "none"}
        current = None

        for line in content.splitlines():
            stripped = line.strip()

            # inline format
            if stripped.upper().startswith("REVISED_DRAFT:"):
                current = "REVISED_DRAFT"
                value = stripped[len("REVISED_DRAFT:"):].strip()
                if value:
                    sections[current] += value + "\n"

            elif stripped.upper().startswith("REVIEW_NOTE:"):
                current = "REVIEW_NOTE"
                value = stripped[len("REVIEW_NOTE:"):].strip()
                if value:
                    sections[current] += value + "\n"

            elif stripped.upper().startswith("REMAINING_ISSUES:"):
                current = "REMAINING_ISSUES"
                value = stripped[len("REMAINING_ISSUES:"):].strip()
                if value:
                    sections[current] += value + "\n"

            # multiline continuation
            elif current:
                sections[current] += line + "\n"

        revised = sections["REVISED_DRAFT"].strip() or fallback_draft
        note = sections["REVIEW_NOTE"].strip() or "Review completed."
        remaining = sections["REMAINING_ISSUES"].strip() or "none"

        return revised, note, remaining

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()