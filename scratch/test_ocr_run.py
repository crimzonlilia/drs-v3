import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from core.utils.r2 import read_binary
from core.ocr.manga_ocr import MangaOCRProvider

async def main():
    asset_id = 'HKkmC_ab0AA7fg8.png'
    r2_path = f"projects/demo_project/docs/doc_test_export/assets/{asset_id}"
    print(f"Downloading {r2_path}...")
    img_bytes = read_binary(r2_path)
    if not img_bytes:
        print("Failed to download image from R2.")
        return
        
    local_path = f"scratch_{asset_id}"
    with open(local_path, "wb") as f:
        f.write(img_bytes)
        
    print(f"Saved to {local_path}. Running MangaOCRProvider...")
    provider = MangaOCRProvider()
    try:
        blocks = await provider.extract(local_path)
        print("Extracted blocks count:", len(blocks))
        for i, b in enumerate(blocks):
            print(f"Block {i}: text={b.text}, bbox={b.bbox}")
    except Exception as e:
        print("Exception occurred during extraction:", e)
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

if __name__ == "__main__":
    asyncio.run(main())
