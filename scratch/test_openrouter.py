import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    print(f"API Key present: {bool(api_key)}")
    if api_key:
        print(f"API Key prefix: {api_key[:10]}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/drs-v3",
        "X-Title": "DRS v3 Test",
    }
    payload = {
        "model": "qwen/qwen3.5-flash-02-23",
        "messages": [{"role": "user", "content": "say hi"}],
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("Sending request to OpenRouter...")
            resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=10.0)
            print(f"Status code: {resp.status_code}")
            print(f"Response: {resp.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
