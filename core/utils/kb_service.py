import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.utils.db import execute_query
from core.utils.text_chunker import chunk_text
from core.utils.embeddings import get_embedding, cosine_similarity

async def index_document_in_kb(project_id: str, doc_id: str, text: str) -> None:
    """
    Deletes existing chunks for the given doc_id, splits the text into chunks,
    generates embeddings using Cloudflare Workers AI, and saves them to the D1 knowledge_base.
    """
    # 1. Clean up existing chunks for this document
    await execute_query(
        "DELETE FROM knowledge_base WHERE project_id = ? AND doc_id = ?",
        [project_id, doc_id]
    )

    # 2. Chunk text
    chunks = chunk_text(text, max_chars=1500)
    if not chunks:
        return

    # 3. Process each chunk
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
            
        emb = get_embedding(chunk)
        # Store embedding as JSON string, default to empty array if embedding call failed/fallback
        emb_json = json.dumps(emb) if emb else "[]"
        
        sql = """
        INSERT INTO knowledge_base (project_id, doc_id, chunk_text, embedding, created_at)
        VALUES (?, ?, ?, ?, ?)
        """
        await execute_query(sql, [
            project_id,
            doc_id,
            chunk,
            emb_json,
            datetime.now().isoformat()
        ])

async def search_kb(project_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Performs a hybrid search:
    - Attempts to get an embedding for the query.
    - If successful, ranks all project chunks by Cosine Similarity and returns top matches.
    - If it fails (rate limits, no credentials, network issue), falls back to SQL LIKE search.
    """
    query_emb = get_embedding(query)
    
    # 1. Vector Search Flow
    if query_emb:
        # Load all candidate chunks for this project
        rows = await execute_query(
            "SELECT doc_id, chunk_text, embedding FROM knowledge_base WHERE project_id = ?",
            [project_id]
        )
        
        matches = []
        for r in rows:
            try:
                chunk_emb = json.loads(r["embedding"])
                if chunk_emb and isinstance(chunk_emb, list):
                    sim = cosine_similarity(query_emb, chunk_emb)
                    # Filter threshold: only keep matches with positive similarity
                    if sim > 0.25:
                        matches.append({
                            "doc_id": r["doc_id"],
                            "text": r["chunk_text"],
                            "score": round(sim, 4),
                            "type": "semantic"
                        })
            except Exception:
                continue
                
        # Sort by similarity descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limit]
        
    # 2. Fallback Keyword Search Flow
    else:
        rows = []
        # Only try exact phrase matching if the query is reasonably short
        if len(query) < 100:
            try:
                like_pattern = f"%{query}%"
                rows = await execute_query(
                    "SELECT doc_id, chunk_text FROM knowledge_base WHERE project_id = ? AND chunk_text LIKE ? LIMIT ?",
                    [project_id, like_pattern, limit]
                )
            except Exception as e:
                print(f"[KB Search] Exact phrase LIKE query failed (ignoring): {e}")
                rows = []
        
        # If exact phrase match returns nothing, search for individual words/keywords
        if not rows:
            # Filter out common Vietnamese stop words and short terms
            stop_words = {"là", "của", "gì", "thì", "và", "nhưng", "trong", "ngoài", "trên", "dưới"}
            keywords = [w.strip("?,.!\"'()[]") for w in query.split() if len(w) > 2 and w.lower() not in stop_words]
            if keywords:
                conditions = []
                params = [project_id]
                for kw in keywords[:4]:  # limit to top 4 keywords to keep queries efficient
                    conditions.append("chunk_text LIKE ?")
                    params.append(f"%{kw}%")
                
                sql = f"SELECT doc_id, chunk_text FROM knowledge_base WHERE project_id = ? AND ({' OR '.join(conditions)}) LIMIT ?"
                params.append(limit)
                rows = await execute_query(sql, params)
        
        matches = []
        for r in rows:
            matches.append({
                "doc_id": r["doc_id"],
                "text": r["chunk_text"],
                "score": 1.0,
                "type": "keyword"
            })
        return matches
