import json
import os
import sys
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
from bson import ObjectId
import io

# Auth imports
from auth import hash_password, verify_password, create_token, decode_token, get_current_user

# Add subfolders to Python path so we can import from them
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "resume_parser"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Voice_Screening"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "inteview"))

# Resume parser imports
from resume_parser import build_resume_json
from groq_parser import refine_with_groq
from groq_confidence import calculate_confidence_scores

# Database imports
from database import Database
from models import (
    CandidateResponse,
    InterviewCreate,
    InterviewDetail,
    DeepInterviewCreate,
    DeepInterviewDetail,
    InterviewReportResponse,
    candidate_doc_to_response,
    interview_doc_to_response,
    deep_interview_doc_to_response,
    report_doc_to_response,
)

# Voice screening imports
from screening_service import (
    generate_greeting,
    text_to_speech,
    transcribe_audio,
    generate_next_question,
)

# Deep interview imports
from interview_orchestrator import build_interview_plan, build_screening_summary
from voice_interview import (
    generate_followup,
    generate_interview_greeting,
    generate_interview_closing,
)
from generate_report import generate_report


# ─── App Lifecycle ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to MongoDB on startup, disconnect on shutdown."""
    await Database.connect()
    yield
    await Database.disconnect()


app = FastAPI(
    title="Hakkuna Mattata AI Interview API",
    description="Backend APIs for resume parsing, AI refinement, skill confidence scoring, voice screening, deep interviews, and report generation.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS - allow all origins for deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check ────────────────────────────────────────────────────────────────

@app.get("/api/health", summary="Health check")
async def health_check():
    return {"status": "ok", "message": "Hakkuna Mattata AI Interview API is running"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AUTH APIs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SignUpRequest(BaseModel):
    name: str
    email: str
    password: str


class SignInRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/signup", summary="Create a new account")
async def signup(body: SignUpRequest):
    """Register a new user with name, email, and password."""
    # Check if email already exists
    existing = await Database.db["users"].find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user_doc = {
        "name": body.name,
        "email": body.email,
        "password": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await Database.db["users"].insert_one(user_doc)

    # Generate JWT token
    token = create_token(
        user_id=str(result.inserted_id),
        email=body.email,
        name=body.name,
    )

    return {
        "status": "success",
        "data": {
            "token": token,
            "user": {
                "id": str(result.inserted_id),
                "name": body.name,
                "email": body.email,
            },
        },
    }


@app.post("/api/auth/signin", summary="Sign in with email and password")
async def signin(body: SignInRequest):
    """Authenticate user and return JWT token."""
    user = await Database.db["users"].find_one({"email": body.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(
        user_id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
    )

    return {
        "status": "success",
        "data": {
            "token": token,
            "user": {
                "id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"],
            },
        },
    }


@app.get("/api/auth/me", summary="Get current user")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's info."""
    return {
        "status": "success",
        "data": {
            "id": current_user["sub"],
            "name": current_user["name"],
            "email": current_user["email"],
        },
    }


# ─── Helpers ────────────────────────────────────────────────────────────────────

async def save_upload_to_temp(file: UploadFile) -> str:
    """Save an uploaded file to a temporary path and return the path."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(contents)
    tmp.close()
    return tmp.name


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RESUME PARSER APIs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.post("/api/parse-resume", summary="Upload PDF and extract resume fields")
async def parse_resume(
    file: UploadFile = File(...),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
):
    """
    Stage 1: Extract data from PDF using rule-based parser.
    Stage 2: Refine with Groq AI.
    Stage 3: Save the candidate to MongoDB.
    Returns the candidate data with DB id.
    """
    tmp_path = await save_upload_to_temp(file)

    try:
        # Stage 1 – rule-based extraction
        raw_json = build_resume_json(tmp_path)

        # Stage 2 – AI refinement
        refined = refine_with_groq(raw_json)

        # Stage 3 – save to MongoDB
        candidate_doc = {
            "name": refined.get("name", ""),
            "email": refined.get("email", ""),
            "resume_refined": refined,
            "confidence_scores": None,
            "interview_ids": [],
            "deep_interview_ids": [],
            "report_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        # Link candidate to logged-in user if authenticated
        if credentials:
            try:
                payload = decode_token(credentials.credentials)
                candidate_doc["user_id"] = payload["sub"]
            except Exception:
                pass
        result = await Database.candidates().insert_one(candidate_doc)
        candidate_doc["_id"] = result.inserted_id

        return {
            "status": "success",
            "data": candidate_doc_to_response(candidate_doc).model_dump(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ─── API 2: Confidence Scores ───────────────────────────────────────────────────

class ConfidenceScoreRequest(BaseModel):
    """Request body for confidence scoring."""
    candidate_id: str


@app.post("/api/confidence-scores", summary="Calculate & store skill confidence scores")
async def confidence_scores(body: ConfidenceScoreRequest):
    """
    Fetch the candidate's parsed resume from MongoDB, calculate
    confidence scores using Groq AI, and save them back.
    """
    try:
        # Find the candidate
        candidate = await Database.candidates().find_one(
            {"_id": ObjectId(body.candidate_id)}
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Calculate confidence scores
        scores = calculate_confidence_scores(candidate["resume_refined"])

        if scores is None:
            raise HTTPException(
                status_code=500,
                detail="Groq API failed to return confidence scores.",
            )

        # Save scores to MongoDB
        await Database.candidates().update_one(
            {"_id": ObjectId(body.candidate_id)},
            {"$set": {"confidence_scores": scores}},
        )

        return {"status": "success", "data": scores}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate confidence scores: {str(e)}",
        )


# ─── API 3: Full Pipeline ───────────────────────────────────────────────────────

@app.post("/api/full-pipeline", summary="Upload PDF → Parse → Scores → Save (all in one)")
async def full_pipeline(
    file: UploadFile = File(...),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
):
    """
    Complete pipeline:
      1. Extract data from PDF
      2. Refine with Groq AI
      3. Calculate skill confidence scores
      4. Save everything to MongoDB
    Returns candidate data + confidence scores.
    """
    tmp_path = await save_upload_to_temp(file)

    try:
        # Stage 1 – rule-based extraction
        raw_json = build_resume_json(tmp_path)

        # Stage 2 – AI refinement
        refined = refine_with_groq(raw_json)

        # Stage 3 – confidence scoring
        scores = calculate_confidence_scores(refined)

        # Stage 4 – save to MongoDB
        candidate_doc = {
            "name": refined.get("name", ""),
            "email": refined.get("email", ""),
            "resume_refined": refined,
            "confidence_scores": scores,
            "interview_ids": [],
            "deep_interview_ids": [],
            "report_ids": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        # Link candidate to logged-in user if authenticated
        if credentials:
            try:
                payload = decode_token(credentials.credentials)
                candidate_doc["user_id"] = payload["sub"]
            except Exception:
                pass
        result = await Database.candidates().insert_one(candidate_doc)
        candidate_doc["_id"] = result.inserted_id

        return {
            "status": "success",
            "data": candidate_doc_to_response(candidate_doc).model_dump(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CANDIDATE APIs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/api/candidates", summary="List all candidates")
async def list_candidates():
    """Get all candidates from the database."""
    candidates = []
    cursor = Database.candidates().find().sort("created_at", -1)
    async for doc in cursor:
        candidates.append(candidate_doc_to_response(doc).model_dump())
    return {"status": "success", "data": candidates}


@app.get("/api/candidates/{candidate_id}", summary="Get a specific candidate")
async def get_candidate(candidate_id: str):
    """Get a specific candidate by ID."""
    doc = await Database.candidates().find_one({"_id": ObjectId(candidate_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"status": "success", "data": candidate_doc_to_response(doc).model_dump()}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCREENING INTERVIEW APIs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.post("/api/start-screening", summary="Start a voice screening interview")
async def start_screening(body: InterviewCreate):
    """
    Start a new screening interview:
      1. Fetch candidate's resume from MongoDB
      2. Generate AI greeting with TTS audio
      3. Store greeting audio in GridFS
      4. Create interview record in MongoDB
    Returns the interview ID, greeting text, and greeting audio.
    """
    try:
        # Verify candidate exists
        candidate = await Database.candidates().find_one(
            {"_id": ObjectId(body.candidate_id)}
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        resume_data = candidate["resume_refined"]

        # Generate greeting text + audio
        greeting_text, greeting_audio_bytes = generate_greeting(resume_data)

        # Store greeting audio in GridFS
        greeting_audio_id = await Database.store_audio(
            filename="q1_greeting.mp3",
            file_data=greeting_audio_bytes,
            metadata={"type": "question", "question_number": 1},
        )

        # Create interview document
        interview_doc = {
            "candidate_id": ObjectId(body.candidate_id),
            "status": "in_progress",
            "target_role": body.target_role or resume_data.get("targetRole", resume_data.get("target_role", "")),
            "questions": [{"id": 1, "text": greeting_text, "audio_file_id": greeting_audio_id}],
            "responses": [],
            "conversation_history": [{"role": "assistant", "content": greeting_text}],
            "question_count": 1,
            "audio_file_ids": [greeting_audio_id],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await Database.interviews().insert_one(interview_doc)
        interview_id = result.inserted_id

        # Link interview to candidate (append to array)
        await Database.candidates().update_one(
            {"_id": ObjectId(body.candidate_id)},
            {"$push": {"interview_ids": interview_id}},
        )

        return {
            "status": "success",
            "data": {
                "interview_id": str(interview_id),
                "greeting_text": greeting_text,
                "greeting_audio_id": greeting_audio_id,
                "message": "Interview started. Use /api/screening/respond to send candidate responses.",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "ratelimit" in error_msg.lower():
            raise HTTPException(
                status_code=429,
                detail="AI service rate limit reached. Please wait a moment and try again.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start screening: {error_msg}",
        )


@app.post("/api/screening/respond", summary="Send candidate audio response, get next AI question")
async def screening_respond(interview_id: str, file: UploadFile = File(...)):
    """
    Handle one turn of the interview:
      1. Receive candidate's audio response (wav/mp3)
      2. Transcribe it to text
      3. Store response audio in GridFS
      4. Generate next AI question using Groq
      5. Convert question to speech via ElevenLabs
      6. Store question audio in GridFS
      7. Save everything to MongoDB
    Returns the transcribed response, next question text, and question audio ID.
    """
    try:
        # Fetch interview from MongoDB
        interview = await Database.interviews().find_one(
            {"_id": ObjectId(interview_id)}
        )
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        if interview["status"] == "completed":
            raise HTTPException(status_code=400, detail="Interview is already completed")

        # Fetch candidate's resume
        candidate = await Database.candidates().find_one(
            {"_id": interview["candidate_id"]}
        )
        resume_data = candidate["resume_refined"]

        question_number = interview.get("question_count", 1) + 1
        conversation_history = interview.get("conversation_history", [])

        # 1. Read uploaded audio
        audio_bytes = await file.read()

        # 2. Store candidate response audio in GridFS
        response_audio_id = await Database.store_audio(
            filename=f"r{question_number}.wav",
            file_data=audio_bytes,
            metadata={"type": "response", "question_number": question_number},
        )

        # 3. Transcribe the candidate's audio
        response_text = transcribe_audio(audio_bytes)

        # Update conversation history with candidate's response
        conversation_history.append({"role": "user", "content": response_text})

        # 4. Generate next AI question
        next_question_text, should_end = generate_next_question(
            resume=resume_data,
            conversation_history=conversation_history,
            question_number=question_number,
        )

        # 5. Convert question to speech
        question_audio_bytes = text_to_speech(next_question_text)

        # 6. Store question audio in GridFS
        question_audio_id = await Database.store_audio(
            filename=f"q{question_number}.mp3",
            file_data=question_audio_bytes,
            metadata={"type": "question", "question_number": question_number},
        )

        # Update conversation history with AI question
        conversation_history.append({"role": "assistant", "content": next_question_text})

        # 7. Determine new status
        new_status = "completed" if should_end else "in_progress"

        # 8. Save everything to MongoDB
        await Database.interviews().update_one(
            {"_id": ObjectId(interview_id)},
            {
                "$push": {
                    "responses": {"id": question_number, "text": response_text, "audio_file_id": response_audio_id},
                    "questions": {"id": question_number, "text": next_question_text, "audio_file_id": question_audio_id},
                    "audio_file_ids": {"$each": [response_audio_id, question_audio_id]},
                },
                "$set": {
                    "conversation_history": conversation_history,
                "question_count": question_number,
                "status": new_status,
            },
        },
    )

        return {
            "status": "success",
            "data": {
                "interview_id": interview_id,
                "response_text": response_text,
                "response_audio_id": response_audio_id,
                "next_question_text": next_question_text,
                "next_question_audio_id": question_audio_id,
                "interview_status": new_status,
                "question_number": question_number,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "ratelimit" in error_msg.lower():
            raise HTTPException(
                status_code=429,
                detail="AI service rate limit reached. Please wait a moment and try again.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process response: {error_msg}",
        )


@app.post("/api/interviews/{interview_id}/save-transcript", summary="Save interview transcript & audio")
async def save_transcript(interview_id: str, transcript: Dict):
    """
    Save the full interview transcript (questions + responses) and
    update the interview status to 'completed'.
    """
    interview = await Database.interviews().find_one(
        {"_id": ObjectId(interview_id)}
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    await Database.interviews().update_one(
        {"_id": ObjectId(interview_id)},
        {
            "$set": {
                "questions": transcript.get("questions", []),
                "responses": transcript.get("responses", []),
                "status": "completed",
            }
        },
    )

    return {"status": "success", "message": "Transcript saved"}


@app.post("/api/interviews/{interview_id}/upload-audio", summary="Upload interview audio file")
async def upload_audio(interview_id: str, file: UploadFile = File(...)):
    """
    Upload an audio file (mp3/wav) and store it in GridFS,
    linked to the interview.
    """
    interview = await Database.interviews().find_one(
        {"_id": ObjectId(interview_id)}
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    contents = await file.read()
    file_id = await Database.store_audio(
        filename=file.filename,
        file_data=contents,
        metadata={
            "interview_id": interview_id,
            "content_type": file.content_type,
        },
    )

    # Add audio file ID to the interview
    await Database.interviews().update_one(
        {"_id": ObjectId(interview_id)},
        {"$push": {"audio_file_ids": file_id}},
    )

    return {"status": "success", "audio_file_id": file_id}


@app.post("/api/interviews/{interview_id}/upload-all-audio", summary="Bulk upload all interview audio files")
async def upload_all_audio(interview_id: str, files: List[UploadFile] = File(...)):
    """
    Upload multiple audio files (mp3/wav) at once and store them in GridFS.
    Use this to upload all question + response audio files after the interview.
    """
    interview = await Database.interviews().find_one(
        {"_id": ObjectId(interview_id)}
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    uploaded = []
    for file in files:
        contents = await file.read()
        file_id = await Database.store_audio(
            filename=file.filename,
            file_data=contents,
            metadata={
                "interview_id": interview_id,
                "content_type": file.content_type,
                "original_filename": file.filename,
            },
        )
        uploaded.append({"filename": file.filename, "file_id": file_id})

    # Add all audio file IDs to the interview
    all_ids = [item["file_id"] for item in uploaded]
    await Database.interviews().update_one(
        {"_id": ObjectId(interview_id)},
        {"$push": {"audio_file_ids": {"$each": all_ids}}},
    )

    return {
        "status": "success",
        "message": f"{len(uploaded)} audio files uploaded",
        "data": uploaded,
    }


@app.get("/api/interviews/{interview_id}", summary="Get interview details")
async def get_interview(interview_id: str):
    """Get full interview details including transcript."""
    doc = await Database.interviews().find_one({"_id": ObjectId(interview_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Interview not found")
    return {"status": "success", "data": interview_doc_to_response(doc).model_dump()}


@app.get("/api/audio/{file_id}", summary="Download an audio file")
async def get_audio(file_id: str):
    """Download an audio file from GridFS."""
    try:
        contents, filename = await Database.get_audio(file_id)
        return StreamingResponse(
            io.BytesIO(contents),
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Audio file not found")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DEEP INTERVIEW APIs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class GeneratePlanRequest(BaseModel):
    candidate_id: str


@app.post("/api/interview/generate-plan", summary="Generate deep interview question plan")
async def api_generate_plan(body: GeneratePlanRequest):
    """
    Generate an interview question plan based on:
      1. Candidate's resume data
      2. Confidence scores
      3. Screening interview summary (if available)
    Saves the plan to a deep_interview document in MongoDB.
    """
    try:
        # Fetch candidate
        candidate = await Database.candidates().find_one(
            {"_id": ObjectId(body.candidate_id)}
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        resume_data = candidate["resume_refined"]
        conf_scores = candidate.get("confidence_scores", {})

        if not conf_scores:
            raise HTTPException(
                status_code=400,
                detail="No confidence scores found. Run confidence scoring first."
            )

        # Get screening summary from latest screening interview
        screening_summary = ""
        screening_interview_id = None
        interview_ids = candidate.get("interview_ids", [])
        # Backward compat: check legacy single field
        if not interview_ids and candidate.get("interview_id"):
            interview_ids = [candidate["interview_id"]]
        if interview_ids:
            screening_doc = await Database.interviews().find_one(
                {"_id": interview_ids[-1]}  # latest screening
            )
            if screening_doc:
                screening_summary = build_screening_summary(screening_doc)
                screening_interview_id = interview_ids[-1]

        # Generate the interview plan
        plan = build_interview_plan(resume_data, conf_scores, screening_summary)

        # Get target role
        target_role = resume_data.get("targetRole", resume_data.get("target_role", "Software Developer"))

        # Create deep interview document
        deep_doc = {
            "candidate_id": ObjectId(body.candidate_id),
            "screening_interview_id": screening_interview_id,
            "status": "planning",
            "target_role": target_role,
            "interview_plan": plan,
            "questions": [],
            "responses": [],
            "conversation_history": [],
            "question_count": 0,
            "audio_file_ids": [],
            "report_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await Database.deep_interviews().insert_one(deep_doc)
        deep_doc["_id"] = result.inserted_id

        # Link to candidate (append to array)
        await Database.candidates().update_one(
            {"_id": ObjectId(body.candidate_id)},
            {"$push": {"deep_interview_ids": result.inserted_id}},
        )

        return {
            "status": "success",
            "data": {
                "deep_interview_id": str(result.inserted_id),
                "interview_plan": plan,
                "total_questions": len(plan.get("interview_plan", [])),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")


class StartDeepInterviewRequest(BaseModel):
    candidate_id: str
    deep_interview_id: str


@app.post("/api/interview/start", summary="Start the deep technical interview")
async def api_start_deep_interview(body: StartDeepInterviewRequest):
    """
    Start the deep interview:
      1. Fetch the deep interview plan
      2. Generate greeting audio via TTS
      3. Store audio in GridFS
      4. Prepare first question
    Returns greeting + first question.
    """
    try:
        # Fetch deep interview
        deep_doc = await Database.deep_interviews().find_one(
            {"_id": ObjectId(body.deep_interview_id)}
        )
        if not deep_doc:
            raise HTTPException(status_code=404, detail="Deep interview not found")

        # Fetch candidate
        candidate = await Database.candidates().find_one(
            {"_id": ObjectId(body.candidate_id)}
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        resume_data = candidate["resume_refined"]
        personal_info = resume_data.get("personalInfo", {})
        name = resume_data.get("name", personal_info.get("name", "Candidate"))
        role = deep_doc.get("target_role", "Software Developer")

        plan_questions = deep_doc.get("interview_plan", {}).get("interview_plan", [])
        total = len(plan_questions)

        # Generate greeting
        greeting_text = generate_interview_greeting(name, role, total)

        # Generate TTS audio for greeting
        greeting_audio_bytes = text_to_speech(greeting_text)
        greeting_audio_id = await Database.store_audio(
            filename="deep_greeting.mp3",
            file_data=greeting_audio_bytes,
            metadata={"type": "greeting", "deep_interview_id": body.deep_interview_id},
        )

        # Prepare first question
        first_question = plan_questions[0] if plan_questions else None
        first_question_text = first_question["question"] if first_question else "Tell me about your experience."

        # Generate TTS for first question
        q1_audio_bytes = text_to_speech(first_question_text)
        q1_audio_id = await Database.store_audio(
            filename="deep_q1.mp3",
            file_data=q1_audio_bytes,
            metadata={"type": "question", "question_number": 1, "deep_interview_id": body.deep_interview_id},
        )

        # Update deep interview document
        conversation_history = [
            {"role": "assistant", "content": greeting_text},
            {"role": "assistant", "content": first_question_text},
        ]

        await Database.deep_interviews().update_one(
            {"_id": ObjectId(body.deep_interview_id)},
            {
                "$set": {
                    "status": "in_progress",
                    "question_count": 1,
                    "conversation_history": conversation_history,
                    "questions": [{
                        "id": 1,
                        "skill": first_question.get("skill", "General") if first_question else "General",
                        "type": first_question.get("type", "DEPTH") if first_question else "DEPTH",
                        "text": first_question_text,
                        "audio_file_id": q1_audio_id,
                    }],
                    "audio_file_ids": [greeting_audio_id, q1_audio_id],
                },
            },
        )

        return {
            "status": "success",
            "data": {
                "deep_interview_id": body.deep_interview_id,
                "greeting_text": greeting_text,
                "greeting_audio_id": greeting_audio_id,
                "first_question": {
                    "id": 1,
                    "text": first_question_text,
                    "skill": first_question.get("skill", "General") if first_question else "General",
                    "type": first_question.get("type", "DEPTH") if first_question else "DEPTH",
                    "audio_id": q1_audio_id,
                },
                "total_questions": total,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")


@app.post("/api/interview/respond", summary="Send answer audio, get follow-up or next question")
async def api_interview_respond(deep_interview_id: str, file: UploadFile = File(...)):
    """
    Handle one turn of the deep interview:
      1. Receive candidate's audio response
      2. Transcribe it
      3. Generate follow-up or move to next question
      4. Convert to TTS
      5. Store everything in GridFS + MongoDB
    """
    try:
        # Fetch deep interview
        deep_doc = await Database.deep_interviews().find_one(
            {"_id": ObjectId(deep_interview_id)}
        )
        if not deep_doc:
            raise HTTPException(status_code=404, detail="Deep interview not found")
        if deep_doc["status"] == "completed":
            raise HTTPException(status_code=400, detail="Interview is already completed")

        # Fetch candidate
        candidate = await Database.candidates().find_one(
            {"_id": deep_doc["candidate_id"]}
        )
        resume_data = candidate["resume_refined"]
        conf_scores = candidate.get("confidence_scores", {})

        plan_questions = deep_doc.get("interview_plan", {}).get("interview_plan", [])
        current_q_count = deep_doc.get("question_count", 1)
        conversation_history = deep_doc.get("conversation_history", [])

        # Current question info
        current_questions = deep_doc.get("questions", [])
        last_question = current_questions[-1] if current_questions else {}
        current_skill = last_question.get("skill", "General")
        current_type = last_question.get("type", "DEPTH")
        current_question_text = last_question.get("text", "")

        # 1. Read uploaded audio
        audio_bytes = await file.read()

        # 2. Store response audio in GridFS
        response_audio_id = await Database.store_audio(
            filename=f"deep_r{current_q_count}.wav",
            file_data=audio_bytes,
            metadata={"type": "response", "question_number": current_q_count, "deep_interview_id": deep_interview_id},
        )

        # 3. Transcribe
        response_text = transcribe_audio(audio_bytes)

        # Update conversation history
        conversation_history.append({"role": "user", "content": response_text})

        # Get candidate name for closing message
        personal_info = resume_data.get("personalInfo", {})
        name = resume_data.get("name", personal_info.get("name", "Candidate"))

        # 4. Determine if we should even ask a follow-up
        # Count how many MAIN questions (non-follow-up) have been responded to
        responses_list = deep_doc.get("responses", [])
        main_questions_answered = len(responses_list) + 1  # +1 for current response

        # Check if last question already had a follow-up
        already_had_followup = False
        if len(current_questions) >= 2:
            prev_q = current_questions[-1] if len(current_questions) > 0 else {}
            already_had_followup = prev_q.get("type") == "FOLLOWUP"
            if already_had_followup:
                # This response is to a follow-up, count the parent as the main question
                main_questions_answered = sum(1 for q in current_questions if q.get("type") != "FOLLOWUP")

        # HARD LIMIT: After 5 main questions answered, end the interview
        if main_questions_answered >= len(plan_questions) or main_questions_answered >= 5:
            should_end = True
            next_question_text = generate_interview_closing(name)
            next_skill = "Closing"
            next_type = "CLOSING"
            is_followup = False
        else:
            # Get role and skill info for the follow-up generator
            role = deep_doc.get("target_role", "")
            strong_skills = ", ".join([s for s, sc in conf_scores.items() if sc >= 0.7])
            weak_skills = ", ".join([s for s, sc in conf_scores.items() if sc < 0.4])

            # Build recent conversation history text
            recent_history = "\n".join([
                f"{'Q' if m['role'] == 'assistant' else 'A'}: {m['content']}"
                for m in conversation_history[-6:]
            ])

            followup = generate_followup(
                question=current_question_text,
                answer=response_text,
                skill=current_skill,
                conversation_history=recent_history,
                confidence_score=conf_scores.get(current_skill, 0.5),
                question_type=current_type,
                role=role,
                strong_skills=strong_skills,
                weak_skills=weak_skills,
                current_question_number=main_questions_answered,
                total_questions=min(len(plan_questions), 5),
                already_had_followup=already_had_followup,
            )

            # Determine what happens next
            should_end = False
            is_followup = False
            next_question_text = ""
            next_skill = ""
            next_type = ""

            if "END_INTERVIEW" in followup or "end_interview" in followup.lower():
                should_end = True
                next_question_text = generate_interview_closing(name)
                next_skill = "Closing"
                next_type = "CLOSING"

            elif followup.strip() == "NEXT":
                # Move to next planned question
                answered_main = sum(1 for q in current_questions if q.get("type") != "FOLLOWUP")
                next_plan_idx = answered_main

                if next_plan_idx < len(plan_questions) and next_plan_idx < 5:
                    next_q = plan_questions[next_plan_idx]
                    next_question_text = next_q["question"]
                    next_skill = next_q.get("skill", "General")
                    next_type = next_q.get("type", "DEPTH")
                else:
                    should_end = True
                    next_question_text = generate_interview_closing(name)
                    next_skill = "Closing"
                    next_type = "CLOSING"

            else:
                # Technical follow-up question
                is_followup = True
                next_question_text = followup
                next_skill = current_skill
                next_type = "FOLLOWUP"

        # 5. Generate TTS for next question
        next_audio_bytes = text_to_speech(next_question_text)
        next_q_count = current_q_count + 1

        next_audio_id = await Database.store_audio(
            filename=f"deep_q{next_q_count}.mp3",
            file_data=next_audio_bytes,
            metadata={"type": "question", "question_number": next_q_count, "deep_interview_id": deep_interview_id},
        )

        # Update conversation history
        conversation_history.append({"role": "assistant", "content": next_question_text})

        new_status = "completed" if should_end else "in_progress"

        # 6. Save to MongoDB
        await Database.deep_interviews().update_one(
            {"_id": ObjectId(deep_interview_id)},
            {
                "$push": {
                    "responses": {
                        "id": current_q_count,
                        "text": response_text,
                        "audio_file_id": response_audio_id,
                        "skill": current_skill,
                    },
                    "questions": {
                        "id": next_q_count,
                        "skill": next_skill,
                        "type": next_type,
                        "text": next_question_text,
                        "audio_file_id": next_audio_id,
                    },
                    "audio_file_ids": {"$each": [response_audio_id, next_audio_id]},
                },
                "$set": {
                    "conversation_history": conversation_history,
                    "question_count": next_q_count,
                    "status": new_status,
                },
            },
        )

        return {
            "status": "success",
            "data": {
                "deep_interview_id": deep_interview_id,
                "response_text": response_text,
                "response_audio_id": response_audio_id,
                "next_question": {
                    "id": next_q_count,
                    "text": next_question_text,
                    "skill": next_skill,
                    "type": next_type,
                    "audio_id": next_audio_id,
                    "is_followup": is_followup,
                },
                "interview_status": new_status,
                "question_number": next_q_count,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process response: {str(e)}")


class EndInterviewRequest(BaseModel):
    deep_interview_id: str


@app.post("/api/interview/end", summary="End the deep interview")
async def api_end_interview(body: EndInterviewRequest):
    """End the deep interview and mark it as completed."""
    deep_doc = await Database.deep_interviews().find_one(
        {"_id": ObjectId(body.deep_interview_id)}
    )
    if not deep_doc:
        raise HTTPException(status_code=404, detail="Deep interview not found")

    await Database.deep_interviews().update_one(
        {"_id": ObjectId(body.deep_interview_id)},
        {"$set": {"status": "completed"}},
    )

    return {"status": "success", "message": "Interview ended"}


class GenerateReportRequest(BaseModel):
    candidate_id: str


@app.post("/api/interview/generate-report", summary="Generate final evaluation report")
async def api_generate_report(body: GenerateReportRequest):
    """
    Generate comprehensive final report based on:
      1. Resume data
      2. Confidence scores
      3. Screening interview transcript
      4. Deep interview transcript
    Saves report to MongoDB.
    """
    try:
        # Fetch candidate
        candidate = await Database.candidates().find_one(
            {"_id": ObjectId(body.candidate_id)}
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Prevent duplicate report generation (e.g. double-click)
        recent_report = await Database.interview_reports().find_one(
            {"candidate_id": ObjectId(body.candidate_id)},
            sort=[("created_at", -1)],
        )
        if recent_report and recent_report.get("created_at"):
            from datetime import timedelta
            created = recent_report["created_at"]
            if isinstance(created, str):
                created = datetime.fromisoformat(created)
            if (datetime.now(timezone.utc) - created) < timedelta(seconds=60):
                return {
                    "status": "success",
                    "data": report_doc_to_response(recent_report).model_dump(),
                }

        resume_data = candidate["resume_refined"]
        conf_scores = candidate.get("confidence_scores", {})

        # Fetch latest screening interview
        screening_data = None
        screening_interview_id = None
        interview_ids = candidate.get("interview_ids", [])
        if not interview_ids and candidate.get("interview_id"):
            interview_ids = [candidate["interview_id"]]
        if interview_ids:
            screening_doc = await Database.interviews().find_one(
                {"_id": interview_ids[-1]}
            )
            if screening_doc:
                screening_data = {
                    "questions": screening_doc.get("questions", []),
                    "responses": screening_doc.get("responses", []),
                }
                screening_interview_id = interview_ids[-1]

        # Fetch latest deep interview
        deep_interview_data = None
        deep_interview_id = None
        deep_ids = candidate.get("deep_interview_ids", [])
        if not deep_ids and candidate.get("deep_interview_id"):
            deep_ids = [candidate["deep_interview_id"]]
        if deep_ids:
            deep_doc = await Database.deep_interviews().find_one(
                {"_id": deep_ids[-1]}
            )
            if deep_doc:
                deep_interview_data = {
                    "questions": deep_doc.get("questions", []),
                    "responses": deep_doc.get("responses", []),
                }
                deep_interview_id = deep_ids[-1]

        # Generate report
        report = generate_report(
            resume=resume_data,
            confidence_scores=conf_scores,
            screening_data=screening_data,
            deep_interview=deep_interview_data,
        )

        # Save report to MongoDB
        report_doc = {
            "candidate_id": ObjectId(body.candidate_id),
            "deep_interview_id": deep_interview_id,
            "screening_interview_id": screening_interview_id,
            "report": report,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await Database.interview_reports().insert_one(report_doc)

        # Link report to candidate (append to array)
        await Database.candidates().update_one(
            {"_id": ObjectId(body.candidate_id)},
            {"$push": {"report_ids": result.inserted_id}},
        )

        # Also link to deep interview if exists
        if deep_interview_id:
            await Database.deep_interviews().update_one(
                {"_id": deep_interview_id},
                {"$set": {"report_id": result.inserted_id}},
            )

        return {
            "status": "success",
            "data": {
                "report_id": str(result.inserted_id),
                "report": report,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@app.get("/api/interview/report/{candidate_id}", summary="Get stored report for a candidate")
async def api_get_report(candidate_id: str):
    """Get the evaluation report for a candidate."""
    # Find the report by candidate_id
    report_doc = await Database.interview_reports().find_one(
        {"candidate_id": ObjectId(candidate_id)},
        sort=[("created_at", -1)],
    )
    if not report_doc:
        raise HTTPException(status_code=404, detail="Report not found for this candidate")

    return {
        "status": "success",
        "data": report_doc_to_response(report_doc).model_dump(),
    }


@app.get("/api/interview/deep/{deep_interview_id}", summary="Get deep interview details")
async def api_get_deep_interview(deep_interview_id: str):
    """Get full deep interview details including transcript."""
    doc = await Database.deep_interviews().find_one({"_id": ObjectId(deep_interview_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Deep interview not found")
    return {"status": "success", "data": deep_interview_doc_to_response(doc).model_dump()}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MY DATA APIs (authenticated user's own data)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/api/my/reports", summary="Get all reports for the logged-in user")
async def api_my_reports(user: dict = Depends(get_current_user)):
    """
    Find all candidates belonging to the current user (by user_id),
    then fetch all their reports. Returns newest first.
    """
    user_id = user["sub"]

    # Find all candidates that belong to this user
    candidates = []
    async for c in Database.candidates().find({"user_id": user_id}):
        candidates.append(c)

    if not candidates:
        return {"status": "success", "data": {"reports": [], "total": 0}}

    # Collect all report IDs from all candidates (deduplicated)
    all_reports = []
    seen_ids = set()
    for candidate in candidates:
        # New format: report_ids array
        report_ids = candidate.get("report_ids", [])
        # Legacy: single report_id
        if not report_ids and candidate.get("report_id"):
            report_ids = [candidate["report_id"]]

        for rid in report_ids:
            rid_str = str(rid)
            if rid_str in seen_ids:
                continue
            seen_ids.add(rid_str)
            doc = await Database.interview_reports().find_one({"_id": rid})
            if doc:
                report_data = report_doc_to_response(doc).model_dump()
                report_data["candidate_name"] = candidate.get("name", "Unknown")
                all_reports.append(report_data)

    # Sort newest first
    all_reports.sort(key=lambda r: r.get("created_at", ""), reverse=True)

    return {
        "status": "success",
        "data": {
            "reports": all_reports,
            "total": len(all_reports),
        },
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SESSION HISTORY APIs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/api/candidates/{candidate_id}/sessions", summary="Get all interview sessions for a candidate")
async def api_get_candidate_sessions(candidate_id: str):
    """Get full session history: all screening interviews, deep interviews, and reports."""
    candidate = await Database.candidates().find_one({"_id": ObjectId(candidate_id)})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get all screening interviews
    screening_ids = candidate.get("interview_ids", [])
    # Backward compat
    if not screening_ids and candidate.get("interview_id"):
        screening_ids = [candidate["interview_id"]]

    screenings = []
    for sid in screening_ids:
        doc = await Database.interviews().find_one({"_id": sid})
        if doc:
            screenings.append(interview_doc_to_response(doc).model_dump())

    # Get all deep interviews
    deep_ids = candidate.get("deep_interview_ids", [])
    if not deep_ids and candidate.get("deep_interview_id"):
        deep_ids = [candidate["deep_interview_id"]]

    deep_interviews = []
    for did in deep_ids:
        doc = await Database.deep_interviews().find_one({"_id": did})
        if doc:
            deep_interviews.append(deep_interview_doc_to_response(doc).model_dump())

    # Get all reports
    report_ids = candidate.get("report_ids", [])
    if not report_ids and candidate.get("report_id"):
        report_ids = [candidate["report_id"]]

    reports = []
    for rid in report_ids:
        doc = await Database.interview_reports().find_one({"_id": rid})
        if doc:
            reports.append(report_doc_to_response(doc).model_dump())

    return {
        "status": "success",
        "data": {
            "candidate": candidate_doc_to_response(candidate).model_dump(),
            "screening_interviews": screenings,
            "deep_interviews": deep_interviews,
            "reports": reports,
            "total_sessions": len(screenings) + len(deep_interviews),
        },
    }


@app.get("/api/candidates/{candidate_id}/interviews", summary="List all screening interviews")
async def api_list_screening_interviews(candidate_id: str):
    """List all screening interviews for a candidate, newest first."""
    cursor = Database.interviews().find(
        {"candidate_id": ObjectId(candidate_id)}
    ).sort("created_at", -1)

    interviews = []
    async for doc in cursor:
        interviews.append(interview_doc_to_response(doc).model_dump())

    return {"status": "success", "data": interviews}


@app.get("/api/candidates/{candidate_id}/deep-interviews", summary="List all deep interviews")
async def api_list_deep_interviews(candidate_id: str):
    """List all deep interviews for a candidate, newest first."""
    cursor = Database.deep_interviews().find(
        {"candidate_id": ObjectId(candidate_id)}
    ).sort("created_at", -1)

    interviews = []
    async for doc in cursor:
        interviews.append(deep_interview_doc_to_response(doc).model_dump())

    return {"status": "success", "data": interviews}


@app.get("/api/candidates/{candidate_id}/reports", summary="List all reports")
async def api_list_reports(candidate_id: str):
    """List all reports for a candidate, newest first."""
    cursor = Database.interview_reports().find(
        {"candidate_id": ObjectId(candidate_id)}
    ).sort("created_at", -1)

    reports = []
    async for doc in cursor:
        reports.append(report_doc_to_response(doc).model_dump())

    return {"status": "success", "data": reports}


# ─── Run ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
