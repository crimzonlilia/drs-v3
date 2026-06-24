"""
LayoutTranslator Agent — detects, OCRs, and translates text directly from document and screenshot images.

Uses a multimodal model (like Gemini 1.5 Flash) on OpenRouter to detect text panels/boxes,
OCR the source text, translate to target language, and return coordinates for rendering.
"""

from __future__ import annotations

import base64
import httpx
import json
import re
from typing import Optional
from dataclasses import dataclass
from config import cfg
from core.memory import ProjectMemory

async def google_translate(text: str, source_lang: str, target_lang: str) -> str:
    if not text.strip():
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        sl = "auto" if source_lang in ("multi", "auto") else source_lang
        tl = "vi" if target_lang in ("multi", "auto") else target_lang
        params = {
            "client": "gtx",
            "sl": sl,
            "tl": tl,
            "dt": "t",
            "q": text
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                translated = "".join([part[0] for part in data[0] if part[0]])
                return translated.strip()
    except Exception as e:
        print(f"Google translate failed: {e}")
    return text

@dataclass
class LayoutTextBlock:
    block_id: str
    box: list[int]  # [x_min, y_min, x_max, y_max] normalized to 0-1000
    source_text: str
    translated_text: str
    bubble_type: str = "normal"  # "normal" | "thought" | "scream" | "narration"

class LayoutTranslator:
    """
    Agent responsible for processing screenshot layout, slides, and visual document panel images.
    """
    def __init__(self, memory: ProjectMemory, model: str | None = None):
        self.memory = memory
        # We use a vision-capable model. Default to cfg.ocr_model
        self.model = model or cfg.ocr_model
        base_url = cfg.base_url
        if not base_url.endswith("/"):
            base_url += "/"
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "HTTP-Referer": "https://github.com/drs-v3",
                "X-Title": "DRS v3",
            },
            timeout=120.0,
        )

    async def translate_page(
        self,
        image_bytes: bytes,
        source_lang: str = "ja",
        target_lang: str = "vi",
        mime_type: str = "image/png",
    ) -> list[LayoutTextBlock]:
        """
        Perform fast layout/OCR via vision model, translate instantly via Google Translate,
        and then batch polish using the LLM with Project memory/glossary.
        """
        # Encode image to base64
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{base64_image}"

        # Resolve language names
        lang_names = {
            "vi": "Vietnamese",
            "en": "English",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
        }
        src_name = lang_names.get(source_lang.lower(), source_lang)
        tgt_name = lang_names.get(target_lang.lower(), target_lang)

        # 1. OCR & Layout analysis via Multimodal Vision LLM
        system_prompt = f"""You are an expert document layout and OCR assistant.
You will receive an image of a document or layout page.
Your task is to detect all text panels, text boxes, or region blocks in the page.
For each text block, you must return:
1. The bounding box coordinates as normalized integers from 0 to 1000:
   - x_min, y_min, x_max, y_max (where 0,0 is top-left, and 1000,1000 is bottom-right).
2. The original {src_name} text inside the block (perform clean OCR).
3. The block type classified as:
   - "normal" for standard document/dialog text.
   - "thought" for inner notes or background text.
   - "scream" for bold, highlighted, or callout text.
   - "narration" for narrative boxes, headers, footers, or panels.

Respond ONLY with a JSON list of objects matching this schema:
[
  {{
    "box": [x_min, y_min, x_max, y_max],
    "source_text": "text in {src_name}",
    "bubble_type": "normal"
  }}
]
Do not include any markdown wrappers (like ```json), explanations, or notes.
"""

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        }
                    ]
                }
            ]
        }

        response = await self._client.post("chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        
        # Clean response
        content_clean = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content_clean = re.sub(r"\s*```$", "", content_clean)
        
        blocks_raw = []
        try:
            blocks_raw = json.loads(content_clean.strip())
        except Exception as e:
            match = re.search(r"\[\s*\{.*\}\s*\]", content_clean, re.DOTALL)
            if match:
                try:
                    blocks_raw = json.loads(match.group(0))
                except Exception:
                    pass
            if not blocks_raw:
                raise RuntimeError(f"Could not parse vision model response: {e}")

        # 2. Call Google Translate for fast raw translation
        blocks = []
        for i, b in enumerate(blocks_raw):
            src_text = b.get("source_text", b.get("japanese_text", ""))
            bubble_type = b.get("bubble_type", "normal")
            
            raw_translation = await google_translate(src_text, source_lang, target_lang)
            
            blocks.append(
                LayoutTextBlock(
                    block_id=f"block_{i}",
                    box=b["box"],
                    source_text=src_text,
                    translated_text=raw_translation,
                    bubble_type=bubble_type
                )
            )

        if not blocks:
            return []

        # 3. Call CandidateGenerator to refine/polish the raw translations in batch using the memory/glossary context
        from core.agents.candidate_generator import CandidateGenerator
        try:
            async with CandidateGenerator(self.memory, model=self.model) as generator:
                ref_map = await generator.refine_translations(
                    blocks=blocks,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                for b in blocks:
                    if b.block_id in ref_map:
                        b.translated_text = ref_map[b.block_id]
        except Exception as e:
            print(f"Failed to refine translations via CandidateGenerator: {e}. Keeping Google Translate defaults.")



        return blocks

    async def evaluate_rendered_page(
        self,
        original_image_bytes: bytes,
        rendered_image_bytes: bytes,
        blocks: list[LayoutTextBlock],
        source_lang: str = "ja",
        target_lang: str = "vi",
        mime_type: str = "image/png"
    ) -> str:
        """
        Multimodal QA check: compares original and rendered images to evaluate typesetting
        and text overflow issues.
        """
        orig_base64 = base64.b64encode(original_image_bytes).decode("utf-8")
        rend_base64 = base64.b64encode(rendered_image_bytes).decode("utf-8")
        
        orig_url = f"data:{mime_type};base64,{orig_base64}"
        rend_url = f"data:{mime_type};base64,{rend_base64}"
        
        # Resolve language names
        lang_names = {
            "vi": "Vietnamese",
            "en": "English",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
        }
        src_name = lang_names.get(source_lang.lower(), source_lang)
        tgt_name = lang_names.get(target_lang.lower(), target_lang)
 
        prompt = f"""You are an expert layout and document QA reviewer.
You are given two versions of a document page:
1. The original raw page (in {src_name}).
2. The translated, typeset page (in {tgt_name}).

Please evaluate the typesetting and layout of the translated page:
1. Are the translated texts properly centered and sized within their layout blocks?
2. Are there any text overflows (text drawing outside the blocks or clipping boundaries)?
3. Does the tone of the fonts feel appropriate?
4. Are there any blocks left untranslated?

Provide a concise, bulleted review report in {tgt_name}. Highlight any specific blocks (e.g. Block 1, Block 2) that require correction. If everything is perfect, simply say a short confirmation message in {tgt_name} indicating all text blocks are perfectly aligned and formatted.
"""
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": orig_url}
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": rend_url}
                        }
                    ]
                }
            ]
        }

        response = await self._client.post("chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
