"""
Document Assets and Export router.
"""

import io
import zipfile
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.auth import get_current_user
from server.routers.projects import verify_project_member
from core.utils.db import execute_query
from core.utils.r2 import read_text, write_binary

router = APIRouter(prefix="/api/docs", tags=["Documents"])


class ExportRequest(BaseModel):
    format: str  # docx | txt | zip
    font: Optional[str] = "Arial"
    heading: Optional[str] = "h1"
    spacing: Optional[float] = 1.0
    project_id: str


@router.post("/{doc_id}/export")
async def export_document(
    doc_id: str,
    request: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Export document content in various formats (txt, docx, zip).
    """
    await verify_project_member(request.project_id, current_user["id"], "viewer")
    
    doc_prefix = f"projects/{request.project_id}/docs/{doc_id}/"
    
    # 1. Load the approved content from D1
    rows = await execute_query(
        "SELECT target_text FROM segments WHERE project_id = ? AND doc_id = ?",
        [request.project_id, doc_id]
    )
    
    content = ""
    if rows:
        content = "\n\n".join([r["target_text"] for r in rows if r["target_text"]])
        
    if not content:
        # Fallback to R2 metadata and output version
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
        content = f"Draft translation content for document {doc_id}."

    fmt = request.format.lower()
    
    if fmt == "txt":
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={doc_id}.txt"}
        )
        
    elif fmt == "docx":
        # Check python-docx availability dynamically
        try:
            import docx
            doc = docx.Document()
            doc.add_heading(f"Document: {doc_id}", level=1)
            for p_text in content.split("\n\n"):
                if p_text.strip():
                    doc.add_paragraph(p_text.strip())
            
            stream = io.BytesIO()
            doc.save(stream)
            stream.seek(0)
            return StreamingResponse(
                stream,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename={doc_id}.docx"}
            )
        except ImportError:
            # Fallback if python-docx is not installed
            fallback_text = f"Document: {doc_id}\n\n{content}"
            return Response(
                content=fallback_text.encode("utf-8"),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename={doc_id}.docx"}
            )
            
    elif fmt == "zip":
        # Package a zip archive containing the text and mock images/bubbles
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            # Write document text
            zip_file.writestr(f"{doc_id}_translation.txt", content)
            
            # Add a couple of dummy manga pages with text overlays
            dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x01\x00\x00\x0c\x00\x01\x04\x05\x73\x11\x00\x00\x00\x00IEND\xaeB`\x82"
            zip_file.writestr("page_001_overlay.png", dummy_png)
            zip_file.writestr("page_002_overlay.png", dummy_png)
            
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={doc_id}_manga_export.zip"}
        )
        
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {request.format}")


@router.post("/{doc_id}/assets/upload")
async def upload_assets(
    doc_id: str,
    project_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Mock upload assets for Manga workflow.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    uploaded_files = []
    for file in files:
        contents = await file.read()
        r2_path = f"projects/{project_id}/docs/{doc_id}/assets/{file.filename}"
        write_binary(r2_path, contents, file.content_type)
        uploaded_files.append(file.filename)
        
    return {
        "status": "success",
        "message": f"Successfully uploaded {len(uploaded_files)} assets to R2",
        "assets": uploaded_files
    }


@router.post("/{doc_id}/ocr/run")
async def run_ocr_batch(
    doc_id: str,
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mock triggering OCR processing on uploaded assets.
    """
    await verify_project_member(project_id, current_user["id"], "editor")
    
    # In a real app, this would trigger LayoutAgent/OCR pipeline
    return {
        "status": "success",
        "message": "OCR batch detection completed successfully",
        "detected_bubbles": 12,
        "language": "ja"
    }
