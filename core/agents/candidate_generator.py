"""
Candidate Generator — call OpenRouter to produce a translation/localization draft.

Injects approved memory (glossary, style, entities) into the system prompt
so the model has full context before generating.
"""

import re
import json
import httpx
from dataclasses import dataclass
from config import cfg
from core.memory import ProjectMemory

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

@dataclass
class GenerationResult:
    draft: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: dict | None = None


from core.utils.prompt_loader import load_prompt_template

DEFAULT_SYSTEM_TEMPLATE = """\
You are a professional localization editor.
Your job is to produce a high-quality, natural-sounding translation draft.
Use the raw translation draft as a starting point, but refine it to ensure it sounds like a professional human translation.

Rules:
- Follow the glossary, style guide, and entity list exactly.
- Do NOT invent terms or names not in the approved lists.
- Preserve tone and register as specified.
- Output ONLY the translated text. No explanations, no notes.

Source language: {source_lang}
Target language: {target_lang}
Content type: {content_type}

Project Context:
{project_context}

{memory_context}
"""

DEFAULT_USER_TEMPLATE = """\
Translate the following:

Source Text:
{source_text}

Raw Translation Draft:
{raw_translation}
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
        base_url = cfg.base_url
        if not base_url.endswith("/"):
            base_url += "/"
        self._client = httpx.AsyncClient(
            base_url=base_url,
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
        temperature: float | None = None,
        project_description: str = "",
    ) -> GenerationResult:
        # Step 1: Fetch instant raw translation from Google Translate
        raw_translation = await google_translate(source_text, source_lang, target_lang)

        # Step 2: Build LLM refinement prompt
        memory_context = self.memory.build_prompt_context(source_lang, target_lang)

        system_tmpl = load_prompt_template("candidate_generator_system", content_type, DEFAULT_SYSTEM_TEMPLATE)
        user_tmpl = load_prompt_template("candidate_generator_user", content_type, DEFAULT_USER_TEMPLATE)

        system_prompt = system_tmpl.format(
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
            project_context=project_description or "(No specific project context)",
            memory_context=memory_context or "(No approved memory yet for this project)",
        )

        user_prompt = user_tmpl.format(
            source_text=source_text,
            raw_translation=raw_translation
        )

        payload = {
            "model": self.model,
            "max_tokens": cfg.gen_max_tokens,
            "temperature": temperature if temperature is not None else cfg.gen_temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = await self._client.post("chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            draft = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
        except Exception as e:
            print(f"OpenRouter API call failed in CandidateGenerator: {e}")
            draft = raw_translation
            usage = {"prompt_tokens": 0, "completion_tokens": 0}
            data = {"choices": [{"message": {"content": draft}}]}



        return GenerationResult(
            draft=draft,
            model=self.model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            raw_response=data,
        )

    async def revise(
        self,
        source_text: str,
        previous_draft: str,
        feedback: str,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
        session_corrections: list[dict] | None = None,
    ) -> GenerationResult:
        memory_context = self.memory.build_prompt_context(source_lang, target_lang)
        if session_corrections:
            session_lines = []
            for c in session_corrections:
                src = c.get("source_term") or c.get("original_text")
                tgt = c.get("corrected_text")
                note = c.get("note")
                note_str = f" ({note})" if note else ""
                if src and tgt:
                    session_lines.append(f"  {src} → {tgt}{note_str}")
            if session_lines:
                session_block = "[Session Corrections (Unsaved)]\n" + "\n".join(session_lines)
                memory_context = (memory_context + "\n\n" + session_block).strip()

        system_tmpl = load_prompt_template("candidate_generator_system", content_type, DEFAULT_SYSTEM_TEMPLATE)
        system_prompt = system_tmpl.format(
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
            memory_context=memory_context or "(No approved memory yet for this project)",
        )

        user_prompt = f"""\
Translate/revise the following text, addressing the review feedback below.

Source Text:
{source_text}

Previous Draft:
{previous_draft}

Feedback/Issues to Correct:
{feedback}

Output ONLY the revised translation. No explanations, no notes.
"""

        payload = {
            "model": self.model,
            "max_tokens": cfg.gen_max_tokens,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        response = await self._client.post("chat/completions", json=payload)
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

    async def refine_translations(
        self,
        blocks: list,
        source_lang: str,
        target_lang: str
    ) -> dict[str, str]:
        """
        Batch refine and polish translation candidates using glossary and memory rules.
        """
        # Resolve target language name
        lang_names = {
            "vi": "Vietnamese",
            "en": "English",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
        }
        tgt_name = lang_names.get(target_lang.lower(), target_lang)

        memory_context = self.memory.build_prompt_context(source_lang, target_lang)

        refine_prompt = f"""You are an expert translation editor.
Your task is to refine and polish the raw translations of text blocks.
Ensure the final translations flow naturally, respect character personalities, and match the style/glossary rules of the project.

Project Memory & Glossary Rules:
{memory_context or "(No approved memory yet)"}

Here are the text blocks to refine:
{json.dumps([{"block_id": b.block_id, "source_text": b.source_text, "raw_translation": b.translated_text, "bubble_type": b.bubble_type} for b in blocks], ensure_ascii=False, indent=2)}

Respond ONLY with a JSON list of objects matching this schema:
[
  {{
    "block_id": "block_id",
    "refined_translation": "polished translation in {tgt_name}"
  }}
]
Do not include any explanations, notes, or markdown wrappers.
"""
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "temperature": 0.2,
            "messages": [
                {"role": "user", "content": refine_prompt}
            ]
        }

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            content_clean = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
            content_clean = re.sub(r"\s*```$", "", content_clean)
            
            ref_list = json.loads(content_clean)
            return {item["block_id"]: item["refined_translation"] for item in ref_list if "block_id" in item and "refined_translation" in item}
        except Exception as e:
            print(f"Batch refinement in CandidateGenerator failed: {e}")
            return {}

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()