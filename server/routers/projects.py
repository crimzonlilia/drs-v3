"""
Project management router.
"""

import re
import html
from pathlib import Path
from typing import List
import yaml
from fastapi import APIRouter, HTTPException, Depends, Response

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


@router.get("/{project_id}/chapters", response_model=List[str])
async def list_project_chapters(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    List all chapters/documents inside a project.
    """
    chapters_dir = Path("projects") / project_id / "chapters"
    if not chapters_dir.exists():
        return []
    chapters = []
    for d in chapters_dir.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            chapters.append(d.name)
    return sorted(chapters)


@router.get("/{project_id}/chapters/{chapter_id}")
async def get_chapter_content(project_id: str, chapter_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get the content of a specific chapter.
    """
    chapter_dir = Path("projects") / project_id / "chapters" / chapter_id
    if not chapter_dir.exists():
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    draft_path = chapter_dir / "draft.md"
    approved_path = chapter_dir / "approved.md"
    
    draft_content = draft_path.read_text(encoding="utf-8") if draft_path.exists() else ""
    approved_content = approved_path.read_text(encoding="utf-8") if approved_path.exists() else ""
    
    return {
        "project_id": project_id,
        "chapter_id": chapter_id,
        "draft": draft_content,
        "approved": approved_content
    }


def convert_html_to_markdown(html_str: str) -> str:
    if not html_str:
        return ""
    md = html_str
    # Replace <br> and <div> with newlines
    md = re.sub(r'<br\s*/?>', '\n', md, flags=re.IGNORECASE)
    md = re.sub(r'<div>', '\n', md, flags=re.IGNORECASE)
    md = re.sub(r'</div>', '', md, flags=re.IGNORECASE)
    
    # Bold
    md = re.sub(r'<(?:b|strong)>(.*?)</(?:b|strong)>', r'**\1**', md, flags=re.IGNORECASE)
    # Italic
    md = re.sub(r'<(?:i|em)>(.*?)</(?:i|em)>', r'*\1*', md, flags=re.IGNORECASE)
    # Strikethrough
    md = re.sub(r'<(?:strike|s)>(.*?)</(?:strike|s)>', r'~~\1~~', md, flags=re.IGNORECASE)
    # Links
    md = re.sub(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', md, flags=re.IGNORECASE)
    # Images
    md = re.sub(r'<img\s+(?:[^>]*?\s+)?src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>', r'![\2](\1)', md, flags=re.IGNORECASE)
    md = re.sub(r'<img\s+(?:[^>]*?\s+)?src="([^"]*)"[^>]*>', r'![](\1)', md, flags=re.IGNORECASE)
    # Blockquotes
    md = re.sub(r'<blockquote>(.*?)</blockquote>', r'\n> \1\n', md, flags=re.IGNORECASE)
    # Align center
    md = re.sub(r'<div\s+align="center">(.*?)</div>', r'<div align="center">\1</div>', md, flags=re.IGNORECASE)
    # Inline code
    md = re.sub(r'<code>(.*?)</code>', r'`\1`', md, flags=re.IGNORECASE)
    # Remove remaining HTML tags (except <u>)
    md = re.sub(r'<(?!\/?u\b)[^>]*>', '', md)
    
    # Decode HTML entities
    md = html.unescape(md)
    return md


@router.post("/{project_id}/chapters/{chapter_id}")
async def save_chapter_content(project_id: str, chapter_id: str, payload: dict, current_user: dict = Depends(get_current_user)):
    """
    Save or update the draft/approved contents of a specific chapter.
    """
    chapter_dir = Path("projects") / project_id / "chapters" / chapter_id
    chapter_dir.mkdir(parents=True, exist_ok=True)
    
    if "draft" in payload:
        draft_content = payload["draft"]
        if "<" in draft_content and ">" in draft_content:
            draft_content = convert_html_to_markdown(draft_content)
        (chapter_dir / "draft.md").write_text(draft_content, encoding="utf-8")
    if "approved" in payload:
        approved_content = payload["approved"]
        if "<" in approved_content and ">" in approved_content:
            approved_content = convert_html_to_markdown(approved_content)
        (chapter_dir / "approved.md").write_text(approved_content, encoding="utf-8")
        
    return {"status": "success", "message": "Chapter saved successfully"}


@router.get("/{project_id}/chapters/{chapter_id}/export")
async def export_chapter_content(project_id: str, chapter_id: str, current_user: dict = Depends(get_current_user)):
    """
    Export the chapter content as a clean Markdown download.
    """
    chapter_dir = Path("projects") / project_id / "chapters" / chapter_id
    draft_path = chapter_dir / "draft.md"
    approved_path = chapter_dir / "approved.md"
    
    content = ""
    if approved_path.exists():
        content = approved_path.read_text(encoding="utf-8")
    elif draft_path.exists():
        content = draft_path.read_text(encoding="utf-8")
    else:
        raise HTTPException(status_code=404, detail="Chapter content not found")
        
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={chapter_id}.md"}
    )
