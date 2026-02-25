from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Candidate Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CandidateCreate(BaseModel):
    """Data stored when a resume is first parsed."""
    name: str = ""
    email: str = ""
    resume_refined: Dict = {}
    confidence_scores: Optional[Dict] = None


class CandidateResponse(BaseModel):
    """Response model for a candidate."""
    id: str
    name: str
    email: str
    resume_refined: Dict
    confidence_scores: Optional[Dict] = None
    interview_id: Optional[str] = None
    created_at: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Interview Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class InterviewQuestion(BaseModel):
    id: int
    text: str
    audio_file_id: Optional[str] = None


class InterviewResponse(BaseModel):
    id: int
    text: str
    audio_file_id: Optional[str] = None


class InterviewCreate(BaseModel):
    """Data for starting a new interview."""
    candidate_id: str
    target_role: str = ""


class InterviewDetail(BaseModel):
    """Full interview data returned from the API."""
    id: str
    candidate_id: str
    status: str  # "pending" | "in_progress" | "completed"
    target_role: str
    questions: List[InterviewQuestion] = []
    responses: List[InterviewResponse] = []
    created_at: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helper: Convert MongoDB document → response model
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def candidate_doc_to_response(doc: dict) -> CandidateResponse:
    """Convert a MongoDB candidate document to a CandidateResponse."""
    return CandidateResponse(
        id=str(doc["_id"]),
        name=doc.get("name", ""),
        email=doc.get("email", ""),
        resume_refined=doc.get("resume_refined", {}),
        confidence_scores=doc.get("confidence_scores"),
        interview_id=str(doc["interview_id"]) if doc.get("interview_id") else None,
        created_at=str(doc.get("created_at", datetime.now(timezone.utc).isoformat())),
    )


def interview_doc_to_response(doc: dict) -> InterviewDetail:
    """Convert a MongoDB interview document to an InterviewDetail."""
    return InterviewDetail(
        id=str(doc["_id"]),
        candidate_id=str(doc.get("candidate_id", "")),
        status=doc.get("status", "pending"),
        target_role=doc.get("target_role", ""),
        questions=doc.get("questions", []),
        responses=doc.get("responses", []),
        created_at=str(doc.get("created_at", datetime.now(timezone.utc).isoformat())),
    )
