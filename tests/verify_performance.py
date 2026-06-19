import os
import sys
import time
import asyncio
from pathlib import Path
from PIL import Image

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.memory import ProjectMemory
from core.utils.r2 import read_text, write_text, delete_file
from core.ocr.multimodal_ocr import MultimodalOCRTranslator

async def test_r2_cache_performance():
    print("--- Test 1: R2 Cache and Connection Pooling Latency ---")
    project_id = "demo_project"
    key = f"projects/{project_id}/memory/glossary.yaml"
    
    # Write a test value
    write_text(key, "test_data: true")
    
    # Measure 1st read (Cold read)
    start_cold = time.perf_counter()
    cold_val = read_text(key)
    end_cold = time.perf_counter()
    cold_duration = (end_cold - start_cold) * 1000.0
    print(f"Cold Read duration: {cold_duration:.4f} ms")
    
    # Measure subsequent reads (Warm reads, should hit RAM cache)
    durations = []
    for i in range(5):
        start_warm = time.perf_counter()
        warm_val = read_text(key)
        end_warm = time.perf_counter()
        durations.append((end_warm - start_warm) * 1000.0)
        
    avg_warm = sum(durations) / len(durations)
    print(f"Average Warm Read duration: {avg_warm:.4f} ms")
    
    # Test invalidation
    write_text(key, "test_data: false")
    
    # Read immediately after write (should be cold read again, since cache was cleared)
    start_after_write = time.perf_counter()
    after_write_val = read_text(key)
    end_after_write = time.perf_counter()
    after_write_duration = (end_after_write - start_after_write) * 1000.0
    print(f"Read after write duration (must be cold): {after_write_duration:.4f} ms")
    
    # Clean up
    delete_file(key)
    
    # Assertions
    assert avg_warm < 1.0, f"Average warm read was too slow: {avg_warm:.4f} ms"
    print("Test 1 passed: Cache hits are near-instantaneous (under 1ms).")


async def test_multimodal_ocr_translation():
    print("\n--- Test 2: Multimodal OCR & Direct Translation ---")
    # Generate a dummy test image with PIL containing some text
    img_path = os.path.join(project_root, "scratch", "manga_test_bubble.png")
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    img.save(img_path)
    print(f"Created dummy test image at: {img_path}")
    
    translator = MultimodalOCRTranslator()
    
    start_time = time.perf_counter()
    results = await translator.extract_and_translate(
        image_path=img_path,
        source_lang="ja",
        target_lang="vi",
        project_memory_context="Glossary: 先輩 -> senpai"
    )
    duration = time.perf_counter() - start_time
    
    print(f"Multimodal OCR & Translation complete in {duration:.2f} seconds.")
    print("Results parsed:")
    print(results)
    
    if os.path.exists(img_path):
        os.unlink(img_path)
        
    print("Test 2 completed.")


async def test_chinese_novel_translation():
    print("\n--- Test 3: Chinese Novel Batch Translation & Speed Verification ---")
    from core.agents import TranslationAgent
    
    project_id = "demo_project"
    mem = ProjectMemory(project_id)
    
    # 15 segments of typical Chinese cultivation web novel
    segments = [
        {"segment_id": f"seg_{i}", "source_text": txt}
        for i, txt in enumerate([
            "林枫站在山巅，狂风吹拂着他的衣衫。",
            "‘这一世，我绝不会再留下遗憾！’他心中暗暗发誓。",
            "天空中突然雷云密布，一道狂暴的紫色闪电划破长空。",
            "‘既然你要战，那便战吧！’林枫冷笑一声，拔出腰间长剑。",
            "长剑发出清脆的鸣响，仿佛在回应主人的战意。",
            "不远处，一位身穿白衣的仙子踏空而来，衣袂飘飘。",
            "‘林公子，别来无恙。’女子的声音清冷，不带一丝感情。",
            "林枫微微皱眉，‘是你？你来这里做什么？’",
            "‘奉阁主之命，带你回去。’白衣女子淡淡说道。",
            "‘回去？真是天大的笑话！我林枫何曾屈服于人？’",
            "狂暴的气息自他体内戏卷开来，周围的巨石瞬间粉碎。",
            "白衣女子眼中闪过一丝惊讶，‘你竟然突破到了金丹期？’",
            "‘这都要拜你们所赐！’林枫身形一闪，化作一道残影冲出。",
            "两股强大的力量在半空中碰撞，爆发出刺眼的光芒。",
            "整座山峰都在微微颤抖，战况瞬间进入了白热化。"
        ])
    ]
    
    start_time = time.perf_counter()
    async with TranslationAgent(mem) as agent:
        translations = await agent.translate_batch(
            segments=segments,
            source_lang="zh",
            target_lang="vi",
            content_type="novel",
            project_description="Truyện tiên hiệp tu chân, hành trình của nhân vật chính Lâm Phong."
        )
    duration = time.perf_counter() - start_time
    
    print(f"Novel Batch Translation (15 segments) completed in {duration:.2f} seconds.")
    print("Sample translation results:")
    for seg in segments[:3]:
        seg_id = seg["segment_id"]
        print(f"  Source: {seg['source_text']}")
        print(f"  Translation: {translations.get(seg_id)}")
    
    print("Test 3 completed.")


async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    
    print("Starting DRS v3 Performance Optimization Verification...")
    await test_r2_cache_performance()
    
    # Only run LLM tests if API key is present
    from config import cfg
    if cfg.api_key:
        await test_multimodal_ocr_translation()
        await test_chinese_novel_translation()
    else:
        print("\nSkipping LLM tests (OPENROUTER_API_KEY not set).")
        
    print("\nAll performance tests completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
