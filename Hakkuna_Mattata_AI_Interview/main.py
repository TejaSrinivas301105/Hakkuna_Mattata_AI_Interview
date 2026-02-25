import json
import os
import sys
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
from bson import ObjectId
import io

# Auth imports
from auth import hash_password, verify_password, create_token, get_current_user

# Add subfolders to Python path so we can import from them
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "resume_parser"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Voice_Screening"))

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
    candidate_doc_to_response,
    interview_doc_to_response,
)

# Voice screening imports
from screening_service import (
    generate_greeting,
    text_to_speech,
    transcribe_audio,
    generate_next_question,
)


# ─── App Lifecycle ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to MongoDB on startup, disconnect on shutdown."""
    await Database.connect()
    yield
    await Database.disconnect()


app = FastAPI(
    title="Hakkuna Mattata AI Interview API",
    description="Backend APIs for resume parsing, AI refinement, skill confidence scoring, and voice screening.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow the React frontend (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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


@app.post("/api/parse-resume", summary="Upload PDF → Parse → Save to DB")
async def parse_resume(file: UploadFile = File(...)):
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
            "interview_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate confidence scores: {str(e)}",
        )


# ─── API 3: Full Pipeline ───────────────────────────────────────────────────────

@app.post("/api/full-pipeline", summary="Upload PDF → Parse → Scores → Save (all in one)")
async def full_pipeline(file: UploadFile = File(...)):
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
            "interview_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
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
#  INTERVIEW APIs
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

    # Link interview to candidate
    await Database.candidates().update_one(
        {"_id": ObjectId(body.candidate_id)},
        {"$set": {"interview_id": interview_id}},
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


# ─── Run ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
