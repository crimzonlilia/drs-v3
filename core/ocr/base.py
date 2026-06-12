from __future__ import annotations

import base64
import os
import httpx
import json
from dataclasses import dataclass
from abc import ABC, abstractmethod
from config import cfg

@dataclass
class OCRBlock:
    text: str
    bbox: list[float]  # [x_min, y_min, width, height] normalized to 0.0 - 1.0
    confidence: float

class OCRProvider(ABC):
    @abstractmethod
    async def extract(self, image_path: str) -> list[OCRBlock]:
        """
        Extract text blocks with normalized coordinates from the image at image_path.
        """
        pass

async def extract_via_llm(image_path: str, source_lang: str) -> list[OCRBlock]:
    """
    Extract text blocks and coordinates from a manga/comic image using a multimodal LLM.
    """
    api_key = cfg.api_key
    base_url = cfg.base_url
    if not api_key:
        print("LLM OCR failed: OPENROUTER_API_KEY is not configured.")
        return []
        
    try:
        ext = os.path.splitext(image_path)[1].lower()
        if ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".webp":
            mime_type = "image/webp"
        else:
            mime_type = "image/png"
            
        with open(image_path, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")
            
        model = os.getenv("OCR_MODEL", "google/gemini-2.5-flash")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/drs-v3",
            "X-Title": "DRS v3",
        }
        
        prompt = (
            f"You are a professional manga/comic translation OCR engine. "
            f"Please transcribe all text bubbles and text blocks from the provided page image in {source_lang.upper()} language. "
            f"For each text bubble/block, estimate its normalized bounding box [x_min, y_min, width, height] relative to the overall image size (scale from 0.0 to 1.0).\n\n"
            f"Return ONLY a valid JSON array of objects, with no markdown code blocks or extra text. Example:\n"
            f"[\n  {{\"text\": \"transcribed text\", \"bbox\": [x_min, y_min, width, height]}}\n]"
        )
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_data}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2048
        }
        
        url = base_url
        if not url.endswith("/"):
            url += "/"
        url += "chat/completions"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.replace("```json", "").replace("```", "").strip()
                
                blocks_data = json.loads(content)
                blocks = []
                for item in blocks_data:
                    text = item.get("text", "").strip()
                    bbox = item.get("bbox", [])
                    if text and isinstance(bbox, list) and len(bbox) == 4:
                        blocks.append(
                            OCRBlock(
                                text=text,
                                bbox=[float(c) for c in bbox],
                                confidence=0.99
                            )
                        )
                return blocks
    except Exception as e:
        print(f"LLM OCR extraction failed: {e}")
    return []
