import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.utils.r2 import read_binary
from server.utils.graphics import render_manga_text_layers
from core.utils.db import execute_query

async def test():
    project_id = "demo_project"
    doc_id = "doc_test_export"
    asset_id = "HK7N-hSawAAS_xY.jpg"
    
    log_lines = []
    try:
        r2_path = f"projects/{project_id}/docs/{doc_id}/assets/{asset_id}"
        image_bytes = read_binary(r2_path)
        if not image_bytes:
            log_lines.append(f"Asset image {asset_id} not found in R2 path: {r2_path}")
            with open("scratch/render_result.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(log_lines))
            return
            
        segments = await execute_query(
            "SELECT segment_id, source_text, target_text, bbox FROM segments WHERE project_id = ? AND doc_id = ? AND asset_id = ?",
            [project_id, doc_id, asset_id]
        )
        
        log_lines.append(f"Found {len(segments)} segments in DB.")
        for s in segments:
            log_lines.append(f"Segment: {s['segment_id']}, Source: {s['source_text']}, Target: {s['target_text']}, BBox: {s['bbox']}")
            
        rendered_bytes = render_manga_text_layers(
            image_bytes=image_bytes,
            segments=segments,
            project_id=project_id,
            font_name="Arial",
            font_size=18
        )
        
        log_lines.append(f"Rendering succeeded! Generated {len(rendered_bytes)} bytes.")
        with open("scratch/render_result.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
            
    except Exception as e:
        import traceback
        log_lines.append(traceback.format_exc())
        with open("scratch/render_result.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

if __name__ == "__main__":
    asyncio.run(test())
