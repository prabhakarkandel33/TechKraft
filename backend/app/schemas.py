from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from enum import Enum


class CandidateStatus(str, Enum):
    new = "new"
    reviewed = "reviewed"
    hired = "hired"
    rejected = "rejected"
    archived = "archived"  # soft delete state


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    # PDF requirement: role is NEVER accepted from client
    # no role field here at all,safer to remove the field than to ignore

    


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str
    email: str
    role: str


class CandidateResponse(BaseModel):
    model_config = {"exclude_none": True} 

    id: str
    name: str
    email: str
    role_applied: str
    status: str
    skills: list[str]
    created_at: str
    internal_notes: Optional[str] = None  # only populated for admin


class CandidateListResponse(BaseModel):
    model_config = {"exclude_none": True} 

    data: list[CandidateResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class ScoreRequest(BaseModel):
    category: str
    score: int
    note: Optional[str] = None

    @field_validator("score")
    @classmethod
    def score_must_be_valid(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("score must be between 1 and 5")
        return v

    @field_validator("category")
    @classmethod
    def category_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("category cannot be empty")
        return v.strip()


class ScoreResponse(BaseModel):
    id: str
    candidate_id: str
    category: str
    score: int
    reviewer_id: str
    note: Optional[str]
    created_at: str


class CandidateDetailResponse(BaseModel):
    model_config = {"exclude_none": True}

    id: str
    name: str
    email: str
    role_applied: str
    status: str
    skills: list[str]
    created_at: str
    internal_notes: Optional[str] = None
    scores: list[ScoreResponse] = []
    summary: Optional[str] = None


class SummaryResponse(BaseModel):
    candidate_id: str
    summary: str
    generated_at: str


class InternalNotesRequest(BaseModel):
    internal_notes: str


class CandidateFilters(BaseModel):
    status: Optional[str] = None
    role_applied: Optional[str] = None
    skill: Optional[str] = None
    keyword: Optional[str] = None
    page: int = 1
    page_size: int = 20

    @field_validator("page_size")
    @classmethod
    def cap_page_size(cls, v):
        # PDF specifies max 50
        return min(v, 50)

    @field_validator("page")
    @classmethod
    def page_must_be_positive(cls, v):
        if v < 1:
            raise ValueError("page must be >= 1")
        return v