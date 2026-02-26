"""
Interview Orchestrator — Generates interview question plan based on
resume data, confidence scores, and screening summary.

Used by API endpoints (no file I/O).
"""

import json
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"


def _get_groq_client() -> Groq:
    return Groq(api_key=GROQ_API_KEY)


def build_interview_plan(resume_data: dict, confidence_scores: dict, screening_summary: str = "") -> dict:
    """
    Generate interview question bank based on resume and confidence scores.

    Args:
        resume_data: Candidate's parsed/refined resume JSON
        confidence_scores: Dict of skill -> confidence score (0.0-1.0)
        screening_summary: Summary of the screening interview

    Returns:
        Dict with 'interview_plan' key containing list of question objects
    """
    # Handle both resume formats
    personal_info = resume_data.get("personalInfo", {})
    name = resume_data.get("name", personal_info.get("name", "Candidate"))
    target_role = resume_data.get("targetRole", resume_data.get("target_role", "Software Developer"))

    focus_areas = [s for s, sc in confidence_scores.items() if 0.3 <= sc < 0.6]
    contradictions = [s for s, sc in confidence_scores.items() if sc < 0.3]

    prompt = f"""
You are preparing questions for a deep technical interview.

# CANDIDATE CONTEXT
Name: {name}
Role Applied: {target_role}
Confidence Scores: {json.dumps(confidence_scores, indent=2)}
Focus Areas (verify these): {focus_areas}
Contradictions (gentle probe): {contradictions}
Already Discussed in Screening: {screening_summary}

# STRICT RULES
- Generate EXACTLY 5 questions — no more, no less
- EVERY question MUST be a real, deep TECHNICAL question
- Questions must test actual coding knowledge, system design, architecture, algorithms, or technical problem-solving
- DO NOT generate generic or behavioral questions like "tell me about a time" or "how do you approach X"
- DO NOT generate transition questions like "let's move to the next topic"
- Each question must be specific enough that a candidate needs real technical knowledge to answer
- ONLY include skills with score >= 0.3
- DO NOT repeat topics already covered in screening
- Cover the candidate's top skills — prioritize high confidence skills first

# QUESTION DISTRIBUTION (exactly 5 total)
- 2 questions on HIGH confidence skills (>= 0.7) → deep dive, edge cases, trade-offs
- 2 questions on MEDIUM confidence skills (0.4-0.69) → verify real knowledge
- 1 question on LOW confidence or contradicted skill (< 0.4) → gentle but technical probe

# QUESTION TYPES
DEPTH (deep technical dive), TRADEOFF (compare approaches), EDGE_CASE (unusual scenarios), PROJECT (real implementation details)

# EXAMPLES OF GOOD TECHNICAL QUESTIONS
- "How would you implement rate limiting in a REST API? Walk me through the algorithm and data structures you'd use."
- "Explain the difference between optimistic and pessimistic locking in databases. When would you choose one over the other?"
- "If you had to design a real-time notification system for 1 million concurrent users, what architecture would you propose?"

# EXAMPLES OF BAD QUESTIONS (DO NOT GENERATE THESE)
- "Tell me about your experience with Python"
- "Let's move on to the next topic"
- "How comfortable are you with React?"
- "Can you describe a challenging project?"

{{
  "interview_plan": [
    {{
      "skill": "skill_name",
      "confidence": 0.75,
      "priority": 1,
      "question": "Your specific technical question here",
      "type": "DEPTH",
      "follow_up": "Follow-up if answer is strong"
    }}
  ]
}}
"""

    groq_client = _get_groq_client()
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a technical interviewer. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    try:
        plan = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        print("⚠️ JSON parse failed, using empty plan")
        plan = {"interview_plan": []}

    return plan


def build_screening_summary(screening_interview: dict) -> str:
    """
    Build a text summary of the screening interview for use in the deep interview.

    Args:
        screening_interview: The screening interview document from MongoDB

    Returns:
        Summary string describing what was covered in screening
    """
    responses = screening_interview.get("responses", [])
    questions = screening_interview.get("questions", [])

    if not responses:
        return ""

    summary = f"Discussed {len(responses)} topics in screening. "

    # Extract topics covered
    topics = []
    for q in questions:
        text = q.get("text", "")
        if text:
            topics.append(text[:80])

    if topics:
        summary += f"Topics covered: {'; '.join(topics[:5])}. "

    return summary
