import base64
import os
import httpx
import json
from config import cfg

class MultimodalOCRTranslator:
    def __init__(self, model_name: str = None):
        self.model = model_name or os.getenv("OCR_MODEL", cfg.ocr_model)
        
    async def extract_and_translate(
        self,
        image_path: str,
        source_lang: str,
        target_lang: str,
        project_memory_context: str = ""
    ) -> list[dict]:
        """
        Send image and project memory context to multimodal LLM.
        Returns a list of dicts with keys: source_text, target_text, bbox
        """
        api_key = cfg.api_key
        base_url = cfg.base_url
        if not api_key:
            print("[MULTIMODAL OCR] Error: OPENROUTER_API_KEY is not configured.")
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
                
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/drs-v3",
                "X-Title": "DRS v3",
            }
            
            prompt = (
                f"You are a professional manga/comic translation and OCR engine.\n"
                f"Please do the following tasks on the provided image:\n"
                f"1. Transcribe all text bubbles/blocks in the source language '{source_lang}'.\n"
                f"2. Translate each text bubble/block directly into the target language '{target_lang}'. Use natural and context-appropriate translations.\n"
                f"3. Estimate the normalized bounding box [x_min, y_min, width, height] for each bubble (scale from 0.0 to 1.0 relative to overall image size).\n\n"
                f"CRITICAL GLOSSARY / STYLE CONTEXT:\n"
                f"{project_memory_context}\n\n"
                f"RULES:\n"
                f"- A single text bubble or text box must correspond to exactly ONE item. Concatenate vertical/horizontal lines in correct reading order.\n"
                f"- Strictly respect the glossary and style rules provided above. For example, if a character name matches a glossary entry, use the canonical name in the translation.\n"
                f"- Return ONLY a valid JSON array of objects, with no markdown code blocks or extra text. Example format:\n"
                f"[\n"
                f"  {{\n"
                f"    \"source_text\": \"Original text in ja\",\n"
                f"    \"target_text\": \"Translated text in vi\",\n"
                f"    \"bbox\": [x_min, y_min, width, height]\n"
                f"  }}\n"
                f"]"
            )
            
            payload = {
                "model": self.model,
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
                    results = []
                    for item in blocks_data:
                        source_text = item.get("source_text", "").strip()
                        target_text = item.get("target_text", "").strip()
                        bbox = item.get("bbox", [])
                        if source_text and target_text and isinstance(bbox, list) and len(bbox) == 4:
                            results.append({
                                "source_text": source_text,
                                "target_text": target_text,
                                "bbox": [float(c) for c in bbox]
                            })
                    print(f"[MULTIMODAL OCR] Successfully parsed {len(results)} text blocks with translations.")
                    return results
                else:
                    print(f"[MULTIMODAL OCR] Error response: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[MULTIMODAL OCR] Joint OCR and Translation failed: {e}")
        return []
