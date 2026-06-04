"""
Context Researcher Agent — automatically seeds project memory with glossary terms,
entities, and style guidelines for any fandom, historical figure, or document topic (e.g., FGO, Richard I)
using Wikipedia Search and LLM knowledge.
"""

from __future__ import annotations

import json
import httpx
import re
from config import cfg
from core.memory import ProjectMemory, GlossaryEntry, Entity, StyleRule

async def search_wikipedia(query: str) -> str:
    """
    Search Wikipedia for the given query and return a summary of the top result.
    """
    if not query.strip():
        return ""
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(search_url, params=search_params, timeout=10.0)
            if resp.status_code == 200:
                search_data = resp.json()
                search_results = search_data.get("query", {}).get("search", [])
                if search_results:
                    # Get the top page title
                    title = search_results[0]["title"]
                    # Fetch summary extract
                    content_params = {
                        "action": "query",
                        "prop": "extracts",
                        "exintro": 1,
                        "explaintext": 1,
                        "titles": title,
                        "format": "json",
                        "utf8": 1
                    }
                    content_resp = await client.get(search_url, params=content_params, timeout=10.0)
                    if content_resp.status_code == 200:
                        content_data = content_resp.json()
                        pages = content_data.get("query", {}).get("pages", {})
                        for page_id, page_data in pages.items():
                            return page_data.get("extract", "")
    except Exception as e:
        print(f"Wikipedia search failed for '{query}': {e}")
    return ""

class FandomResearcher:
    def __init__(self, memory: ProjectMemory, model: str | None = None):
        self.memory = memory
        self.model = model or cfg.generator_model
        self._client = httpx.AsyncClient(
            base_url=cfg.base_url,
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "HTTP-Referer": "https://github.com/drs-v3",
                "X-Title": "DRS v3",
            },
            timeout=60.0,
        )

    async def seed_project_memory(self, topic_name: str, source_lang: str, target_lang: str) -> dict:
        """
        Generate glossary, entity profiles, and style rules for any topic and save to memory.
        """
        lang_names = {
            "vi": "Vietnamese",
            "en": "English",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
        }
        src_name = lang_names.get(source_lang.lower(), source_lang)
        tgt_name = lang_names.get(target_lang.lower(), target_lang)

        # Step 1: Perform Wikipedia Search to fetch real-world context
        wiki_context = await search_wikipedia(topic_name)

        prompt = f"""You are an expert translation director and research librarian.
The user is starting a translation project on the topic/subject: "{topic_name}" from {src_name} ({source_lang}) to {tgt_name} ({target_lang}).

Here is the background information retrieved from Wikipedia for this topic:
---
{wiki_context or "(No direct wiki page found, rely on your internal knowledge)"}
---

Generate a high-quality "translation seed profile" for this topic.
This profile must contain:
1. Glossary: 5-10 core terms or vocabulary specific to this topic/fandom and their canonical translations into {tgt_name}.
2. Entities: 5-8 major entities (characters, historical figures, organizations, places) with their source names, canonical translated names, and appropriate description/pronoun guidelines for {tgt_name}.
3. Style Rules: 3-5 guidelines for translation tone, register, and formatting conventions appropriate for this topic.

Respond ONLY with a JSON object of this exact schema (no markdown formatting, no explanations, no notes):
{{
  "glossary": [
    {{
      "source_term": "source term",
      "target_term": "canonical translation",
      "context_note": "explanation or usage context"
    }}
  ],
  "entities": [
    {{
      "entity_id": "unique_slug",
      "source_name": "source language name",
      "canonical_name": "translated name",
      "entity_type": "character | historical_figure | location | organization",
      "notes": "pronouns, title, relationship details"
    }}
  ],
  "style_rules": [
    {{
      "category": "tone | format | terminology",
      "description": "guideline details",
      "example_before": "incorrect or literal translation example",
      "example_after": "correct or preferred translation example"
    }}
  ]
}}
"""

        payload = {
            "model": self.model,
            "max_tokens": 3000,
            "temperature": 0.3,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        
        # Clean response
        content_clean = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content_clean = re.sub(r"\s*```$", "", content_clean)

        try:
            profile = json.loads(content_clean.strip())
        except Exception as e:
            match = re.search(r"\{.*\}", content_clean, re.DOTALL)
            if match:
                try:
                    profile = json.loads(match.group(0))
                except Exception:
                    raise RuntimeError(f"Failed to parse LLM response as JSON: {e}")
            else:
                raise RuntimeError(f"Failed to parse LLM response as JSON: {e}")

        # Seed Glossary
        glossary_count = 0
        for entry in profile.get("glossary", []):
            if "source_term" in entry and "target_term" in entry:
                self.memory.glossary.add_entry(GlossaryEntry(
                    source_term=entry["source_term"],
                    target_term=entry["target_term"],
                    source_lang=source_lang,
                    target_lang=target_lang,
                    content_type="general",
                    context_note=entry.get("context_note", "")
                ))
                glossary_count += 1

        # Seed Entities
        entities_count = 0
        for ent in profile.get("entities", []):
            if "entity_id" in ent and "canonical_name" in ent:
                self.memory.entities.add_entity(Entity(
                    entity_id=ent["entity_id"],
                    canonical_name=ent["canonical_name"],
                    source_name=ent.get("source_name", ent["canonical_name"]),
                    entity_type=ent.get("entity_type", "character"),
                    source_lang=source_lang,
                    target_lang=target_lang,
                    pronouns=ent.get("notes", ""),
                    notes=ent.get("notes", "")
                ))
                entities_count += 1

        # Seed Style Rules
        style_count = 0
        for rule in profile.get("style_rules", []):
            if "description" in rule:
                # Generate a slug rule_id
                rule_id = f"seed_rule_{style_count}"
                self.memory.style.add_rule(StyleRule(
                    rule_id=rule_id,
                    category=rule.get("category", "tone"),
                    description=rule["description"],
                    example_before=rule.get("example_before", ""),
                    example_after=rule.get("example_after", "")
                ))
                style_count += 1

        return {
            "glossary_count": glossary_count,
            "entities_count": entities_count,
            "style_count": style_count
        }

    async def enrich_context_from_text(self, text: str, source_lang: str, target_lang: str) -> None:
        """
        Scan text for new proper nouns/entities and research them on Wikipedia in the background.
        """
        if not text.strip():
            return
        existing_names = [e.source_name.lower() for e in self.memory.entities.get_all()] + \
                         [e.source_term.lower() for e in self.memory.glossary.get_all()]
        
        prompt = f"""Identify up to 3 key proper nouns, character names, or specialized terms in this text that are important for translation context.
Do NOT include these existing terms: {existing_names}

Text:
{text[:2000]}

Respond ONLY with a JSON list of strings, for example: ["Saladin", "Philip II"]
If no new terms are found, respond with [].
"""
        try:
            payload = {
                "model": self.model,
                "max_tokens": 200,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }
            response = await self._client.post("/chat/completions", json=payload)
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                content_clean = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
                content_clean = re.sub(r"\s*```$", "", content_clean)
                new_terms = json.loads(content_clean)
                
                # Search and seed each new term in the background
                for term in new_terms:
                    # Avoid duplicate background tasks for same term
                    if term.lower() not in existing_names:
                        print(f"[Background Research] Seeding context for '{term}'...")
                        await self.seed_project_memory(term, source_lang, target_lang)
        except Exception as e:
            print(f"Background context enrichment failed: {e}")

    async def close(self):
        await self._client.aclose()
