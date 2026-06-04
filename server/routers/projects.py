"""
Project management router.
"""

from pathlib import Path
from typing import List
import yaml
from fastapi import APIRouter, HTTPException, Depends

from core.memory import ProjectMemory
from server.schemas import ProjectCreate, ProjectInfo
from server.auth import get_current_user

router = APIRouter(prefix="/api/projects", tags=["Project"])


@router.post("", response_model=ProjectInfo)
async def create_project(data: ProjectCreate, current_user: dict = Depends(get_current_user)):
    """
    Initialize a new project, creating the directory structure and style profile.
    """
    project_id = data.project_id.strip()
    if not project_id:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    # Create the project directory first so ProjectMemory uses it
    project_dir = Path("projects") / project_id / "chapters"
    project_dir.mkdir(parents=True, exist_ok=True)

    try:
        mem = ProjectMemory(project_id)
        mem.style.init_profile(
            source_lang=data.source_lang,
            target_lang=data.target_lang,
            content_type=data.content_type,
            tone_note=data.tone_note,
        )

        # Save metadata
        config_path = Path("projects") / project_id / "project.yaml"
        config_data = {
            "project_id": project_id,
            "source_lang": data.source_lang,
            "target_lang": data.target_lang,
            "content_type": data.content_type,
            "tone_note": data.tone_note,
        }
        config_path.write_text(yaml.dump(config_data, allow_unicode=True), encoding="utf-8")

        return ProjectInfo(**config_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {e}")


@router.get("", response_model=List[str])
async def list_projects(current_user: dict = Depends(get_current_user)):
    """
    List all projects in the workspace.
    """
    projects_dir = Path("projects")
    projects = []
    if projects_dir.exists():
        for d in projects_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                projects.append(d.name)
    return sorted(projects)


@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get config metadata for a specific project.
    """
    config_path = Path("projects") / project_id / "project.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        return ProjectInfo(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading project config: {e}")
