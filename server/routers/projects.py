"""
Project and Document management router using Cloudflare R2 and D1.
"""

import re
import html
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Response

from core.memory import ProjectMemory
from server.schemas import ProjectCreate, ProjectInfo
from server.auth import get_current_user
from core.utils.db import execute_query
from core.utils.r2 import read_text, write_text, list_files

router = APIRouter(prefix="/api/projects", tags=["Project"])


# Helper to verify project role-based access gate
async def verify_project_member(project_id: str, user_id: int, min_role: str = "viewer") -> str:
    rows = await execute_query(
        "SELECT role FROM project_members WHERE user_id = ? AND project_id = ?",
        [user_id, project_id]
    )
    if not rows:
        raise HTTPException(status_code=403, detail="Access denied: Not a member of this project")
    
    role = rows[0]["role"]
    role_hierarchy = {"viewer": 1, "editor": 2, "owner": 3}
    
    if role_hierarchy.get(role, 0) < role_hierarchy.get(min_role, 0):
        raise HTTPException(status_code=403, detail=f"Access denied: Requires at least '{min_role}' role")
    
    return role


@router.post("", response_model=ProjectInfo)
async def create_project(data: ProjectCreate, current_user: dict = Depends(get_current_user)):
    """
    Initialize a new project, setting up metadata in D1 and default configuration in R2.
    """
    project_id = data.project_id.strip()
    if not project_id:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    # Check if project already exists
    existing = await execute_query("SELECT id FROM projects WHERE id = ?", [project_id])
    if existing:
        raise HTTPException(status_code=400, detail="Project ID already exists")

    try:
        created_at = datetime.now().isoformat(timespec="seconds")
        
        # 1. Insert project into D1
        await execute_query(
            "INSERT INTO projects (id, display_name, source_lang, target_lang, content_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [project_id, data.project_id, data.source_lang, data.target_lang, data.content_type, created_at]
        )
        
        # 2. Add current user as owner in project_members D1
        await execute_query(
            "INSERT INTO project_members (user_id, project_id, role, joined_at) VALUES (?, ?, ?, ?)",
            [current_user["id"], project_id, "owner", created_at]
        )

        # 3. Save styles.yaml metadata to R2
        mem = ProjectMemory(project_id)
        mem.style.init_profile(
            source_lang=data.source_lang,
            target_lang=data.target_lang,
            content_type=data.content_type,
            tone_note=data.tone_note,
        )

        # 4. Save metadata project.yaml to R2
        config_data = {
            "project_id": project_id,
            "source_lang": data.source_lang,
            "target_lang": data.target_lang,
            "content_type": data.content_type,
            "tone_note": data.tone_note,
        }
        write_text(f"projects/{project_id}/project.yaml", yaml.dump(config_data, allow_unicode=True))

        return ProjectInfo(**config_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {e}")


@router.get("", response_model=List[str])
async def list_projects(current_user: dict = Depends(get_current_user)):
    """
    List all projects where the current user is a member.
    """
    rows = await execute_query(
        "SELECT project_id FROM project_members WHERE user_id = ?",
        [current_user["id"]]
    )
    return sorted([r["project_id"] for r in rows])


@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get config metadata for a specific project.
    """
    await verify_project_member(project_id, current_user["id"], "viewer")
    
    rows = await execute_query("SELECT * FROM projects WHERE id = ?", [project_id])
    if not rows:
        raise HTTPException(status_code=404, detail="Project not found")
        
    proj = rows[0]
    
    # Load tone note from R2 if possible
    tone_note = ""
    config_content = read_text(f"projects/{project_id}/project.yaml")
    if config_content:
        try:
            config_data = yaml.safe_load(config_content)
            tone_note = config_data.get("tone_note", "")
        except Exception:
            pass

    return ProjectInfo(
        project_id=proj["id"],
        source_lang=proj["source_lang"],
        target_lang=proj["target_lang"],
        content_type=proj["content_type"],
        tone_note=tone_note
    )


@router.get("/{project_id}/docs", response_model=List[str])
@router.get("/{project_id}/chapters", response_model=List[str])
async def list_project_docs(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    List all document IDs inside a project by listing R2 keys.
    """
    await verify_project_member(project_id, current_user["id"], "viewer")
    
    prefix = f"projects/{project_id}/docs/"
    all_files = list_files(prefix)
    
    docs = set()
    for file in all_files:
        # File key is: projects/{project_id}/docs/{doc_id}/...
        parts = file.split("/")
        if len(parts) >= 4:
            docs.add(parts[3])
            
    return sorted(list(docs))


@router.get("/{project_id}/docs/{doc_id}")
@router.get("/{project_id}/chapters/{chapter_id}")
async def get_doc_content(
    project_id: str,
    doc_id: Optional[str] = None,
    chapter_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the content of a specific document from R2 / D1.
    """
    await verify_project_member(project_id, current_user["id"], "viewer")
    
    actual_doc_id = doc_id or chapter_id
    if not actual_doc_id:
        raise HTTPException(status_code=400, detail="Missing document/chapter identifier")
        
    doc_prefix = f"projects/{project_id}/docs/{actual_doc_id}/"
    draft_content = read_text(f"{doc_prefix}draft.md") or ""
    
    # Load approved content. Try segments database first.
    rows = await execute_query(
        "SELECT target_text FROM segments WHERE project_id = ? AND doc_id = ?",
        [project_id, actual_doc_id]
    )
    
    approved_content = ""
    if rows:
        approved_content = "\n\n".join([r["target_text"] for r in rows if r["target_text"]])
        
    if not approved_content:
        # Fallback to R2 outputs
        meta_content = read_text(f"{doc_prefix}outputs/metadata.json")
        if meta_content:
            try:
                meta = json.loads(meta_content)
                v = meta.get("latest_version")
                output_content = read_text(f"{doc_prefix}outputs/translation_v{v}.json")
                if output_content:
                    out_data = json.loads(output_content)
                    approved_content = out_data.get("approved_text", "")
            except Exception:
                pass
                
    return {
        "project_id": project_id,
        "chapter_id": actual_doc_id,
        "doc_id": actual_doc_id,
        "draft": draft_content,
        "approved": approved_content
    }


def convert_html_to_markdown(html_str: str) -> str:
    if not html_str:
        return ""
    md = html_str
    md = re.sub(r'<br\s*/?>', '\n', md, flags=re.IGNORECASE)
    md = re.sub(r'<div>', '\n', md, flags=re.IGNORECASE)
    md = re.sub(r'</div>', '', md, flags=re.IGNORECASE)
    md = re.sub(r'<(?:b|strong)>(.*?)</(?:b|strong)>', r'**\1**', md, flags=re.IGNORECASE)
    md = re.sub(r'<(?:i|em)>(.*?)</(?:i|em)>', r'*\1*', md, flags=re.IGNORECASE)
    md = re.sub(r'<(?:strike|s)>(.*?)</(?:strike|s)>', r'~~\1~~', md, flags=re.IGNORECASE)
    md = re.sub(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', md, flags=re.IGNORECASE)
    md = re.sub(r'<img\s+(?:[^>]*?\s+)?src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>', r'![\2](\1)', md, flags=re.IGNORECASE)
    md = re.sub(r'<img\s+(?:[^>]*?\s+)?src="([^"]*)"[^>]*>', r'![](\1)', md, flags=re.IGNORECASE)
    md = re.sub(r'<blockquote>(.*?)</blockquote>', r'\n> \1\n', md, flags=re.IGNORECASE)
    md = re.sub(r'<div\s+align="center">(.*?)</div>', r'<div align="center">\1</div>', md, flags=re.IGNORECASE)
    md = re.sub(r'<code>(.*?)</code>', r'`\1`', md, flags=re.IGNORECASE)
    md = re.sub(r'<(?!\/?u\b)[^>]*>', '', md)
    md = html.unescape(md)
    return md


@router.post("/{project_id}/docs/{doc_id}")
@router.post("/{project_id}/chapters/{chapter_id}")
async def save_doc_content(
    project_id: str,
    doc_id: Optional[str] = None,
    chapter_id: Optional[str] = None,
    payload: dict = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Save or update draft/approved text of a document in R2.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    actual_doc_id = doc_id or chapter_id
    if not actual_doc_id:
        raise HTTPException(status_code=400, detail="Missing document/chapter identifier")
        
    doc_prefix = f"projects/{project_id}/docs/{actual_doc_id}/"
    
    if payload is None:
        payload = {}
        
    if "draft" in payload:
        draft_content = payload["draft"]
        if "<" in draft_content and ">" in draft_content:
            draft_content = convert_html_to_markdown(draft_content)
        write_text(f"{doc_prefix}draft.md", draft_content)
        
    if "approved" in payload:
        approved_content = payload["approved"]
        if "<" in approved_content and ">" in approved_content:
            approved_content = convert_html_to_markdown(approved_content)
            
        # Update R2 latest version
        meta_content = read_text(f"{doc_prefix}outputs/metadata.json")
        v_num = 1
        if meta_content:
            try:
                meta = json.loads(meta_content)
                v_num = meta.get("latest_version", 1) + 1
            except Exception:
                pass
                
        output_data = {
            "doc_id": actual_doc_id,
            "version": v_num,
            "approved_text": approved_content,
            "decided_at": datetime.now().isoformat()
        }
        write_text(f"{doc_prefix}outputs/translation_v{v_num}.json", json.dumps(output_data, ensure_ascii=False))
        
        latest_meta = {
            "latest_version": v_num,
            "approved_by": str(current_user["id"]),
            "approved_at": datetime.now().isoformat(timespec="seconds"),
            "segment_count": 1
        }
        write_text(f"{doc_prefix}outputs/metadata.json", json.dumps(latest_meta, ensure_ascii=False))
        
        # Save to D1 segments table as a single segment for simplicity
        sql = """
        INSERT OR REPLACE INTO segments 
        (project_id, doc_id, segment_id, segment_type, source_text, target_text, approved_by, approved_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await execute_query(sql, [
            project_id,
            actual_doc_id,
            "seg_001",
            "paragraph",
            approved_content, # source fallback
            approved_content,
            current_user["id"],
            latest_meta["approved_at"]
        ])
        
    return {"status": "success", "message": "Document saved successfully"}


@router.post("/{project_id}/rebuild-index")
async def rebuild_master_index(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    Rebuild the master index for all documents in a project from D1 segments table.
    """
    await verify_project_member(project_id, current_user["id"], "owner")
    
    # Load all entities and glossary terms
    mem = ProjectMemory(project_id)
    entities_list = mem.entities.get_all()
    glossary_list = mem.glossary.get_all()
    
    # Query segments
    segments = await execute_query(
        "SELECT doc_id, segment_id, source_text FROM segments WHERE project_id = ?",
        [project_id]
    )
    
    # Group by doc_id
    doc_segments: Dict[str, List[Dict[str, Any]]] = {}
    for seg in segments:
        doc_segments.setdefault(seg["doc_id"], []).append(seg)
        
    # Rebuild index for each document
    for doc_id, segs in doc_segments.items():
        entities_index = {}
        terms_index = {}
        
        for seg in segs:
            text = seg["source_text"]
            seg_id = seg["segment_id"]
            
            # Index entities
            for ent in entities_list:
                if ent.source_name in text:
                    entities_index.setdefault(ent.entity_id, {}).setdefault("segment_ids", []).append(seg_id)
            # Index glossary terms
            for g in glossary_list:
                if g.source_term in text:
                    terms_index.setdefault(g.source_term, {}).setdefault("segment_ids", []).append(seg_id)
                    
        master_index = {
            "doc_id": doc_id,
            "entities": entities_index,
            "terms": terms_index
        }
        write_text(
            f"projects/{project_id}/memory/master_index/{doc_id}.yaml",
            yaml.dump(master_index, allow_unicode=True, sort_keys=False)
        )
        
    return {"status": "success", "message": f"Successfully rebuilt indices for {len(doc_segments)} documents"}


@router.get("/{project_id}/docs/{doc_id}/export")
@router.get("/{project_id}/chapters/{chapter_id}/export")
async def export_doc_content(
    project_id: str,
    doc_id: Optional[str] = None,
    chapter_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Export document content as a clean Markdown download.
    """
    await verify_project_member(project_id, current_user["id"], "viewer")
    
    actual_doc_id = doc_id or chapter_id
    if not actual_doc_id:
        raise HTTPException(status_code=400, detail="Missing document/chapter identifier")
        
    doc_prefix = f"projects/{project_id}/docs/{actual_doc_id}/"
    
    # Check D1 segments table first
    rows = await execute_query(
        "SELECT target_text FROM segments WHERE project_id = ? AND doc_id = ?",
        [project_id, actual_doc_id]
    )
    
    content = ""
    if rows:
        content = "\n\n".join([r["target_text"] for r in rows if r["target_text"]])
        
    if not content:
        # Fallback to R2
        meta_content = read_text(f"{doc_prefix}outputs/metadata.json")
        if meta_content:
            try:
                meta = json.loads(meta_content)
                v = meta.get("latest_version")
                output_content = read_text(f"{doc_prefix}outputs/translation_v{v}.json")
                if output_content:
                    out_data = json.loads(output_content)
                    content = out_data.get("approved_text", "")
            except Exception:
                pass
                
    if not content:
        # Fallback to draft
        content = read_text(f"{doc_prefix}draft.md") or ""
        
    if not content:
        raise HTTPException(status_code=404, detail="Document content not found")
        
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={actual_doc_id}.md"}
    )
