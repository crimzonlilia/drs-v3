from core.memory import (
    ProjectMemory,
    GlossaryEntry,
    Entity,
)

mem = ProjectMemory("demo")

# glossary
mem.glossary.add_entry(
    GlossaryEntry(
        source_term="先輩",
        target_term="senpai",
        source_lang="ja",
        target_lang="vi",
        content_type="manga",
    )
)

# entity
mem.entities.add_entity(
    Entity(
        entity_id="luffy",
        canonical_name="Luffy",
        source_name="ルフィ",
        entity_type="character",
        source_lang="ja",
        target_lang="vi",
        pronouns="cậu",
    )
)

print(mem.build_prompt_context("ja", "vi"))