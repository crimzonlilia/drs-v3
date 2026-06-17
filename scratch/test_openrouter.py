import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.memory import ProjectMemory
from core.agents.candidate_generator import CandidateGenerator

async def test():
    try:
        mem = ProjectMemory("demo_project")
        gen = CandidateGenerator(mem)
        res = await gen.generate(
            source_text="ちなみに本物と同じモーションで代わりに攻撃する",
            source_lang="ja",
            target_lang="vi",
            content_type="comic"
        )
        
        output = []
        output.append(f"Model: {gen.model}")
        output.append(f"Draft: {res.draft}")
        if res.raw_response:
            output.append(f"Raw Response: {res.raw_response}")
            
        with open("scratch/openrouter_result.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
            
    except Exception as e:
        import traceback
        with open("scratch/openrouter_result.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test())
