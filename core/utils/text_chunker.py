import re
from typing import List

def chunk_text(text: str, max_chars: int = 1500) -> List[str]:
    """
    Splits text into chunks, honoring paragraph boundaries (\\n\\n) and sentence
    boundaries (., !, ?, 。) to ensure context remains intact and segments
    do not exceed max_chars.
    """
    # 1. Split by double newline (paragraphs)
    paragraphs = re.split(r'\n\n+', text)
    
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
            
        if len(current_chunk) + len(p) + 2 <= max_chars:
            if current_chunk:
                current_chunk += "\n\n" + p
            else:
                current_chunk = p
        else:
            # Current chunk is full or paragraph is too long
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
                
            # If a single paragraph is longer than max_chars, split it by sentences
            if len(p) > max_chars:
                # Split on sentence-ending punctuation, keeping the punctuation
                sentences = re.split(r'(?<=[.!?。！？])\s+', p)
                for s in sentences:
                    s = s.strip()
                    if not s:
                        continue
                    if len(current_chunk) + len(s) + 1 <= max_chars:
                        if current_chunk:
                            current_chunk += " " + s
                        else:
                            current_chunk = s
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = s
            else:
                current_chunk = p
                
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks
