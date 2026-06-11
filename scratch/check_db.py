import asyncio
from core.utils.db import execute_query

async def main():
    rows = await execute_query("SELECT * FROM segments")
    print(f"Total segments: {len(rows)}")
    for r in rows:
        print(f"Project: {r['project_id']}, Doc: {r['doc_id']}, Seg: {r['segment_id']}, Source: {r['source_text']}, Target: {r['target_text']}")

if __name__ == "__main__":
    asyncio.run(main())
