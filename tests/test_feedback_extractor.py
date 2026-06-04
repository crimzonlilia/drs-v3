import asyncio
from core.memory import ProjectMemory
from core.agents.feedback_extractor import FeedbackExtractor


async def main():
    mem = ProjectMemory("demo_test")
    extractor = FeedbackExtractor(mem)

    source_text = "こんにちは先輩。ルフィは本当に優しい。"
    draft_text = "Xin chào tiền bối. Lupin thực sự rất tử tế."
    final_text = "Xin chào senpai. Luffy thực sự rất tử tế."
    feedback_text = "Sửa tiền bối thành senpai, Lupin thành Luffy nha."

    print("Running FeedbackExtractor test...")
    print(f"Source: {source_text}")
    print(f"Draft: {draft_text}")
    print(f"Final: {final_text}")
    print(f"Feedback: {feedback_text}")
    print("---------------------------------")

    corrections = await extractor.extract(
        source_text=source_text,
        draft_text=draft_text,
        final_text=final_text,
        feedback_text=feedback_text,
    )

    print(f"Extracted {len(corrections)} correction(s):")
    for c in corrections:
        print(f"- Type: {c.correction_type}")
        print(f"  Source term: '{c.source_term}'")
        print(f"  Original (draft): '{c.original_text}'")
        print(f"  Corrected: '{c.corrected_text}'")
        print(f"  Note: {c.note}")

    await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())
