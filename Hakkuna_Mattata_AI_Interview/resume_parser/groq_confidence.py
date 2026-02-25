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


def calculate_confidence_scores(resume_data: Dict) -> Optional[Dict]:
    """Calculate confidence scores for each skill using Groq API."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables")

    confidence_prompt = f"""You are a resume skill evidence evaluator.

Your task is to compute an evidence-based confidence score for each skill listed in the resume.

Definition of skill confidence:
Skill confidence represents the strength of evidence supporting that skill in the resume, based on its presence and depth in:
- Work experience
- Projects
- Certifications
- Overall frequency of mention

Scoring Rules:

1. Evidence Weights:
- Work Experience weight = 0.4
- Projects weight = 0.3
- Certifications weight = 0.15
- Frequency of mention weight = 0.15

2. For each skill:
- Count how many times it appears in work experience descriptions.
- Count how many projects meaningfully use the skill.
- Check if the skill appears in certifications.
- Count total semantic mentions across resume.

3. Important:
- Consider semantic usage (e.g., FastAPI implies Python).
- Do NOT hallucinate skills not provided in the skills list.
- Only evaluate skills explicitly listed.
- If a skill appears only in the skills section and nowhere else, its confidence must be low.

4. Normalize:
After computing weighted raw scores for all skills, normalize scores between 0 and 1 by dividing each skill's raw score by the maximum raw score among all skills.

5. Minimum Confidence Score Rule:
- CRITICAL: No skill should ever receive a confidence score of 0.
- If a skill has absolutely no evidence in the resume (appears only in skills list), assign it a minimum baseline score of 0.10 to 0.15.
- This acknowledges that the candidate listed it, even if there's no supporting evidence.
- Skills with some evidence should score higher accordingly.

6. Output Rules:
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
