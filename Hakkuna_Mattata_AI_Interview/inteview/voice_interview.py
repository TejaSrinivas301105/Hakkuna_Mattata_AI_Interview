"""
Voice Interview Service — Generates follow-up questions and manages
interview conversation flow for the deep technical interview.

Used by API endpoints (no desktop I/O).
Reuses screening_service for TTS and transcription.
"""

import json
import os
from typing import Tuple
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Hard limit: exactly 5 main questions, max 1 follow-up per question
MAX_MAIN_QUESTIONS = 5


def _get_groq_client() -> Groq:
    return Groq(api_key=GROQ_API_KEY)


def generate_followup(
    question: str,
    answer: str,
    skill: str,
    conversation_history: str,
    confidence_score: float = 0.5,
    question_type: str = "DEPTH",
    role: str = "",
    strong_skills: str = "",
    weak_skills: str = "",
    contradiction_flags: str = "",
    current_question_number: int = 1,
    total_questions: int = 5,
    already_had_followup: bool = False,
) -> str:
    """
    Generate a technical follow-up based on the candidate's answer.

    Returns:
        - A technical follow-up question string, OR
        - "NEXT" to move to next planned question, OR
        - "END_INTERVIEW" if candidate requests to stop
    """

    # If this question already had a follow-up, always move to next
    if already_had_followup:
        return "NEXT"

    prompt = f"""You are a technical interviewer evaluating a candidate's answer.

QUESTION ASKED: {question}
CANDIDATE'S ANSWER: {answer}
SKILL BEING TESTED: {skill}
QUESTION {current_question_number} OF {total_questions}

TASK: Decide whether to ask ONE technical follow-up or move on.

RULES:
1. If the answer is STRONG (detailed, correct, shows depth) → Return exactly: NEXT
2. If the answer is WEAK or VAGUE → Ask ONE specific technical follow-up to probe deeper
3. If the candidate said "I don't know" or "skip" or "next" → Return exactly: NEXT
4. If the candidate said "stop" or "end" or "quit" → Return exactly: END_INTERVIEW

CRITICAL CONSTRAINTS:
- Your follow-up MUST be a specific technical question — never say things like "let's move on" or "great answer" or "ok we'll move to the next topic"
- The follow-up must test a concrete technical concept (e.g. "What happens if two threads access that HashMap simultaneously?" or "How would you handle a network partition in that design?")
- Maximum 2 sentences
- NO commentary, NO praise, NO transitions — ONLY the technical question itself
- If in doubt, return NEXT

OUTPUT: Return ONLY one of:
- A single technical follow-up question (max 2 sentences)
- The exact word: NEXT
- The exact word: END_INTERVIEW"""

    groq_client = _get_groq_client()
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a strict technical interviewer. Return only a technical question or the word NEXT. Nothing else."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=80,
        temperature=0.3
    )

    result = response.choices[0].message.content.strip()

    # Safety check: if the response isn't clearly technical and isn't NEXT/END_INTERVIEW,
    # default to NEXT to prevent non-technical filler
    if result not in ("NEXT", "END_INTERVIEW"):
        # Check if it looks like a transition phrase instead of a real question
        filler_phrases = [
            "let's move", "moving on", "next topic", "move to", "great answer",
            "good answer", "well done", "nice", "thank you", "thanks for",
            "that's a good", "interesting", "i appreciate", "ok so",
            "alright", "now let's", "shall we", "we'll move", "let me move",
        ]
        lower = result.lower()
        if any(phrase in lower for phrase in filler_phrases):
            return "NEXT"
        # Must end with a question mark to be a real question
        if "?" not in result:
            return "NEXT"

    return result


def generate_interview_greeting(candidate_name: str, role: str, num_questions: int) -> str:
    """Generate the opening greeting for the deep interview."""
    return (
        f"Hello {candidate_name}, welcome to your technical interview for the "
        f"{role} position. I'll be asking you {num_questions} technical questions today. "
        f"Take your time with each answer. Let's begin."
    )


def generate_interview_closing(candidate_name: str) -> str:
    """Generate the closing message for the deep interview."""
    return (
        f"Thank you {candidate_name}. That concludes the technical interview. "
        f"We'll review your responses and get back to you soon. Have a great day!"
    )
