"""
Feedback Extractor — AI-driven analysis of unstructured human review comments.

Extracts specific, systematic corrections (glossary/entity/style) by mapping
them back to the original source text terms, the wrong AI translation, and the corrected version.
"""

from __future__ import annotations

import json
import httpx
from dataclasses import dataclass
from config import cfg
from core.memory import ProjectMemory


@dataclass
class ExtractedCorrection:
    source_term: str
    original_text: str
    corrected_text: str
    correction_type: str
    note: str = ""


SYSTEM_TEMPLATE = """You are a localization database administrator.
Your task is to analyze a translator's unstructured feedback comments, along with the draft and any edits, and extract systematic memory corrections (Glossary entries, Entities, or Style rules) to be saved into the project database.

Inputs:
- Source Text (original language): {source_text}
- AI Draft: {draft_text}
- Edited Draft (if modified): {final_text}
- Human Feedback (chat comments): {feedback_text}

Rules for Extraction:
1. Terminology: Look for specific translation corrections. Identify the source word (source_term) in the Source Text, the incorrect term/phrase in the AI Draft (original_text), and the correct term/phrase in the Edited Draft or human feedback (corrected_text).
2. Entity: Look for character names, places, pronouns, etc.
3. Style: Look for tone, register, or style rule adjustments.
4. Deep Reasoning: Analyze puns, wordplays, or double meanings mentioned in the feedback (e.g. if the user says 'cá hồi là masu đúng k, chơi chữ của master đấy chứ kp là cá hồi thật đâu nhé' -> they mean the source term '鱒' / 'masu' is a wordplay on 'master', so the intended target translation is 'master', not salmon/'masu'). Reason through this step-by-step in the 'reasoning' field before extracting the final corrected_text.
5. If no systematic corrections can be extracted from the feedback/edits, return an empty list.

For each correction, output:
- reasoning: Step-by-step chain-of-thought analysis of what the user is requesting in their feedback/edit, explaining the correct translation choice.
- source_term: The term/word in the SOURCE text (in the original language, e.g. "先輩" or "ルフィ") that corresponds to this correction.
- original_text: The incorrect term/phrase in the AI Draft (in the target language, e.g. "tiền bối" or "Lupin").
- corrected_text: The corrected term/phrase (in the target language, e.g. "senpai" or "Luffy").
- correction_type: Must be one of: "terminology", "entity", "style", "factual", or "other".
- note: A short reason for the change (e.g. "fandom honorific", "character name").

Format your output as a valid JSON object with a "corrections" key containing a list of objects:
{{
  "corrections": [
    {{
      "reasoning": "...",
      "source_term": "...",
      "original_text": "...",
      "corrected_text": "...",
      "correction_type": "...",
      "note": "..."
    }}
  ]
}}

Output ONLY valid JSON. Do not write any conversational wrapper, introductory, or concluding remarks. Do not wrap JSON in markdown block fence.
"""

USER_TEMPLATE = """Analyze the feedback and extract corrections:
Source: {source_text}
AI Draft: {draft_text}
Edited: {final_text}
Feedback: {feedback_text}
"""


class FeedbackExtractor:
    """
    Extract structured memory corrections from unstructured chat/comment feedback using OpenRouter.
    """

    def __init__(self, memory: ProjectMemory, model: str | None = None):
        self.memory = memory
        self.model = model or cfg.reviewer_model
        self._client = httpx.AsyncClient(
            base_url=cfg.base_url,
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "HTTP-Referer": "https://github.com/drs-v3",
                "X-Title": "DRS v3",
            },
            timeout=60.0,
        )

    async def extract(
        self,
        source_text: str,
        draft_text: str,
        final_text: str,
        feedback_text: str,
    ) -> list[ExtractedCorrection]:
        """
        Extract systematic corrections from user edits and chat comments.
        """
        if not feedback_text.strip() and final_text.strip() == draft_text.strip():
            return []

        system_prompt = SYSTEM_TEMPLATE.format(
            source_text=source_text,
            draft_text=draft_text,
            final_text=final_text,
            feedback_text=feedback_text,
        )

        user_prompt = USER_TEMPLATE.format(
            source_text=source_text,
            draft_text=draft_text,
            final_text=final_text,
            feedback_text=feedback_text,
        )

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        try:
            response = await self._client.post("/chat/completions", json=payload)
            # If JSON mode is not supported by the model or returns an error, fallback to normal call
            if response.status_code != 200:
                payload.pop("response_format", None)
                response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            print(f"DEBUG: raw AI response: {content}")
            return self._parse_json(content)
        except Exception as e:
            print(f"Error during extract LLM call: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Response text: {response.text}")
            return []

    def _parse_json(self, content: str) -> list[ExtractedCorrection]:
        # Handle markdown JSON fence if present
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                lines = lines[1:-1]
            content = "\n".join(lines).strip()

        try:
            parsed = json.loads(content)
            # Check if it is wrapped in an object or directly a list
            if isinstance(parsed, dict):
                # Sometimes models output {"corrections": [...]} even in JSON mode
                for k, v in parsed.items():
                    if isinstance(v, list):
                        parsed = v
                        break
            
            if not isinstance(parsed, list):
                print(f"DEBUG: parsed is not a list: {parsed}")
                return []

            results = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                results.append(
                    ExtractedCorrection(
                        source_term=item.get("source_term", ""),
                        original_text=item.get("original_text", ""),
                        corrected_text=item.get("corrected_text", ""),
                        correction_type=item.get("correction_type", "terminology"),
                        note=item.get("note", ""),
                    )
                )
            return results
        except Exception as pe:
            print(f"DEBUG: JSON parsing failed: {pe} for content: {content}")
            return []

    async def refine_tone(self, raw_tone: str) -> str:
        """
        Refine a raw, colloquial tone note into a clear, professional style instruction in Vietnamese.
        """
        if not raw_tone.strip():
            return ""
            
        system_instruction = (
            "You are a professional localization editor.\n"
            "Your task is to take a raw, colloquial tone preference or translation style request in Vietnamese (e.g. 'dịch nghiêm túc vào', 'đừng dịch thô quá') "
            "and rewrite it into a clear, professional, and well-structured directive in Vietnamese suitable for a generative AI system prompt (e.g. 'Sử dụng văn phong trang trọng, nghiêm túc. Hạn chế sử dụng từ lóng hay ngôn ngữ suồng sã.').\n"
            "Keep it concise (1-2 sentences). Do not include any chat wrapper or introductory remarks. Output ONLY the refined directive."
        )
        
        try:
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": f"Refine this tone note: {raw_tone}"}
                    ],
                    "temperature": 0.3,
                }
            )
            response.raise_for_status()
            res_json = response.json()
            refined = res_json["choices"][0]["message"]["content"].strip()
            if refined.startswith('"') and refined.endswith('"'):
                refined = refined[1:-1].strip()
            return refined
        except Exception as e:
            print(f"Error refining tone: {e}")
            return raw_tone

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
