import asyncio

from core.memory import (
    ProjectMemory,
    GlossaryEntry,
)
from core.workflow import Pipeline


async def human_review(session):
    print("\n=== HUMAN REVIEW ===")
    print(session.draft)

    # mock human review:
    # giữ nguyên để xem model sinh gì trước
    final_text = session.draft

    return final_text, []


async def main():
    print("=== TEST PIPELINE START ===")

    mem = ProjectMemory("demo")

    mem.glossary.add_entry(
    GlossaryEntry(
        source_term="先輩",
        target_term="DRS_TEST_777",
        source_lang="ja",
        target_lang="vi",
        content_type="manga",
    )
)

    print("Memory loaded.")

    async with Pipeline(
        memory=mem,
        source_lang="ja",
        target_lang="vi",
        content_type="manga",
    ) as pipeline:

        print("Pipeline ready.")

        result = await pipeline.run(
            source_text="こんにちは先輩",
            chapter_or_doc="ch001",
            review_callback=human_review,
        )

    print("\n=== PIPELINE RESULT ===")
    print(result.summary())

    try:
        print("\nDraft:", result.final_text)
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())