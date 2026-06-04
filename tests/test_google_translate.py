import asyncio
import httpx

async def google_translate(text: str, source_lang: str, target_lang: str) -> str:
    if not text.strip():
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
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

async def main():
    test_text = "こんにちは、元気ですか？"
    source = "ja"
    target = "vi"
    
    print(f"Original Text: {test_text}")
    print("Translating via Google Translate API...")
    
    result = await google_translate(test_text, source, target)
    print(f"Translated Text: {result}")
    
    # English test
    print("\nOriginal Text: Hello, how are you?")
    result_en = await google_translate("Hello, how are you?", "en", "vi")
    print(f"Translated Text (EN -> VI): {result_en}")

if __name__ == "__main__":
    asyncio.run(main())
