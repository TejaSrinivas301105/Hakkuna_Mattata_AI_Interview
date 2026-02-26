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
) -> str:
    """
    Generate follow-up question based on candidate's answer.

    Args:
        question: The question that was asked
        answer: The candidate's answer (transcribed text)
        skill: The skill being tested
        conversation_history: Recent conversation history as text
        confidence_score: Confidence score for this skill (0.0-1.0)
        question_type: Type of question (DEPTH/TRADEOFF/PROJECT/EDGE_CASE/CONTRADICTION)
        role: Role applied for
        strong_skills: Candidate's strong skills
        weak_skills: Flagged skill gaps
        contradiction_flags: Any contradictions detected

    Returns:
        Follow-up question text, "NEXT" to move on, or "END_INTERVIEW" to stop
    """
    prompt = f"""
You are ARIA, a sharp and experienced technical interviewer conducting a live interview.
Your job is to respond intelligently to the candidate's last answer.

---

# CONTEXT
Skill Being Tested : {skill}
Skill Confidence   : {confidence_score}  (0.0 = no knowledge, 1.0 = expert)
Question Asked     : {question}
Question Type      : {question_type}  (DEPTH / TRADEOFF / PROJECT / EDGE_CASE / CONTRADICTION)
Candidate's Answer : {answer}

---

# RECENT CONVERSATION HISTORY
{conversation_history}

---

# CANDIDATE PROFILE REMINDER
Role Applied     : {role}
Key Strengths    : {strong_skills}
Flagged Gaps     : {weak_skills}
Contradictions   : {contradiction_flags}

---
# CANDIDATE INTENT DETECTION
First, detect if the candidate is trying to skip, quit, or express they don't know.

## SKIP SIGNALS (candidate wants to move on)
Triggers: "skip", "next question", "can we move on", "pass", "let's skip this",
          "I'd rather not answer that", "move on please"
→ Respond warmly and move on. Return exactly: NEXT
→ Example response before NEXT:
  "Of course, no problem at all — let's move to something else."
  Then return: NEXT

## DON'T KNOW SIGNALS (candidate admits they don't know)
Triggers: "I don't know", "not sure", "no idea", "haven't used this",
          "I'm not familiar with", "I haven't worked with this", "can't answer"
→ Give them ONE gentle follow-up chance using a simpler angle:
  "No worries — even from a theoretical standpoint, how would you approach it?"
→ If they still don't know after the follow-up, return: NEXT
→ Never press more than once on something they've admitted they don't know

## END INTERVIEW SIGNALS (candidate wants to stop the interview)
Triggers: "I want to stop", "end the interview", "I'm done", "can we end this",
          "stop the interview", "I want to leave", "I need to go", "quit"
→ Acknowledge gracefully and close the session professionally.
→ Return exactly: END_INTERVIEW

## DISTRESS SIGNALS (candidate seems overwhelmed or frustrated)
Triggers: "this is too hard", "I can't do this", "I give up", "I'm stressed",
          "I don't understand any of this", "this isn't fair"
→ Pause, reassure warmly, offer to skip the current question.
→ Example: "That's completely okay — these are tough questions. 
   Let's try something different."
→ Then return: NEXT


# YOUR DECISION LOGIC

## STRONG ANSWER (detailed, correct, uses real examples)
→ Ask a deeper follow-up that builds on what they just said.
→ Probe an edge case, trade-off, or failure scenario they haven't mentioned.

## DECENT ANSWER (correct but surface-level or generic)
→ Ask for a specific real example from their own experience.
→ Push for depth without being confrontational.

## VAGUE OR UNCLEAR ANSWER (didn't directly answer, went off-topic)
→ Gently redirect and ask them to be more specific.
→ Rephrase the original question slightly if needed.

## WEAK ANSWER (significant gap, clearly unfamiliar)
→ Give them ONE chance with a simpler version of the question.
→ If still weak, return exactly: NEXT

## CONTRADICTION DETECTED (answer conflicts with resume or earlier answer)
→ Ask ONE calm, non-accusatory clarifying question.

## INTERESTING TANGENT (candidate mentioned something unplanned but relevant)
→ Pivot and probe that tangent — it often reveals real depth.

---

# STRICT RULES
- Return ONLY the follow-up question — no explanation, no label, no preamble
- Maximum 2 sentences
- Never repeat a question already asked in the conversation history
- Never reveal your evaluation logic or scoring to the candidate
- Keep tone warm, professional, and curious — never robotic or interrogating
- If moving on, return exactly the word: NEXT

---

# OUTPUT
Return either:
  - A single follow-up question (max 2 sentences), OR
  - The exact word: NEXT
"""

    groq_client = _get_groq_client()
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a technical interviewer. Be concise."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


def generate_interview_greeting(candidate_name: str, role: str, num_questions: int) -> str:
    """Generate the opening greeting for the deep interview."""
    return (
        f"Hello {candidate_name}, welcome to your technical interview for the "
        f"{role} position. I'll be asking you {num_questions} questions today. "
        f"Take your time with each answer. Let's begin."
    )


def generate_interview_closing(candidate_name: str) -> str:
    """Generate the closing message for the deep interview."""
    return (
        f"Thank you {candidate_name}. That concludes the technical interview. "
        f"We'll review your responses and get back to you soon. Have a great day!"
    )
