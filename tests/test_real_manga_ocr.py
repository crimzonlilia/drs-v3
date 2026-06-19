import os
import sys
import time
import asyncio
import tempfile
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.memory import ProjectMemory
from core.utils.r2 import read_binary
from core.ocr.multimodal_ocr import MultimodalOCRTranslator

async def test_real_image_translation():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    
    print("=== Test: Real Manga Image Multimodal Translation ===")
    project_id = "demo_project"
    doc_id = "doc_test_export"
    asset_id = "HK7N-hSawAAS_xY.jpg"
    
    # 1. Fetch image from R2
    r2_path = f"projects/{project_id}/docs/{doc_id}/assets/{asset_id}"
    print(f"Reading image from R2: {r2_path}...")
    image_bytes = read_binary(r2_path)
    
    if not image_bytes:
        print("Error: Could not retrieve image bytes from R2.")
        return
        
    print(f"Successfully retrieved image. Bytes size: {len(image_bytes)}")
    
    # 2. Write to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_file.write(image_bytes)
        temp_file_path = temp_file.name
        
    print(f"Saved image locally to: {temp_file_path}")
    
    # 3. Load Project Memory
    mem = ProjectMemory(project_id)
    project_memory_context = mem.build_prompt_context("ja", "vi")
    
    # 4. Run Multimodal OCR
    translator = MultimodalOCRTranslator()
    print(f"Running joint Multimodal OCR & Translation with model: {translator.model}...")
    
    start_time = time.perf_counter()
    results = await translator.extract_and_translate(
        image_path=temp_file_path,
        source_lang="ja",
        target_lang="vi",
        project_memory_context=project_memory_context
    )
    duration = time.perf_counter() - start_time
    
    print(f"\nMultimodal OCR & Translation completed in {duration:.2f} seconds.")
    print(f"Found {len(results)} translated blocks:")
    for idx, item in enumerate(results):
        print(f"\nBlock {idx + 1}:")
        print(f"  Source: {ascii(item['source_text'])}")
        print(f"  Translation: {ascii(item['target_text'])}")
        print(f"  Bounding Box: {item['bbox']}")
        
    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
        
    print("\n=== Real Image Test Completed ===")

if __name__ == "__main__":
    asyncio.run(test_real_image_translation())
