"""
Report Generator — Generates comprehensive final evaluation report
based on resume, confidence scores, screening data, and deep interview data.

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


def generate_report(
    resume: dict,
    confidence_scores: dict,
    screening_data: dict = None,
    deep_interview: dict = None,
) -> dict:
    """
    Generate comprehensive final evaluation report.

    Args:
        resume: Candidate's parsed/refined resume JSON
        confidence_scores: Dict of skill -> confidence score (0.0-1.0)
        screening_data: Screening interview document from MongoDB (optional)
        deep_interview: Deep interview document from MongoDB (optional)

    Returns:
        Report dict with candidate_summary, skill_assessment, interview_analysis, etc.
    """
    # Safety: ensure resume is a dict
    if isinstance(resume, str):
        try:
            resume = json.loads(resume)
        except (json.JSONDecodeError, TypeError):
            resume = {}

    # Handle both resume formats
    personal_info = resume.get("personalInfo", {}) if isinstance(resume.get("personalInfo"), dict) else {}
    name = resume.get("name", personal_info.get("name", "Candidate"))
    target_role = resume.get("targetRole", resume.get("target_role", "Software Developer"))
    experience = resume.get("experience", [])
    education = resume.get("education", [])

    # Build education string safely — items can be strings or dicts
    edu_str = "Not specified"
    if education and len(education) > 0:
        first_edu = education[0]
        if isinstance(first_edu, dict):
            edu_str = f"{first_edu.get('degree', 'N/A')} from {first_edu.get('institution', 'N/A')}"
        elif isinstance(first_edu, str):
            edu_str = first_edu

    # Count experience safely — items can be strings or dicts
    exp_count = len(experience) if isinstance(experience, list) else 0

    # Build screening section
    screening_section = "Not conducted"
    if screening_data:
        screening_questions = screening_data.get("questions", [])
        screening_responses = screening_data.get("responses", [])
        # Ensure responses are serializable (items may be strings or dicts)
        safe_responses = []
        for r in screening_responses:
            if isinstance(r, dict):
                safe_responses.append(r)
            else:
                safe_responses.append({"text": str(r)})
        screening_section = f"""
Total Questions: {len(screening_questions)}
Total Responses: {len(screening_responses)}

Screening Responses:
{json.dumps(safe_responses, indent=2)}
"""

    # Build deep interview section
    deep_section = "Not conducted"
    if deep_interview:
        deep_questions = deep_interview.get("questions", [])
        deep_responses = deep_interview.get("responses", [])
        # Ensure responses are serializable
        safe_deep_responses = []
        for r in deep_responses:
            if isinstance(r, dict):
                safe_deep_responses.append(r)
            else:
                safe_deep_responses.append({"text": str(r)})
        deep_section = f"""
Total Questions: {len(deep_questions)}
Total Responses: {len(deep_responses)}

Deep Interview Responses:
{json.dumps(safe_deep_responses, indent=2)}
"""

    prompt = f"""
You are a senior technical hiring manager preparing a final evaluation report.

# CANDIDATE INFORMATION
Name: {name}
Role Applied: {target_role}
Experience: {exp_count} positions
Education: {edu_str}

# INITIAL CONFIDENCE SCORES (Resume Analysis)
{json.dumps(confidence_scores, indent=2)}

# SCREENING INTERVIEW PERFORMANCE
{screening_section}

# DEEP TECHNICAL INTERVIEW PERFORMANCE
{deep_section}

---

# YOUR TASK
Generate a comprehensive final evaluation report in JSON format.

# REPORT STRUCTURE
{{
  "candidate_summary": {{
    "name": "{name}",
    "role": "{target_role}",
    "overall_recommendation": "STRONG_HIRE | HIRE | MAYBE | NO_HIRE",
    "overall_score": 0.0-10.0,
    "key_strengths": ["strength1", "strength2", "strength3"],
    "key_concerns": ["concern1", "concern2"],
    "summary": "2-3 sentence executive summary"
  }},
  "skill_assessment": {{
    "skill_name": {{
      "initial_confidence": 0.0-1.0,
      "interview_performance": "STRONG | GOOD | WEAK | NOT_ASSESSED",
      "final_rating": 0.0-10.0,
      "evidence": "What they demonstrated",
      "gaps": "What was missing or unclear"
    }}
  }},
  "interview_analysis": {{
    "screening": {{
      "performance": "STRONG | GOOD | WEAK",
      "highlights": ["point1", "point2"],
      "red_flags": ["flag1", "flag2"]
    }},
    "deep_technical": {{
      "performance": "STRONG | GOOD | WEAK",
      "highlights": ["point1", "point2"],
      "red_flags": ["flag1", "flag2"]
    }}
  }},
  "detailed_evaluation": {{
    "technical_depth": {{
      "score": 0.0-10.0,
      "comment": "Assessment of technical knowledge depth"
    }},
    "communication": {{
      "score": 0.0-10.0,
      "comment": "Clarity and articulation"
    }},
    "problem_solving": {{
      "score": 0.0-10.0,
      "comment": "Approach to technical challenges"
    }},
    "honesty": {{
      "score": 0.0-10.0,
      "comment": "Willingness to admit knowledge gaps"
    }},
    "cultural_fit": {{
      "score": 0.0-10.0,
      "comment": "Alignment with role requirements"
    }}
  }},
  "next_steps": {{
    "recommendation": "PROCEED_TO_ONSITE | ADDITIONAL_ROUND | REJECT | HOLD",
    "focus_areas_for_next_round": ["area1", "area2"],
    "questions_to_probe": ["question1", "question2"]
  }}
}}

# EVALUATION CRITERIA
- Compare resume claims vs actual interview performance
- Identify contradictions between what's listed and what was demonstrated
- Note "I don't know" responses and unclear answers
- Assess depth of knowledge vs surface-level familiarity
- Consider both screening and deep interview performance
- Be honest but professional in assessment

Return ONLY valid JSON.
"""

    groq_client = _get_groq_client()
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a senior hiring manager. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    try:
        report = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        report = {
            "candidate_summary": {
                "name": name,
                "role": target_role,
                "overall_recommendation": "MAYBE",
                "overall_score": 5.0,
                "key_strengths": [],
                "key_concerns": ["Report generation failed — manual review required"],
                "summary": "Unable to generate automated report. Manual review recommended."
            },
            "skill_assessment": {},
            "interview_analysis": {},
            "detailed_evaluation": {},
            "next_steps": {"recommendation": "HOLD"}
        }

    return report
