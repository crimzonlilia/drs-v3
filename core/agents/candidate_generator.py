"""
Candidate Generator — call OpenRouter to produce a translation/localization draft.

Injects approved memory (glossary, style, entities) into the system prompt
so the model has full context before generating.
"""

from __future__ import annotations

import httpx
from dataclasses import dataclass
from config import cfg
from core.memory import ProjectMemory


@dataclass
class GenerationResult:
    draft: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: dict | None = None


SYSTEM_TEMPLATE = """\
You are a professional localization editor.
Your job is to produce a high-quality, natural-sounding translation draft.

Rules:
- Follow the glossary, style guide, and entity list exactly.
- Do NOT invent terms or names not in the approved lists.
- Preserve tone and register as specified.
- Output ONLY the translated text. No explanations, no notes.

Source language: {source_lang}
Target language: {target_lang}
Content type: {content_type}

{memory_context}
"""

USER_TEMPLATE = """\
Translate the following:

{source_text}
"""


class CandidateGenerator:
    """
    Generate a translation candidate using OpenRouter.

    Usage:
        mem = ProjectMemory("one-piece-vi")
        gen = CandidateGenerator(mem)
        result = await gen.generate(source_text, "ja", "vi", "manga")
    """

    def __init__(self, memory: ProjectMemory, model: str | None = None):
        self.memory = memory
        self.model = model or cfg.generator_model
        self._client = httpx.AsyncClient(
            base_url=cfg.base_url,
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "HTTP-Referer": "https://github.com/drs-v3",  # OpenRouter best practice
                "X-Title": "DRS v3",
            },
            timeout=60.0,
        )

    async def generate(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
    ) -> GenerationResult:
        memory_context = self.memory.build_prompt_context(source_lang, target_lang)

        system_prompt = SYSTEM_TEMPLATE.format(
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
            memory_context=memory_context or "(No approved memory yet for this project)",
        )

        user_prompt = USER_TEMPLATE.format(source_text=source_text)

        payload = {
            "model": self.model,
            "max_tokens": cfg.gen_max_tokens,
            "temperature": cfg.gen_temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        draft = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})

        return GenerationResult(
            draft=draft,
            model=self.model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            raw_response=data,
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()