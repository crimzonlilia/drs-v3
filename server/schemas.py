"""
Pydantic Request & Response Schemas for the REST API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    project_id: str = Field(..., example="one-piece-vi")
    source_lang: str = Field("ja", example="ja")
    target_lang: str = Field("vi", example="vi")
    content_type: str = Field("manga", example="manga")
    tone_note: str = Field("", example="Thân thiện, trẻ trung, dùng từ ngữ hiện đại")


class ProjectInfo(BaseModel):
    project_id: str
    source_lang: str
    target_lang: str
    content_type: str
    tone_note: str


class TranslateRequest(BaseModel):
    project_id: str
    source_text: str
    chapter_or_doc: str
    source_lang: str
    target_lang: str
    content_type: str = "general"


class TranslateResponse(BaseModel):
    session_id: str
    draft: str
    review_note: str
    check_report: Dict[str, Any]


class CorrectionInput(BaseModel):
    correction_type: str
    source_term: Optional[str] = None
    original_text: str
    corrected_text: str
    note: Optional[str] = None


class ApproveRequest(BaseModel):
    final_text: str
    corrections: List[CorrectionInput] = []


class SeedRequest(BaseModel):
    topic: str
    source_lang: str
    target_lang: str


# ------------------------------------------------------------------ #
# Authentication Schemas                                              #
# ------------------------------------------------------------------ #

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    username: str
    email: Optional[str] = None


class GlossaryAddInput(BaseModel):
    source_term: str
    target_term: str
    source_lang: str
    target_lang: str
    context_note: Optional[str] = ""


class EntityAddInput(BaseModel):
    entity_id: str
    canonical_name: str
    source_name: str
    entity_type: str = "character"
    source_lang: str
    target_lang: str
    pronouns: Optional[str] = ""
    notes: Optional[str] = ""


class StyleRuleAddInput(BaseModel):
    rule_id: str
    category: str = "tone"
    description: str
    example_before: Optional[str] = ""
    example_after: Optional[str] = ""
    source_lang: Optional[str] = ""
    target_lang: Optional[str] = ""



