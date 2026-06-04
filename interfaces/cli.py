"""
DRS v3 CLI — run the localization pipeline from the terminal.

Commands:
    run       — translate a source file through the full pipeline
    memory    — inspect / manage project memory
    promote   — promote pending corrections to approved memory
    project   — init a new project

Usage examples:
    python -m interfaces.cli run --project one-piece-vi --chapter ch001 --source input.md
    python -m interfaces.cli memory --project one-piece-vi --show glossary
    python -m interfaces.cli promote --project one-piece-vi
"""

from __future__ import annotations

import asyncio
import sys
import textwrap
import uuid
from pathlib import Path

import click

from core.memory import ProjectMemory, GlossaryEntry, Entity, StyleRule, Correction, CorrectionType
from core.workflow import Pipeline, ApprovalSession


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _print_box(title: str, content: str) -> None:
    width = 60
    print(f"\n{'─'*width}")
    print(f"  {title}")
    print(f"{'─'*width}")
    print(content)
    print(f"{'─'*width}\n")


async def _cli_review_callback(session: ApprovalSession):
    """
    Interactive human review in the terminal.
    Loops until approved or rejected, allowing editing and feedback extraction.
    """
    current_text = session.draft
    corrections = []

    while True:
        _print_box(
            f"Draft ready for review -- {session.chapter_or_doc}",
            current_text
        )

        if session.review_note:
            click.echo(f"Reviewer note: {session.review_note}\n")

        if corrections:
            click.echo("Logged corrections in this session:")
            for c in corrections:
                click.echo(f"  - [{c.correction_type}] Source: '{c.source_term}' | Draft: '{c.original_text}' -> Corrected: '{c.corrected_text}'")
            click.echo()

        user_input = click.prompt(
            "Action (Press Enter to approve, type 'edit' to modify, type 'reject' to reject, or type feedback directly)",
            default="approve",
        )

        clean_input = user_input.strip().lower()

        if clean_input == "reject":
            click.echo("Draft rejected.")
            return "", []

        elif clean_input in ("approve", ""):
            click.echo("Approved.")
            return current_text, corrections

        elif clean_input == "edit":
            click.echo("Enter your edited version (end with a line containing only '###'):")
            lines = []
            while True:
                line = input()
                if line.strip() == "###":
                    break
                lines.append(line)
            current_text = "\n".join(lines)

        else:
            feedback_text = user_input
            click.echo("Analyzing feedback with AI...")
            from core.agents.feedback_extractor import FeedbackExtractor
            extractor = FeedbackExtractor(ProjectMemory(session.project_id))
            try:
                extracted = await extractor.extract(
                    source_text=session.source_text,
                    draft_text=session.draft,
                    final_text=current_text,
                    feedback_text=feedback_text,
                )
                await extractor.close()
                if extracted:
                    click.echo(f"AI extracted {len(extracted)} correction(s):")
                    for item in extracted:
                        click.echo(f"  [{item.correction_type}] Source: '{item.source_term}' | Draft: '{item.original_text}' -> Corrected: '{item.corrected_text}'")
                        if item.note:
                            click.echo(f"    Note: {item.note}")
                        
                        # Avoid duplicates in the session's corrections list
                        corrections = [c for c in corrections if not (
                            (c.source_term and item.source_term and c.source_term == item.source_term) or
                            (not c.source_term and not item.source_term and c.original_text == item.original_text)
                        )]

                        corrections.append(Correction(
                            correction_id=str(uuid.uuid4())[:8],
                            project_id=session.project_id,
                            chapter_or_doc=session.chapter_or_doc,
                            source_lang=session.source_lang if hasattr(session, "source_lang") else "ja",
                            target_lang=session.target_lang if hasattr(session, "target_lang") else "vi",
                            correction_type=CorrectionType(item.correction_type),
                            source_term=item.source_term,
                            original_text=item.original_text,
                            corrected_text=item.corrected_text,
                            note=item.note,
                        ))
                else:
                    click.echo("No systematic corrections extracted.")
            except Exception as e:
                click.echo(f"Error extracting feedback: {e}")


# ------------------------------------------------------------------ #
# CLI groups                                                           #
# ------------------------------------------------------------------ #

@click.group()
def cli():
    """DRS v3 — localization workspace with persistent memory."""
    pass


# ------------------------------------------------------------------ #
# run                                                                  #
# ------------------------------------------------------------------ #

@cli.command()
@click.option("--project", "-p", required=True, help="Project ID (e.g. one-piece-vi)")
@click.option("--chapter", "-c", required=True, help="Chapter/doc ID (e.g. ch001)")
@click.option("--source", "-s", required=True, type=click.Path(exists=True), help="Source text file")
@click.option("--source-lang", default="ja", show_default=True)
@click.option("--target-lang", default="vi", show_default=True)
@click.option("--content-type", default="manga", show_default=True,
              type=click.Choice(["manga", "fanfic", "novel", "general"]))
@click.option("--output-dir", default="projects", show_default=True)
def run(project, chapter, source, source_lang, target_lang, content_type, output_dir):
    """Run the full pipeline on a source file."""
    source_text = Path(source).read_text(encoding="utf-8")
    memory = ProjectMemory(project)

    async def _run():
        async with Pipeline(memory, source_lang, target_lang, content_type) as pipeline:
            await pipeline.run(
                source_text=source_text,
                chapter_or_doc=chapter,
                review_callback=_cli_review_callback,
                save_output=True,
                output_dir=output_dir,
            )

    asyncio.run(_run())


# ------------------------------------------------------------------ #
# memory                                                               #
# ------------------------------------------------------------------ #

@cli.command()
@click.option("--project", "-p", required=True)
@click.option("--show", type=click.Choice(["glossary", "entities", "style", "corrections", "all"]),
              default="all")
@click.option("--source-lang", default=None)
@click.option("--target-lang", default=None)
def memory(project, show, source_lang, target_lang):
    """Inspect project memory."""
    mem = ProjectMemory(project)

    if show in ("glossary", "all"):
        entries = mem.glossary.get_all(source_lang=source_lang, target_lang=target_lang)
        _print_box(f"Glossary ({len(entries)} entries)", 
                   "\n".join(f"  {e.source_term} → {e.target_term}  [{e.source_lang}→{e.target_lang}]"
                             for e in entries) or "  (empty)")

    if show in ("entities", "all"):
        entities = mem.entities.get_all(source_lang=source_lang, target_lang=target_lang)
        _print_box(f"Entities ({len(entities)} entries)",
                   "\n".join(f"  [{e.entity_type}] {e.source_name} → {e.canonical_name}"
                             + (f"  | {e.pronouns}" if e.pronouns else "")
                             for e in entities) or "  (empty)")

    if show in ("style", "all"):
        ctx = mem.style.as_prompt_context()
        _print_box("Style Profile", ctx or "  (empty)")

    if show in ("corrections", "all"):
        stats = mem.corrections.summary()
        _print_box("Corrections",
                   f"  total: {stats['total']}  pending: {stats['pending']}  "
                   f"promoted: {stats['promoted']}  repeated patterns: {stats['repeated_patterns']}")


# ------------------------------------------------------------------ #
# promote                                                              #
# ------------------------------------------------------------------ #

@cli.command()
@click.option("--project", "-p", required=True)
def promote(project):
    """Review pending corrections and promote to approved memory."""
    from core.workflow import ApprovalGate

    mem = ProjectMemory(project)
    gate = ApprovalGate(mem)
    pending = gate.get_pending_promotions()

    if not pending:
        click.echo("No pending corrections to promote.")
        return

    total = sum(len(v) for v in pending.values())
    click.echo(f"\n{total} pending correction(s):\n")

    for ctype, corrections in pending.items():
        click.echo(f"[{ctype}]")
        for c in corrections:
            click.echo(f"  ID: {c.correction_id}")
            if c.source_term:
                click.echo(f"  Source: '{c.source_term}' | Draft: '{c.original_text}' -> Corrected: '{c.corrected_text}'")
            else:
                click.echo(f"  Draft: '{c.original_text}' -> Corrected: '{c.corrected_text}'")
            if c.note:
                click.echo(f"  note: {c.note}")

            action = click.prompt(
                "  Promote to",
                type=click.Choice(["glossary", "entity", "style", "skip", "dismiss"]),
                default="skip",
            )

            if action == "dismiss":
                mem.corrections.dismiss(c.correction_id)
                click.echo("  dismissed.")

            elif action == "glossary":
                source_lang = click.prompt("  source_lang", default="ja")
                target_lang = click.prompt("  target_lang", default="vi")
                note = click.prompt("  context_note (optional)", default="")
                
                # Check if we have source_term, otherwise prompt
                source_term = c.source_term
                if not source_term:
                    source_term = click.prompt("  source_term (original language word)", default="")
                if not source_term:
                    source_term = c.original_text # final fallback
                    
                gate.promote_correction_to_glossary(
                    c.correction_id,
                    source_term=source_term,
                    target_term=c.corrected_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    context_note=note,
                )
                click.echo("  promoted to glossary")

            elif action == "entity":
                entity_id = click.prompt("  entity_id (slug)")
                canonical = click.prompt("  canonical_name")
                etype = click.prompt("  entity_type", default="character")
                source_lang = click.prompt("  source_lang", default="ja")
                target_lang = click.prompt("  target_lang", default="vi")
                pronouns = click.prompt("  pronouns (optional)", default="")
                
                # Check if we have source_term, otherwise prompt
                source_name = c.source_term
                if not source_name:
                    source_name = click.prompt("  source_name (original language name)", default="")
                if not source_name:
                    source_name = c.original_text # final fallback
                    
                gate.promote_correction_to_entity(
                    c.correction_id,
                    Entity(
                        entity_id=entity_id,
                        canonical_name=canonical,
                        source_name=source_name,
                        entity_type=etype,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        pronouns=pronouns,
                    ),
                )
                click.echo("  promoted to entity registry")

            elif action == "style":
                if not mem.style.profile:
                    click.echo("  No style profile initialized for this project. Skipping.")
                    continue
                rule_id = click.prompt("  rule_id (slug)")
                category = click.prompt("  category", default="other")
                description = click.prompt("  description")
                gate.promote_correction_to_style(
                    c.correction_id,
                    StyleRule(
                        rule_id=rule_id,
                        category=category,
                        description=description,
                        example_before=c.original_text,
                        example_after=c.corrected_text,
                    ),
                )
                click.echo("  promoted to style profile")

            else:
                click.echo("  skipped.")

        click.echo()


# ------------------------------------------------------------------ #
# project init                                                         #
# ------------------------------------------------------------------ #

@cli.command("project")
@click.option("--id", "project_id", required=True, help="Project ID slug (e.g. one-piece-vi)")
@click.option("--source-lang", required=True)
@click.option("--target-lang", required=True)
@click.option("--content-type", default="manga",
              type=click.Choice(["manga", "fanfic", "novel", "general"]))
@click.option("--tone-note", default="", help="Top-level tone note for style profile")
def project_init(project_id, source_lang, target_lang, content_type, tone_note):
    """Initialize a new project with empty memory stores."""
    # Create the project directory FIRST so ProjectMemory knows to use it for self-contained memory
    project_dir = Path("projects") / project_id / "chapters"
    project_dir.mkdir(parents=True, exist_ok=True)

    mem = ProjectMemory(project_id)
    mem.style.init_profile(
        source_lang=source_lang,
        target_lang=target_lang,
        content_type=content_type,
        tone_note=tone_note,
    )

    config_path = Path("projects") / project_id / "project.yaml"
    import yaml
    config_path.write_text(yaml.dump({
        "project_id": project_id,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "content_type": content_type,
        "tone_note": tone_note,
    }, allow_unicode=True), encoding="utf-8")

    click.echo(f"✓ Project '{project_id}' initialized.")
    click.echo(f"  Memory store : memory_store/{{glossaries,styles,entities,corrections}}/{project_id}.yaml")
    click.echo(f"  Project dir  : projects/{project_id}/")
    click.echo(f"\nNext: python -m interfaces.cli run -p {project_id} -c ch001 -s your_source.md")


if __name__ == "__main__":
    cli()
