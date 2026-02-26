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
    interview_ids: List[str] = []
    deep_interview_ids: List[str] = []
    report_ids: List[str] = []
    created_at: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Interview Models (Screening)
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
#  Deep Interview Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class DeepInterviewCreate(BaseModel):
    """Data for starting a deep technical interview."""
    candidate_id: str


class DeepInterviewDetail(BaseModel):
    """Full deep interview data returned from the API."""
    id: str
    candidate_id: str
    screening_interview_id: Optional[str] = None
    status: str  # "pending" | "planning" | "in_progress" | "completed"
    target_role: str
    interview_plan: Optional[Dict] = None
    questions: List[Dict] = []
    responses: List[Dict] = []
    conversation_history: List[Dict] = []
    question_count: int = 0
    audio_file_ids: List[str] = []
    report_id: Optional[str] = None
    created_at: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Interview Report Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class InterviewReportResponse(BaseModel):
    """Full report data returned from the API."""
    id: str
    candidate_id: str
    deep_interview_id: Optional[str] = None
    screening_interview_id: Optional[str] = None
    report: Dict
    created_at: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helper: Convert MongoDB document → response model
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _to_str_list(doc: dict, array_key: str, legacy_key: str) -> List[str]:
    """Get list of IDs, with backward compat for old single-value fields."""
    # New format: array of IDs
    arr = doc.get(array_key, [])
    if arr:
        return [str(x) for x in arr]
    # Legacy format: single ID
    single = doc.get(legacy_key)
    if single:
        return [str(single)]
    return []


def candidate_doc_to_response(doc: dict) -> CandidateResponse:
    """Convert a MongoDB candidate document to a CandidateResponse."""
    return CandidateResponse(
        id=str(doc["_id"]),
        name=doc.get("name", ""),
        email=doc.get("email", ""),
        resume_refined=doc.get("resume_refined", {}),
        confidence_scores=doc.get("confidence_scores"),
        interview_ids=_to_str_list(doc, "interview_ids", "interview_id"),
        deep_interview_ids=_to_str_list(doc, "deep_interview_ids", "deep_interview_id"),
        report_ids=_to_str_list(doc, "report_ids", "report_id"),
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


def deep_interview_doc_to_response(doc: dict) -> DeepInterviewDetail:
    """Convert a MongoDB deep interview document to a DeepInterviewDetail."""
    return DeepInterviewDetail(
        id=str(doc["_id"]),
        candidate_id=str(doc.get("candidate_id", "")),
        screening_interview_id=str(doc["screening_interview_id"]) if doc.get("screening_interview_id") else None,
        status=doc.get("status", "pending"),
        target_role=doc.get("target_role", ""),
        interview_plan=doc.get("interview_plan"),
        questions=doc.get("questions", []),
        responses=doc.get("responses", []),
        conversation_history=doc.get("conversation_history", []),
        question_count=doc.get("question_count", 0),
        audio_file_ids=doc.get("audio_file_ids", []),
        report_id=str(doc["report_id"]) if doc.get("report_id") else None,
        created_at=str(doc.get("created_at", datetime.now(timezone.utc).isoformat())),
    )


def report_doc_to_response(doc: dict) -> InterviewReportResponse:
    """Convert a MongoDB report document to an InterviewReportResponse."""
    return InterviewReportResponse(
        id=str(doc["_id"]),
        candidate_id=str(doc.get("candidate_id", "")),
        deep_interview_id=str(doc["deep_interview_id"]) if doc.get("deep_interview_id") else None,
        screening_interview_id=str(doc["screening_interview_id"]) if doc.get("screening_interview_id") else None,
        report=doc.get("report", {}),
        created_at=str(doc.get("created_at", datetime.now(timezone.utc).isoformat())),
    )
