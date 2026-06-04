"""
Memory Management and Wiki Seeding router.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from core.memory import ProjectMemory
from core.agents import FandomResearcher
from server.schemas import SeedRequest
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
    
    return {
        "glossary": glossary,
        "entities": entities,
        "style_rules": style_rules
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
