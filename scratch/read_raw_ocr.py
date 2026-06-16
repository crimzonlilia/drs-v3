import asyncio
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from core.utils.r2 import read_text

def main():
    r2_key = "projects/demo_project/docs/doc_test_export/extracted/HKkmC_ab0AA7fg8.png.json"
    print(f"Reading R2 file: {r2_key}")
    content = read_text(r2_key)
    if not content:
        print("No content found or file does not exist in R2.")
        return
        
    try:
        data = json.loads(content)
        print("Provider:", data.get("provider"))
        print("Generated At:", data.get("generated_at"))
        print("Blocks count:", len(data.get("blocks", [])))
        for i, b in enumerate(data.get("blocks", [])):
            print(f"Block {i}: {b}")
    except Exception as e:
        print("Failed to parse JSON:", e)
        print("Raw content:")
        print(content)

if __name__ == "__main__":
    main()
