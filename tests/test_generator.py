import asyncio
from core.memory import ProjectMemory
from core.agents import CandidateGenerator

async def main():
    mem = ProjectMemory("demo")

    async with CandidateGenerator(mem) as gen:
        result = await gen.generate(
            "こんにちは先輩",
            "ja",
            "vi",
            "manga",
        )

        print(result.draft)

asyncio.run(main())