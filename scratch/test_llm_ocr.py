import asyncio
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from config import cfg
from core.utils.r2 import read_binary

async def main():
    asset_id = 'HKkmC_ab0AA7fg8.png'
    r2_path = f"projects/demo_project/docs/doc_test_export/assets/{asset_id}"
    img_bytes = read_binary(r2_path)
    if not img_bytes:
        print("Failed to download image from R2.")
        return
        
    local_path = f"scratch_{asset_id}"
    with open(local_path, "wb") as f:
        f.write(img_bytes)
        
    print("API Key configured:", bool(cfg.api_key))
    print("Base URL:", cfg.base_url)
    
    import httpx
    try:
        import base64
        with open(local_path, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")
            
        model = "google/gemini-2.5-flash"
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "HTTP-Referer": "https://github.com/drs-v3",
            "X-Title": "DRS v3",
        }
        
        prompt = (
            f"You are a professional manga/comic translation OCR engine. "
            f"Please transcribe all text bubbles and text blocks from the provided page image in ja language. "
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
                                    "url": f"data:image/png;base64,{base64_data}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1
        }
        
        url = cfg.base_url
        if not url.endswith("/"):
            url += "/"
        url += "chat/completions"
        
        print(f"Sending request to {url} using model {model}...")
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
            print("Response Status Code:", resp.status_code)
            if resp.status_code != 200:
                print("Response Body:", resp.text)
            else:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                print("Raw Content returned by LLM:")
                print(content)
    except Exception as e:
        print("Failed to run custom LLM OCR:", e)
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

if __name__ == "__main__":
    asyncio.run(main())
