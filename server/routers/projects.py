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
from fastapi import APIRouter, HTTPException, Depends, Response, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse

from core.memory import ProjectMemory
from server.schemas import ProjectCreate, ProjectInfo, ProjectUpdate, DocumentRename
from server.auth import get_current_user
from core.utils.db import execute_query
from core.utils.r2 import read_text, write_text, list_files, write_binary, read_binary, delete_file

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
            "INSERT INTO projects (id, display_name, description, source_lang, target_lang, content_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [project_id, data.project_id, data.description, data.source_lang, data.target_lang, data.content_type, created_at]
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
            "description": data.description,
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
        description=proj.get("description", ""),
        source_lang=proj["source_lang"],
        target_lang=proj["target_lang"],
        content_type=proj["content_type"],
        tone_note=tone_note
    )


@router.patch("/{project_id}", response_model=ProjectInfo)
async def patch_project(
    project_id: str,
    data: ProjectUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update project metadata (display_name and description).
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    # 1. Update SQLite D1 projects table
    await execute_query(
        "UPDATE projects SET display_name = ?, description = ? WHERE id = ?",
        [data.display_name, data.description, project_id]
    )
    
    # 2. Load existing YAML from R2, update it, and write it back
    tone_note = ""
    config_path = f"projects/{project_id}/project.yaml"
    config_content = read_text(config_path)
    config_data = {}
    if config_content:
        try:
            config_data = yaml.safe_load(config_content) or {}
            tone_note = config_data.get("tone_note", "")
        except Exception:
            pass
            
    config_data["display_name"] = data.display_name
    config_data["description"] = data.description
    
    write_text(config_path, yaml.dump(config_data, allow_unicode=True))
    
    # 3. Retrieve updated info
    rows = await execute_query("SELECT * FROM projects WHERE id = ?", [project_id])
    if not rows:
        raise HTTPException(status_code=404, detail="Project not found")
    proj = rows[0]
    
    return ProjectInfo(
        project_id=proj["id"],
        description=proj.get("description", ""),
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
        "SELECT source_text, target_text FROM segments WHERE project_id = ? AND doc_id = ?",
        [project_id, actual_doc_id]
    )
    
    approved_content = ""
    source_content = ""
    if rows:
        approved_content = "\n\n".join([r["target_text"] for r in rows if r["target_text"]])
        source_content = "\n\n".join([r["source_text"] for r in rows if r["source_text"]])
        
    if not source_content:
        # Fallback to R2 assets/source.txt
        source_content = read_text(f"{doc_prefix}assets/source.txt") or ""
        
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
        "source_text": source_content,
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
    background_tasks: BackgroundTasks = None,
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
        
    if "source_text" in payload:
        source_content = payload["source_text"]
        if "<" in source_content and ">" in source_content:
            source_content = convert_html_to_markdown(source_content)
        write_text(f"{doc_prefix}assets/source.txt", source_content)
        
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

        # Index approved content into knowledge_base in background
        if background_tasks:
            from core.utils.kb_service import index_document_in_kb
            background_tasks.add_task(
                index_document_in_kb,
                project_id,
                actual_doc_id,
                approved_content
            )
            background_tasks.add_task(
                auto_generate_and_save_summary,
                project_id,
                actual_doc_id,
                approved_content
            )
        
    return {"status": "success", "message": "Document saved successfully"}


@router.delete("/{project_id}/docs/{doc_id}")
@router.delete("/{project_id}/chapters/{chapter_id}")
async def delete_project_doc(
    project_id: str,
    doc_id: Optional[str] = None,
    chapter_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a document/chapter from R2 bucket and clean up database records.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    actual_doc_id = doc_id or chapter_id
    if not actual_doc_id:
        raise HTTPException(status_code=400, detail="Missing document/chapter identifier")
        
    doc_prefix = f"projects/{project_id}/docs/{actual_doc_id}/"
    
    # Delete R2 files
    files_to_delete = list_files(doc_prefix)
    for file in files_to_delete:
        delete_file(file)
        
    # Delete D1 segments
    await execute_query(
        "DELETE FROM segments WHERE project_id = ? AND doc_id = ?",
        [project_id, actual_doc_id]
    )
    
    # Delete chat history
    await execute_query(
        "DELETE FROM chat_history WHERE project_id = ? AND doc_id = ?",
        [project_id, actual_doc_id]
    )
    
    return {"status": "success", "message": f"Document {actual_doc_id} deleted successfully"}


@router.post("/{project_id}/docs/{doc_id}/rename")
@router.post("/{project_id}/chapters/{doc_id}/rename")
async def rename_document(
    project_id: str,
    doc_id: str,
    data: DocumentRename,
    current_user: dict = Depends(get_current_user)
):
    """
    Rename a document/chapter. Renames its R2 prefix and updates references in D1.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    new_doc_id = data.new_doc_id.strip()
    if not new_doc_id:
        raise HTTPException(status_code=400, detail="Invalid new document ID")
        
    if new_doc_id == doc_id:
        return {"status": "success", "message": "Document name is unchanged"}
        
    old_prefix = f"projects/{project_id}/docs/{doc_id}/"
    new_prefix = f"projects/{project_id}/docs/{new_doc_id}/"
    
    # Check if target already exists by listing its files
    existing_files = list_files(new_prefix)
    if existing_files:
        raise HTTPException(status_code=400, detail="A document with the new name already exists")
        
    # 1. Copy files in R2 from old_prefix to new_prefix, then delete old files
    old_files = list_files(old_prefix)
    if not old_files:
        raise HTTPException(status_code=404, detail="Document files not found")
        
    for old_file in old_files:
        new_file = old_file.replace(old_prefix, new_prefix, 1)
        # Read the file from R2 and write to the new key
        file_bytes = read_binary(old_file)
        if file_bytes is not None:
            write_binary(new_file, file_bytes)
            delete_file(old_file)
            
    # 2. Also rename the master index YAML file if it exists in R2
    old_index_file = f"projects/{project_id}/memory/master_index/{doc_id}.yaml"
    new_index_file = f"projects/{project_id}/memory/master_index/{new_doc_id}.yaml"
    index_bytes = read_binary(old_index_file)
    if index_bytes is not None:
        write_binary(new_index_file, index_bytes)
        delete_file(old_index_file)
        
    # 3. Update references in SQLite D1 tables
    # tables: segments, chat_history, chapter_summaries, assets, knowledge_base
    
    # segments
    await execute_query(
        "UPDATE segments SET doc_id = ? WHERE project_id = ? AND doc_id = ?",
        [new_doc_id, project_id, doc_id]
    )
    
    # chat_history
    await execute_query(
        "UPDATE chat_history SET doc_id = ? WHERE project_id = ? AND doc_id = ?",
        [new_doc_id, project_id, doc_id]
    )
    
    # chapter_summaries
    await execute_query(
        "UPDATE chapter_summaries SET chapter_id = ? WHERE project_id = ? AND chapter_id = ?",
        [new_doc_id, project_id, doc_id]
    )
    
    # assets (update doc_id and replace old prefix in r2_path)
    await execute_query(
        "UPDATE assets SET doc_id = ?, r2_path = REPLACE(r2_path, 'docs/' || ? || '/', 'docs/' || ? || '/') WHERE project_id = ? AND doc_id = ?",
        [new_doc_id, doc_id, new_doc_id, project_id, doc_id]
    )
    
    # knowledge_base
    await execute_query(
        "UPDATE knowledge_base SET doc_id = ? WHERE project_id = ? AND doc_id = ?",
        [new_doc_id, project_id, doc_id]
    )
    
    return {"status": "success", "message": f"Document successfully renamed from {doc_id} to {new_doc_id}"}



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


@router.post("/{project_id}/fonts/upload")
async def upload_font(
    project_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    await verify_project_member(project_id, current_user["id"], "editor")
    
    filename = file.filename
    if not (filename.lower().endswith(".ttf") or filename.lower().endswith(".otf")):
        raise HTTPException(status_code=400, detail="Only .ttf and .otf font files are supported")
        
    contents = await file.read()
    r2_path = f"projects/{project_id}/fonts/{filename}"
    write_binary(r2_path, contents, file.content_type or "font/ttf")
    
    return {
        "status": "success",
        "message": f"Font {filename} uploaded successfully to R2",
        "font_name": filename
    }


@router.get("/{project_id}/fonts")
async def list_project_fonts(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    await verify_project_member(project_id, current_user["id"], "viewer")
    
    prefix = f"projects/{project_id}/fonts/"
    r2_files = list_files(prefix)
    
    custom_fonts = []
    for f in r2_files:
        parts = f.split("/")
        if parts[-1]:
            custom_fonts.append(parts[-1])
            
    defaults = ["Arial", "Georgia", "Times New Roman", "Courier New", "Impact", "Noto Sans", "Noto Sans JP", "Noto Serif"]
    
    return {
        "default_fonts": defaults,
        "custom_fonts": custom_fonts
    }


@router.get("/{project_id}/fonts/download/{font_name}")
async def download_font(
    project_id: str,
    font_name: str
):
    r2_path = f"projects/{project_id}/fonts/{font_name}"
    font_bytes = read_binary(r2_path)
    if not font_bytes:
        raise HTTPException(status_code=404, detail="Font file not found in R2")
        
    media_type = "font/otf" if font_name.lower().endswith(".otf") else "font/ttf"
    
    import io
    return StreamingResponse(
        io.BytesIO(font_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename={font_name}"}
    )


# ------------------------------------------------------------------ #
# Chapter Summarization & Knowledge Base Endpoints                  #
# ------------------------------------------------------------------ #

@router.post("/{project_id}/docs/{doc_id}/summarize")
async def summarize_chapter(
    project_id: str,
    doc_id: str,
    payload: dict = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a 2-3 sentence summary draft for the chapter translation.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    payload = payload or {}
    text_content = payload.get("text", "")
    
    # If text is not supplied, load it from R2
    if not text_content:
        doc_prefix = f"projects/{project_id}/docs/{doc_id}/"
        # Try metadata / translation output first
        meta_content = read_text(f"{doc_prefix}outputs/metadata.json")
        if meta_content:
            try:
                meta = json.loads(meta_content)
                v = meta.get("latest_version", 1)
                translation_content = read_text(f"{doc_prefix}outputs/translation_v{v}.json")
                if translation_content:
                    out = json.loads(translation_content)
                    text_content = out.get("approved_text", "")
            except Exception:
                pass
        
        # Fallback to draft or segments
        if not text_content:
            text_content = read_text(f"{doc_prefix}draft.md") or ""

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="No translation text available to summarize")

    # Call LLM to summarize
    from core.agents.candidate_generator import CandidateGenerator
    from core.memory import ProjectMemory
    
    # Instantiate with dummy ProjectMemory
    proj_mem = ProjectMemory(project_id, "ja", "vi")
    async with CandidateGenerator(proj_mem) as generator:
        system_prompt = (
            "You are a professional editor. Summarize the following chapter translation in exactly 2 to 3 concise Vietnamese sentences. "
            "Focus only on key plot events, character developments, and major changes. Do not include introductory phrases like 'Chương này kể về...'. "
            "Write the summary directly in Vietnamese."
        )
        summary = await generator.chat(system_prompt=system_prompt, message=text_content)
        
    return {"summary": summary.strip()}


@router.post("/{project_id}/docs/{doc_id}/save-summary")
async def save_chapter_summary(
    project_id: str,
    doc_id: str,
    payload: dict = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Saves or updates the chapter summary in D1.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    payload = payload or {}
    summary_text = payload.get("summary", "").strip()
    if not summary_text:
        raise HTTPException(status_code=400, detail="Summary text cannot be empty")
        
    sql = """
    INSERT OR REPLACE INTO chapter_summaries (project_id, chapter_id, summary_text, created_at)
    VALUES (?, ?, ?, ?)
    """
    await execute_query(sql, [
        project_id,
        doc_id,
        summary_text,
        datetime.now().isoformat()
    ])
    
    return {"status": "success", "message": "Chapter summary saved successfully"}


@router.post("/{project_id}/kb/upload")
async def upload_reference_doc(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a text document, chunk it, and save chunks + embeddings to D1.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    # Read text content
    contents = await file.read()
    try:
        text = contents.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Only UTF-8 encoded text files are supported")
        
    doc_id = file.filename or f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Trigger background indexing
    from core.utils.kb_service import index_document_in_kb
    background_tasks.add_task(
        index_document_in_kb,
        project_id,
        doc_id,
        text
    )
    
    return {"status": "success", "doc_id": doc_id, "message": "Document uploaded and indexing started in the background"}


@router.get("/{project_id}/kb/list")
async def list_kb_documents(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Lists unique document IDs currently indexed in the project's knowledge base.
    """
    await verify_project_member(project_id, current_user["id"], "viewer")
    
    rows = await execute_query(
        "SELECT DISTINCT doc_id FROM knowledge_base WHERE project_id = ? ORDER BY doc_id ASC",
        [project_id]
    )
    docs = [r["doc_id"] for r in rows]
    return {"documents": docs}


@router.delete("/{project_id}/kb/delete/{doc_id}")
async def delete_kb_document(
    project_id: str,
    doc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes all chunks and embeddings for the given document from the knowledge base.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    await execute_query(
        "DELETE FROM knowledge_base WHERE project_id = ? AND doc_id = ?",
        [project_id, doc_id]
    )
    return {"status": "success", "message": f"Document '{doc_id}' successfully deleted from knowledge base"}


async def auto_generate_and_save_summary(project_id: str, doc_id: str, approved_content: str):
    try:
        from core.agents.candidate_generator import CandidateGenerator
        from core.memory import ProjectMemory
        from core.utils.db import execute_query
        
        proj_mem = ProjectMemory(project_id, "ja", "vi")
        async with CandidateGenerator(proj_mem) as generator:
            system_prompt = (
                "You are a professional editor. Summarize the following chapter translation in exactly 2 to 3 concise Vietnamese sentences. "
                "Focus only on key plot events, character developments, and major changes. Do not include introductory phrases like 'Chương này kể về...'. "
                "Write the summary directly in Vietnamese."
            )
            summary = await generator.chat(system_prompt=system_prompt, message=approved_content)
            
        summary_text = summary.strip()
        if summary_text:
            sql = """
            INSERT OR REPLACE INTO chapter_summaries (project_id, chapter_id, summary_text, created_at)
            VALUES (?, ?, ?, ?)
            """
            await execute_query(sql, [
                project_id,
                doc_id,
                summary_text,
                datetime.now().isoformat()
            ])
    except Exception as e:
        print(f"Failed to auto-generate and save chapter summary: {e}")


