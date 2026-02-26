"""
Screening Service — Core logic for voice screening interviews.

Extracted from interactive_interview.py into reusable functions
that can be called by the API endpoints (turn-by-turn).
"""

import json
import os
import io
import speech_recognition as sr
from typing import Dict, List, Optional, Tuple

from elevenlabs.client import ElevenLabs
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
VOICE_ID = "Xb7hH8MSUJpSbSDYk0k2"
GROQ_MODEL = "llama-3.3-70b-versatile"


def _get_elevenlabs_client() -> ElevenLabs:
    return ElevenLabs(api_key=ELEVENLABS_API_KEY)


def _get_groq_client() -> Groq:
    return Groq(api_key=GROQ_API_KEY)


def _build_system_prompt(resume: Dict) -> str:
    """Build the ARIA system prompt from resume data."""
    # Handle both resume formats:
    #   Format A (from interactive_interview): resume['personalInfo']['name'], resume['targetRole']
    #   Format B (from groq_parser):           resume['name'], no targetRole field

    name = resume.get("name", "")
    if not name:
        personal_info = resume.get("personalInfo", {})
        name = personal_info.get("name", "Candidate")

    target_role = resume.get("targetRole", resume.get("target_role", "Software Developer"))
    projects = resume.get("projects", [])
    experience = resume.get("experience", [])
    education = resume.get("education", [])
    skills = resume.get("skills", [])

    return f"""
    You are ARIA (AI Recruiter for Intelligent Assessment), a professional and warm technical screening interviewer.
    You are conducting an initial screening interview for {name} who has applied for the role of {target_role}.

    ---

    # CANDIDATE PROFILE
    - Name: {name}
    - Role Applied: {target_role}
    - Projects: {projects}
    - Experience: {experience}
    - Education: {education}
    - Skills: {skills}

    ---

    # YOUR GOALS
    1. Verify and validate the skills listed in the candidate's resume through natural conversation
    2. Assess depth of knowledge — not just surface-level familiarity
    3. Identify any contradictions between resume claims and verbal answers
    4. Complete the screening in under 7 minutes

    ---

    # STRICT RULES
    - ONLY ask about skills mentioned in the resume
    - NEVER ask about skills not mentioned in the resume
    - Ask ONE question at a time — never stack multiple questions
    - If the candidate says "I don't know", "no idea", or similar, politely say "No problem, let's move to the next question" and ask about a different skill
    - Ask follow-up questions if an answer is vague or too short
    - If the candidate says 'repeat', 'come again', 'say that again', or 'can you repeat' — repeat the last question word for word
    - If the candidate says 'bye', 'thank you', or indicates they want to end — immediately use the CLOSING MESSAGE and stop asking questions
    - Do not reveal scores, internal reasoning, or evaluation logic to the candidate
    - Do not ask HR or behavioural questions — this is a technical screening only
    - Keep your tone warm, professional, and encouraging — never robotic
    - After delivering the CLOSING MESSAGE, do not ask any more questions or continue the conversation

    ---

    # QUESTION STRATEGY
    - Start with a skill the candidate is most confident in to build comfort
    - Go depth-first: if a candidate answers well, ask a follow-up on the same skill before moving on
    - If a candidate gives a weak or vague answer, note it and move to the next skill
    - If the candidate's answer contradicts what is on their resume, ask ONE calm clarifying question:
    "I noticed your resume mentions X — could you elaborate a bit more on that?"

    ---

    # QUESTION TYPES TO USE
    - Project-based: "Walk me through a project where you used [skill]."
    - Depth probe: "What was the most challenging part of working with [skill]?"
    - Trade-off: "When would you choose [X] over [Y]?"
    - Contradiction probe: "Your resume mentions [X] — can you tell me more about how you used it?"
    - Follow-up: "Interesting — and how did you handle [edge case]?"

    ---

    # FLOW
    1. Greet the candidate warmly and introduce yourself
    2. Ask 5 to 7 questions based on the rules above
    3. After the final question, thank the candidate and close the session professionally

    ---

    # OPENING MESSAGE
    "Hi {name}! I'm ARIA, your AI screening assistant today. 
    This will be a short conversation — around 5 to 7 minutes — where I'd love to learn more about your experience and background. 
    There are no trick questions here, just a chance for you to tell me about your work. 
    Ready to begin?"

    ---

    # CLOSING MESSAGE
    "That's all from my side, {name}! 
    Thank you for your time today — you'll hear back from the team shortly regarding next steps. 
    Have a great day!"
    """


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Core Functions (called by API endpoints)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_greeting(resume: Dict) -> Tuple[str, bytes]:
    """
    Generate the initial greeting text and audio.
    Returns: (greeting_text, audio_bytes)
    """
    name = resume.get("name", "")
    if not name:
        name = resume.get("personalInfo", {}).get("name", "Candidate")

    greeting = f"Hello {name}, I am your AI interviewer. Welcome to the screening call."

    # Generate TTS audio
    audio_bytes = text_to_speech(greeting)

    return greeting, audio_bytes


def text_to_speech(text: str) -> bytes:
    """Convert text to speech using ElevenLabs. Returns audio bytes (mp3)."""
    client = _get_elevenlabs_client()
    audio_generator = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        text=text,
        model_id="eleven_multilingual_v2",
    )

    # Collect all chunks into bytes
    audio_bytes = b""
    for chunk in audio_generator:
        audio_bytes += chunk

    return audio_bytes


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribe audio bytes to text using Groq Whisper API.
    Handles webm, wav, mp3 and other formats from browser MediaRecorder.
    Returns the transcribed text.
    """
    import tempfile

    groq_client = _get_groq_client()

    # Write audio to a temporary file (Groq API needs a file-like object)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    try:
        tmp.write(audio_bytes)
        tmp.close()

        with open(tmp.name, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language="en",
            )

        text = transcription.text.strip()
        return text if text else "[No speech detected]"

    except Exception as e:
        print(f"Transcription error: {e}")
        return "[Could not transcribe]"
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


def generate_next_question(
    resume: Dict,
    conversation_history: List[Dict],
    question_number: int,
) -> Tuple[str, bool]:
    """
    Generate the next interview question using Groq AI.

    Args:
        resume: The candidate's parsed resume JSON
        conversation_history: List of {"role": "...", "content": "..."} messages
        question_number: Current question number (2-10)

    Returns: (question_text, should_end_interview)
    """
    name = resume.get("name", "")
    if not name:
        name = resume.get("personalInfo", {}).get("name", "Candidate")

    # Check if interview should end (question 7+)
    if question_number >= 7:
        closing = (
            f"That's all from my side, {name}! "
            f"Thank you for your time today — you'll hear back from the team shortly "
            f"regarding next steps. Have a great day!"
        )
        return closing, True

    # Build messages for Groq
    system_prompt = _build_system_prompt(resume)
    messages = [{"role": "system", "content": system_prompt}]

    # Add recent conversation history (last 6 messages)
    for msg in conversation_history[-6:]:
        messages.append(msg)

    messages.append({
        "role": "user",
        "content": (
            f"Based on the candidate's response: If they said 'I don't know' or similar, "
            f"move to next skill. If they said 'bye' or 'thank you' after closing message, "
            f"output only 'END_INTERVIEW'. If they asked for clarification, repeat previous "
            f"question. Otherwise ask next question (question {question_number} of 10). "
            f"If question 7 or higher, wrap up with closing message."
        ),
    })



    groq_client = _get_groq_client()
    response = groq_client.chat.completions.create(
        messages=messages,
        model=GROQ_MODEL,
        max_tokens=100,
        temperature=0.7,
    )


    next_question = response.choices[0].message.content.strip()

    # Check if AI decided to end the interview
    if "END_INTERVIEW" in next_question:
        return next_question, True

    return next_question, False
