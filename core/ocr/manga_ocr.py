from __future__ import annotations

import os
import httpx
import json
from PIL import Image
from core.ocr.base import OCRProvider, OCRBlock

class MangaOCRProvider(OCRProvider):
    async def extract(self, image_path: str) -> list[OCRBlock]:
        api_url = os.getenv("MANGA_OCR_API_URL")
        mock_ocr = os.getenv("MOCK_OCR", "false").lower() == "true"
        
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
                print(f"MangaOCR API failed: {e}. Falling back to other modes...")

        # 2. Local Mode
        if not mock_ocr:
            try:
                # Lazy import to avoid importing heavy libraries unless running locally
                from paddleocr import PaddleOCR
                from manga_ocr import MangaOcr
                
                # Initialize engines (uses cpu by default or gpu if available)
                # det=True, rec=False means detection-only for PaddleOCR
                det_model = PaddleOCR(use_angle_cls=True, lang="japan", rec=False, show_log=False)
                mocr = MangaOcr()
                
                # Open image to get size for normalization
                img = Image.open(image_path)
                width, height = img.size
                
                # Run detection
                # PaddleOCR expects a path or numpy array
                det_result = det_model.ocr(image_path, rec=False)
                
                blocks = []
                if det_result and det_result[0]:
                    for idx, box in enumerate(det_result[0]):
                        # box is a list of 4 points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
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
                            
                        # Crop bubble/line
                        crop_img = img.crop((x_min, y_min, x_max, y_max))
                        
                        # Transcribe text
                        text = mocr(crop_img)
                        
                        # Normalize coordinates
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
                                confidence=0.98  # MangaOCR does not expose confidence natively
                            )
                        )
                return blocks
                
            except ImportError:
                # Local packages are not installed, fallback to Mock or error
                if not api_url and os.getenv("MOCK_OCR") is None:
                    # If user did not configure MOCK_OCR explicitly, warn them
                    print("Warning: paddleocr or manga_ocr not installed. Falling back to Mock OCR.")
        
        # 3. Mock Mode (Fallback)
        # Mock Japanese Manga bubbles
        return [
            OCRBlock(
                text="お前は誰だ？",
                bbox=[0.550, 0.200, 0.120, 0.180],
                confidence=0.99
            ),
            OCRBlock(
                text="私は先輩の後輩です。",
                bbox=[0.250, 0.450, 0.150, 0.250],
                confidence=0.97
            ),
            OCRBlock(
                text="そんなことがあるか！",
                bbox=[0.750, 0.650, 0.100, 0.200],
                confidence=0.95
            )
        ]
