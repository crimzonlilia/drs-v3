import asyncio

from core.memory import (
    ProjectMemory,
    GlossaryEntry,
)
from core.checks import CheckSuite
from core.agents import Reviewer


async def main():
    mem = ProjectMemory("demo")

    # approved glossary
    mem.glossary.add_entry(
        GlossaryEntry(
            source_term="先輩",
            target_term="senpai",
            source_lang="ja",
            target_lang="vi",
            content_type="manga",
        )
    )

    source = "こんにちは先輩"
    bad_draft = "Xin chào tiền bối"

    suite = CheckSuite(mem)
    report = suite.run(
        source_text=source,
        draft_text=bad_draft,
        source_lang="ja",
        target_lang="vi",
        content_type="manga",
    )

    print(report.summary())

    async with Reviewer(mem) as reviewer:
        result = await reviewer.review(
            source_text=source,
            draft=bad_draft,
            check_report=report,
            source_lang="ja",
            target_lang="vi",
            content_type="manga",
        )

    print("\n=== REVIEW RESULT ===")
    print(result.revised_draft)
    print(result.review_note)
    print("remaining:", result.has_remaining_issues)


asyncio.run(main())