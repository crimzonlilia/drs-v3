import os
import json
import httpx
from typing import List, Optional

CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")

def get_embedding(text: str) -> Optional[List[float]]:
    """
    Generates a 1024-dimensional embedding vector for the given text using
    Cloudflare Workers AI @cf/baai/bge-m3.
    If credentials are missing or the API call fails, returns None to allow
    fallback logic to kick in.
    """
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        # Graceful fallback: return None (which triggers keyword LIKE fallback)
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/baai/bge-m3"
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                result_data = resp.json()
                if result_data.get("success"):
                    # The response format for embeddings is typically:
                    # {"result": {"data": [[0.1, 0.2, ...]]}} or {"result": {"data": [0.1, 0.2, ...]}}
                    result = result_data.get("result", {})
                    data = result.get("data", [])
                    if data:
                        # Handle both single list or list of list response structures
                        if isinstance(data[0], list):
                            return data[0]
                        return data
            # Handle rate limiting or other API errors gracefully
            return None
    except Exception:
        # Network timeout or other connection errors: fallback gracefully
        return None

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Computes the cosine similarity between two float vectors.
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = sum(a * a for a in v1) ** 0.5
    norm_v2 = sum(b * b for b in v2) ** 0.5
    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)
