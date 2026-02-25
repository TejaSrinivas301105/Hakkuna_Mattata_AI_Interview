import json
import os
import re
from typing import Dict, Optional

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

MULTISPACE_REGEX = re.compile(r"\s+")


def extract_text(pdf_path: str) -> str:
    """Extract raw text from PDF using PyMuPDF."""
    text_parts = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    # Remove excessive whitespace
    text = MULTISPACE_REGEX.sub(" ", text)
    # Remove common bullet symbols
    text = text.replace("\u2022", " ").replace("•", " ")
    return text.strip()


def call_groq(parsed_json: Dict) -> Optional[str]:
    """Call Groq API with parsed JSON and get refined JSON response."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables")

    user_prompt = f"""You have been given a JSON object extracted from a resume using a rule-based parser. Your task is to refine, correct, and reformat it into clean structured JSON strictly in this format:

{{
  "name": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "github": "",
  "summary": "",
  "skills": [],
  "projects": [
    {{
      "title": "",
      "description": ""
    }}
  ],
  "experience": [],
  "education": [],
  "certifications": [],
  "achievements": []
}}

Rules:
- Fix broken words and merged text.
- Remove irrelevant tokens, section headers, and garbage data.
- Clean and deduplicate skills.
- Ensure project titles and descriptions are properly split.
- Fix email and phone formatting issues.
- Standardize all field names.
- If a field is missing or empty, return empty list or empty string.
- Return valid JSON only.
- Do NOT add explanations or markdown.

Parsed JSON:
\"\"\"
{json.dumps(parsed_json, indent=2)}
\"\"\"
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
                "content": "You are an intelligent resume parser.",
            },
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
        "temperature": 0,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"Groq API error: {e}")
        return None


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


def refine_with_groq(parsed_json: Dict) -> Dict:
    """Refine parsed JSON using Groq API.
    
    Returns:
        Dict: refined_resume_data
    """
    # Call Groq API with parsed JSON to get structured resume
    groq_response = call_groq(parsed_json)

    # Parse JSON response
    result = parse_json(groq_response)

    if not result:
        # Return empty structure if parsing fails
        result = {
            "name": "",
            "email": "",
            "phone": "",
            "linkedin": "",
            "github": "",
            "summary": "",
            "skills": [],
            "projects": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "achievements": [],
        }

    return result
