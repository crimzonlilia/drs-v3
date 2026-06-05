"""
Memory Management and Wiki Seeding router.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from core.memory import ProjectMemory, GlossaryEntry, Entity, StyleRule
from core.agents import FandomResearcher
from server.schemas import SeedRequest, GlossaryAddInput, EntityAddInput, StyleRuleAddInput
from server.auth import get_current_user

router = APIRouter(prefix="/api/memory", tags=["Memory"])


@router.get("/{project_id}")
async def get_project_memory(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    Fetch all glossary entries, entities, and style guidelines for a project.
    """
    mem = ProjectMemory(project_id)
    
    glossary = [
        {
            "source_term": e.source_term,
            "target_term": e.target_term,
            "source_lang": e.source_lang,
            "target_lang": e.target_lang,
            "context_note": e.context_note
        }
        for e in mem.glossary.get_all()
    ]
    
    entities = [
        {
            "entity_id": e.entity_id,
            "canonical_name": e.canonical_name,
            "source_name": e.source_name,
            "entity_type": e.entity_type,
            "pronouns": e.pronouns,
            "notes": e.notes
        }
        for e in mem.entities.get_all()
    ]
    
    style_rules = [
        {
            "rule_id": r.rule_id,
            "category": r.category,
            "description": r.description,
            "example_before": r.example_before,
            "example_after": r.example_after
        }
        for r in (mem.style.profile.rules if mem.style.profile else [])
    ]

    corrections = [
        {
            "correction_id": c.correction_id,
            "correction_type": c.correction_type.value if hasattr(c.correction_type, "value") else str(c.correction_type),
            "original_text": c.original_text,
            "corrected_text": c.corrected_text,
            "source_term": c.source_term,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "logged_at": c.logged_at,
            "note": c.note
        }
        for c in mem.corrections._corrections
    ]
    
    return {
        "glossary": glossary,
        "entities": entities,
        "style_rules": style_rules,
        "corrections": corrections
    }


@router.post("/{project_id}/seed")
async def seed_memory(project_id: str, data: SeedRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Run Wikipedia FandomResearcher to proactively gather context and seed project memory.
    """
    mem = ProjectMemory(project_id)
    
    async def run_seeding():
        researcher = FandomResearcher(mem)
        try:
            await researcher.seed_project_memory(
                topic=data.topic,
                source_lang=data.source_lang,
                target_lang=data.target_lang
            )
        finally:
            await researcher.close()

    # Runs in the background to prevent blocking
    background_tasks.add_task(run_seeding)
    
    return {
        "status": "pending",
        "message": f"Background research task started for topic '{data.topic}'"
    }


@router.post("/{project_id}/glossary")
async def add_glossary_term(project_id: str, data: GlossaryAddInput, current_user: dict = Depends(get_current_user)):
    """
    Explicitly add a term to the glossary.
    """
    mem = ProjectMemory(project_id)
    entry = GlossaryEntry(
        source_term=data.source_term,
        target_term=data.target_term,
        source_lang=data.source_lang,
        target_lang=data.target_lang,
        content_type="general",
        context_note=data.context_note or ""
    )
    try:
        mem.glossary.add_entry(entry)
        return {"status": "success", "message": "Glossary term added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save glossary term: {e}")


@router.delete("/{project_id}/glossary/{source_lang}/{target_lang}/{source_term}")
async def delete_glossary_term(project_id: str, source_lang: str, target_lang: str, source_term: str, current_user: dict = Depends(get_current_user)):
    """
    Delete a term from the glossary.
    """
    mem = ProjectMemory(project_id)
    try:
        removed = mem.glossary.remove_entry(source_term, source_lang, target_lang)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete glossary term: {e}")
    if not removed:
        raise HTTPException(status_code=404, detail="Glossary term not found")
    return {"status": "success", "message": "Glossary term deleted successfully"}


@router.post("/{project_id}/entities")
async def add_entity_item(project_id: str, data: EntityAddInput, current_user: dict = Depends(get_current_user)):
    """
    Add or update an entity in project memory.
    """
    mem = ProjectMemory(project_id)
    entity = Entity(
        entity_id=data.entity_id,
        canonical_name=data.canonical_name,
        source_name=data.source_name,
        entity_type=data.entity_type,
        source_lang=data.source_lang,
        target_lang=data.target_lang,
        pronouns=data.pronouns or "",
        notes=data.notes or ""
    )
    try:
        mem.entities.add_entity(entity)
        return {"status": "success", "message": "Entity saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save entity: {e}")


@router.delete("/{project_id}/entities/{entity_id}")
async def delete_entity_item(project_id: str, entity_id: str, current_user: dict = Depends(get_current_user)):
    """
    Delete an entity from project memory.
    """
    mem = ProjectMemory(project_id)
    try:
        removed = mem.entities.remove_entity(entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete entity: {e}")
    if not removed:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"status": "success", "message": "Entity deleted successfully"}


@router.post("/{project_id}/style-rules")
async def add_style_rule_item(project_id: str, data: StyleRuleAddInput, current_user: dict = Depends(get_current_user)):
    """
    Add or update a style rule in project memory.
    """
    mem = ProjectMemory(project_id)
    rule = StyleRule(
        rule_id=data.rule_id,
        category=data.category,
        description=data.description,
        example_before=data.example_before or "",
        example_after=data.example_after or "",
        source_lang=data.source_lang or "",
        target_lang=data.target_lang or ""
    )
    try:
        mem.style.add_rule(rule)
        return {"status": "success", "message": "Style rule saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save style rule: {e}")


@router.delete("/{project_id}/style-rules/{rule_id}")
async def delete_style_rule_item(project_id: str, rule_id: str, current_user: dict = Depends(get_current_user)):
    """
    Delete a style rule from project memory.
    """
    mem = ProjectMemory(project_id)
    try:
        removed = mem.style.remove_rule(rule_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete style rule: {e}")
    if not removed:
        raise HTTPException(status_code=404, detail="Style rule not found")
    return {"status": "success", "message": "Style rule deleted successfully"}


@router.delete("/{project_id}/corrections/{correction_id}")
async def delete_correction_item(project_id: str, correction_id: str, current_user: dict = Depends(get_current_user)):
    """
    Dismiss (delete) a correction log entry.
    """
    mem = ProjectMemory(project_id)
    try:
        removed = mem.corrections.dismiss(correction_id)
        if removed:
            return {"status": "success", "message": "Correction dismissed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Correction not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dismiss correction: {e}")


@router.post("/{project_id}/corrections/{correction_id}/promote")
async def promote_correction_item(project_id: str, correction_id: str, target_type: str, current_user: dict = Depends(get_current_user)):
    """
    Promote a correction entry into approved glossary memory.
    """
    mem = ProjectMemory(project_id)

    correction = next((c for c in mem.corrections._corrections if c.correction_id == correction_id), None)
    if not correction:
        raise HTTPException(status_code=404, detail="Correction not found")

    if target_type != "glossary":
        raise HTTPException(status_code=400, detail="Only promotion to 'glossary' is currently supported")

    try:
        entry = GlossaryEntry(
            source_term=correction.source_term or correction.original_text,
            target_term=correction.corrected_text,
            source_lang=correction.source_lang,
            target_lang=correction.target_lang,
            content_type="general",
            context_note=f"Promoted from correction log: {correction.note}"
        )
        mem.glossary.add_entry(entry)
        mem.corrections.promote(correction_id, "glossary")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to promote correction: {e}")

    return {"status": "success", "message": "Correction promoted to Glossary successfully"}
