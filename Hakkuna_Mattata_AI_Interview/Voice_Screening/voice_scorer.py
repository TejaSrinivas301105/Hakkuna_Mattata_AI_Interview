import json
import os
from typing import Dict, Optional
import re

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def parse_json(groq_response: str) -> Optional[Dict]:
    """Parse Groq response and extract JSON safely."""
    if not groq_response:
        return None

    try:
        # Try direct JSON parsing
        return json.loads(groq_response)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", groq_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find any JSON object in the response
        json_match = re.search(r"\{.*\}", groq_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

    print(f"Failed to parse JSON from Groq response: {groq_response[:200]}")
    return None


def calculate_confidence_scores(resume_data: Dict, interview_data: Optional[Dict] = None) -> Optional[Dict]:
    """Calculate confidence scores for each skill using Groq API, optionally including interview data."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables")

    # Build interview context if available
    interview_context = ""
    if interview_data:
        interview_context = f"""

Interview Data Available:
- Questions Asked: {len(interview_data.get('questions', []))}
- Responses Given: {len(interview_data.get('responses', []))}

Interview Responses:
"""
        for response in interview_data.get('responses', []):
            flag = response.get('flag', 'clear')
            interview_context += f"- Q{response['id']}: {response['text']} [Flag: {flag}]\n"

    confidence_prompt = f"""You are a resume skill evidence evaluator.

Your task is to compute an evidence-based confidence score for each skill listed in the resume{' and interview performance' if interview_data else ''}.

Definition of skill confidence:
Skill confidence represents the strength of evidence supporting that skill in the resume, based on its presence and depth in:
- Work experience
- Projects
- Certifications
- Overall frequency of mention

Scoring Rules:

1. Evidence Weights:
- If interview data available: Work Experience=0.3, Projects=0.2, Certifications=0.1, Frequency=0.1, Interview=0.3
- If no interview: Work Experience=0.4, Projects=0.3, Certifications=0.15, Frequency=0.15

2. Interview Performance (if available):
- Clear confident answer about skill: +0.3
- Vague/unclear answer: +0.1
- "Don't know" or flagged response: -0.2
- Skill not discussed: no change

3. For each skill:
- Count how many times it appears in work experience descriptions.
- Count how many projects meaningfully use the skill.
- Check if the skill appears in certifications.
- Count total semantic mentions across resume.

4. Important:
- Consider semantic usage (e.g., FastAPI implies Python).
- Do NOT hallucinate skills not provided in the skills list.
- Only evaluate skills explicitly listed.
- If a skill appears only in the skills section and nowhere else, its confidence must be low.

5. Normalize:
After computing weighted raw scores for all skills, normalize scores between 0 and 1 by dividing each skill's raw score by the maximum raw score among all skills.

6. Minimum Confidence Score Rule:
- CRITICAL: No skill should ever receive a confidence score of 0.
- If a skill has absolutely no evidence in the resume (appears only in skills list), assign it a minimum baseline score of 0.10 to 0.15.
- This acknowledges that the candidate listed it, even if there's no supporting evidence.
- Skills with some evidence should score higher accordingly.

7. Output Rules:
- Return ONLY valid JSON.
- No explanation.
- No markdown.
- No extra text.
- Values must be floats between 0 and 1 rounded to 2 decimal places.
- Ensure ALL skills from the resume have a score (minimum 0.10, no zeros).

Resume Data:
\"\"\"
{json.dumps(resume_data, indent=2)}
\"\"\"
{interview_context}

Output Format:
{{
  "skill_name": confidence_score,
  "skill_name2": confidence_score2,
  ...
}}
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a resume skill evidence evaluator.",
            },
            {
                "role": "user",
                "content": confidence_prompt,
            }
        ],
        "temperature": 0,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        confidence_response = data["choices"][0]["message"]["content"]
        return parse_json(confidence_response)
    except requests.exceptions.RequestException as e:
        print(f"Groq API error for confidence scores: {e}")
        return None