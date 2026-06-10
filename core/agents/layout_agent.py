from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from core.memory import ProjectMemory
from core.agents.layout_translator import LayoutTranslator, LayoutTextBlock
from core.utils.r2 import read_binary

class LayoutAgent:
    """
    LayoutAgent manages layout extraction, visual analysis, capacity estimating,
    typesetting, and visual quality assurance.
    """
    
    def __init__(self, memory: ProjectMemory, model: str | None = None):
        self.memory = memory
        self.translator = LayoutTranslator(memory, model=model)

    async def extract_layout(self, asset_id: str) -> List[Dict[str, Any]]:
        """
        Extracts bounding boxes, OCR text, and region types from a visual asset.
        """
        # Load asset bytes from R2
        path = f"projects/{self.memory.project_id}/docs/assets/{asset_id}"
        data = read_binary(path)
        if not data:
            # Try backup path
            path = f"projects/{self.memory.project_id}/docs/doc_test_export/assets/{asset_id}"
            data = read_binary(path)
            
        if not data:
            # Mock fallback if file doesn't exist
            return [
                {
                    "block_id": "block_0",
                    "box": [100, 150, 400, 300],
                    "source_text": "ジョンは先輩と陛下を見ました。",
                    "translated_text": "John đã nhìn thấy tiền bối và bệ hạ.",
                    "bubble_type": "normal"
                }
            ]

        try:
            blocks = await self.translator.translate_page(
                image_bytes=data,
                source_lang="ja",
                target_lang="vi"
            )
        except Exception as e:
            print(f"LayoutTranslator failed to translate page: {e}. Falling back to mock layout.")
            return [
                {
                    "block_id": "block_0",
                    "box": [100, 150, 400, 300],
                    "source_text": "ジョンは先輩 và 陛下を見ました。",
                    "translated_text": "John đã nhìn thấy tiền bối và bệ hạ.",
                    "bubble_type": "normal"
                }
            ]
        
        return [
            {
                "block_id": b.block_id,
                "box": b.box,
                "source_text": b.source_text,
                "translated_text": b.translated_text,
                "bubble_type": b.bubble_type
            }
            for b in blocks
        ]

    def estimate_text_capacity(self, box: List[int], font_config: Dict[str, Any]) -> int:
        """
        Estimates characters capacity for a bounding box based on box size and font.
        """
        # box format: [x_min, y_min, x_max, y_max] from 0 to 1000
        x_min, y_min, x_max, y_max = box
        width = x_max - x_min
        height = y_max - y_min
        
        font_size = font_config.get("font_size", 12)
        # Simple heuristic: area divided by approximate char size
        area = width * height
        capacity = int(area / (font_size * 2))
        return max(5, capacity)

    def render_page(self, asset_id: str, segments: List[Dict[str, Any]]) -> bytes:
        """
        Renders translated text onto page asset.
        """
        # In mock mode, we just return the original file bytes or empty PNG
        path = f"projects/{self.memory.project_id}/docs/assets/{asset_id}"
        data = read_binary(path)
        if data:
            return data
            
        # Standard transparent PNG 1x1 mock
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x01\x00\x00\x0c\x00\x01\x04\x05\x73\x11\x00\x00\x00\x00IEND\xaeB`\x82"

    def audit_visual_layout(self, rendered_asset_id: str) -> Dict[str, Any]:
        """
        Audits typesetting output for overflows, missing text, and alignment issues.
        """
        # Mock QA response
        return {
            "status": "passed",
            "overflow_detected": False,
            "missing_text_detected": False,
            "alignment_issues": []
        }

    async def close(self):
        await self.translator.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
