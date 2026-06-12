from __future__ import annotations

import os
import httpx
import json
from PIL import Image
from config import cfg
from core.ocr.base import OCRProvider, OCRBlock, extract_via_llm

class PaddleOCRProvider(OCRProvider):
    async def extract(self, image_path: str) -> list[OCRBlock]:
        api_url = os.getenv("PADDLE_OCR_API_URL")
        mock_ocr = cfg.mock_ocr
        
        # 1. API Mode
        if api_url:
            try:
                async with httpx.AsyncClient() as client:
                    with open(image_path, "rb") as f:
                        files = {"file": f}
                        resp = await client.post(api_url, files=files, timeout=60.0)
                        if resp.status_code == 200:
                            data = resp.json()
                            blocks = []
                            for item in data:
                                blocks.append(
                                    OCRBlock(
                                        text=item["text"],
                                        bbox=item["bbox"],  # [x, y, w, h] normalized
                                        confidence=item.get("confidence", 0.95)
                                    )
                                )
                            return blocks
            except Exception as e:
                print(f"PaddleOCR API failed: {e}. Falling back to other modes...")

        # 2. Local Mode
        if not mock_ocr:
            try:
                # Lazy import to avoid importing heavy libraries
                from paddleocr import PaddleOCR
                
                # Initialize PaddleOCR with English default or config
                ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
                
                # Open image for normalization
                img = Image.open(image_path)
                width, height = img.size
                
                # Run full OCR
                # result is a list of lists containing [[polygon, [text, confidence]]]
                result = ocr.ocr(image_path, cls=True)
                
                blocks = []
                if result and result[0]:
                    for line in result[0]:
                        box = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                        text, conf = line[1]
                        
                        xs = [pt[0] for pt in box]
                        ys = [pt[1] for pt in box]
                        
                        x_min = max(0, int(min(xs)))
                        y_min = max(0, int(min(ys)))
                        x_max = min(width, int(max(xs)))
                        y_max = min(height, int(max(ys)))
                        
                        w_px = x_max - x_min
                        h_px = y_max - y_min
                        
                        if w_px <= 0 or h_px <= 0:
                            continue
                            
                        # Normalize
                        bbox = [
                            round(x_min / width, 4),
                            round(y_min / height, 4),
                            round(w_px / width, 4),
                            round(h_px / height, 4)
                        ]
                        
                        blocks.append(
                            OCRBlock(
                                text=text,
                                bbox=bbox,
                                confidence=float(conf)
                            )
                        )
                return blocks
                
            except ImportError:
                # Local packages are not installed, fallback to real LLM OCR
                return await extract_via_llm(image_path, "en")
        
        # 3. Mock Mode (Fallback)
        return [
            OCRBlock(
                text="Hello, who are you?",
                bbox=[0.100, 0.150, 0.350, 0.080],
                confidence=0.98
            ),
            OCRBlock(
                text="I am a translation assistant.",
                bbox=[0.100, 0.250, 0.500, 0.080],
                confidence=0.96
            ),
            OCRBlock(
                text="Let's translate some text.",
                bbox=[0.200, 0.400, 0.450, 0.080],
                confidence=0.97
            )
        ]
