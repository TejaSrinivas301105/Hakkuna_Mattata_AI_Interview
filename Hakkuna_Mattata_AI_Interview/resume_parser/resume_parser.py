import re
from typing import Dict, List, Tuple

import fitz  # PyMuPDF


SECTION_HEADERS = [
    "skills",
    "technical skills",
    "soft skills",
    "projects",
    "experience",
    "work experience",
    "internships",
    "education",
    "certifications",
    "achievements",
    "summary",
    "professional summary",
    "executive summary",
    "about",
    "objective",
    "profile",
    "linkedin",
]

SECTION_HEADER_MAP = {
    "skills": "skills",
    "technical skills": "skills",
    "soft skills": "skills",
    "projects": "projects",
    "experience": "experience",
    "work experience": "experience",
    "internships": "experience",
    "education": "education",
    "certifications": "certifications",
    "achievements": "achievements",
    "summary": "summary",
    "professional summary": "summary",
    "executive summary": "summary",
    "about": "summary",
    "objective": "summary",
    "profile": "summary",
    "linkedin": "linkedin",
}

LINKEDIN_REGEX = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com[^\s]*|(?:🔗|linkedin|in)[:\s—]+([a-zA-Z0-9._-]+)")
GITHUB_REGEX = re.compile(r"(?:https?://)?(?:www\.)?github\.com[^\s]*|(?:🐙|github|gh)[:\s—]+([a-zA-Z0-9._-]+)")

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_REGEX = re.compile(
    r"(\+?\d{1,3}[\s.-]?)?(\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}"
)
BULLET_SPLIT_REGEX = re.compile(r"[\u2022\u2023\u25E6\u2043\u2219\-\*]\s+")
SKILL_SPLIT_REGEX = re.compile(r"[,;|]")
MULTISPACE_REGEX = re.compile(r"\s+")
HYPHEN_LINEBREAK_REGEX = re.compile(r"-\s*\n\s*")
LINEBREAK_SPLIT_REGEX = re.compile(r"(\w)\n(\w)")
SKILL_GARBAGE_REGEX = re.compile(r"^[A-Za-z]$")

EDU_TERMS = {
    "university",
    "college",
    "institute",
    "school",
    "bachelor",
    "master",
    "phd",
    "degree",
}

PROJECT_KEYWORDS = ["developed", "created", "built", "engineered"]


def extract_text_blocks(pdf_path: str) -> List[Dict[str, str]]:
    """Extract text blocks from a PDF using PyMuPDF (fitz)."""
    blocks: List[Dict[str, str]] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            # Each block is (x0, y0, x1, y1, text, block_no, block_type)
            for block in page.get_text("blocks"):
                text = block[4].strip()
                if not text:
                    continue
                blocks.append({"text": text})
    return blocks


def fix_broken_words(text: str) -> str:
    """Fix broken words caused by PDF line breaks and hyphenation."""
    # Remove hyphen + newline breaks (e.g., "Engine-\nering" -> "Engineering")
    text = HYPHEN_LINEBREAK_REGEX.sub("", text)
    # Merge words split across newlines (e.g., "Teleg\nram" -> "Telegram")
    text = LINEBREAK_SPLIT_REGEX.sub(r"\1\2", text)
    return text


def clean_text(text: str) -> str:
    """Clean bullets, normalize whitespace, and trim."""
    text = fix_broken_words(text)
    # Replace common bullet symbols with spaces
    text = text.replace("\u2022", " ")
    # Normalize multiple spaces and newlines
    text = MULTISPACE_REGEX.sub(" ", text)
    return text.strip()


def detect_sections(blocks: List[Dict[str, str]]) -> Dict[str, List[str]]:
    """Group block text under detected section headers."""
    sections: Dict[str, List[str]] = {
        "skills": [],
        "projects": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "achievements": [],
        "summary": [],
        "linkedin": [],
    }
    current_section = None
    header_set = {header.lower() for header in SECTION_HEADERS}

    for block in blocks:
        text = clean_text(block["text"])
        normalized = text.lower().strip(":").strip()

        # Check for exact header match
        matched_section = None
        if normalized in header_set:
            matched_section = SECTION_HEADER_MAP[normalized]
        else:
            # Check for partial match (e.g., "Professional Summary" contains "summary")
            # Sort by length descending to match longer headers first
            sorted_headers = sorted(header_set, key=len, reverse=True)
            for header in sorted_headers:
                # More aggressive matching - check if header appears as substring
                if header in normalized and len(header) > 2:
                    matched_section = SECTION_HEADER_MAP.get(header)
                    if matched_section:
                        break

        if matched_section:
            current_section = matched_section
            continue

        if current_section:
            sections[current_section].append(text)

    return sections


def extract_summary_direct(blocks: List[Dict[str, str]]) -> str:
    """Directly extract summary from blocks by finding content after contact info and before Skills."""
    summary_content = []
    capture_mode = False
    summary_header_found_at = -1
    
    # Patterns that indicate we should start capturing summary
    summary_triggers = ["executive summary", "professional summary", "summary", "profile", "about", "objective"]
    
    # Patterns that indicate we should stop capturing summary
    stop_triggers = ["skills", "technical skills", "soft skills", "projects", "experience", "education", "certifications", "achievements", "awards", "languages"]
    
    # First pass: find the summary header
    for i, block in enumerate(blocks):
        text = clean_text(block["text"])
        normalized = text.lower().strip()
        
        for trigger in summary_triggers:
            if trigger == normalized or normalized.startswith(trigger):
                summary_header_found_at = i
                capture_mode = True
                break
        
        if capture_mode:
            break
    
    # Second pass: capture content after summary header until stop trigger
    if summary_header_found_at >= 0:
        for i in range(summary_header_found_at + 1, len(blocks)):
            text = clean_text(blocks[i]["text"])
            normalized = text.lower().strip()
            
            # Check if we hit a stop trigger
            is_stop_trigger = False
            for stop in stop_triggers:
                if stop == normalized or normalized.startswith(stop):
                    is_stop_trigger = True
                    break
            
            if is_stop_trigger:
                break
            
            # Capture non-empty content
            if text.strip() and len(text) > 3:
                summary_content.append(text)
    
    # Join and clean the summary
    summary = " ".join(summary_content).strip()
    
    # Remove extra whitespace
    summary = re.sub(r'\s+', ' ', summary)
    
    return summary


def extract_contact_info(blocks: List[Dict[str, str]]) -> Tuple[str, str, str, str, str]:
    """Extract name, email, phone, linkedin, and github from the top blocks."""
    name = ""
    email = ""
    phone = ""
    linkedin = ""
    github = ""

    # Name: first non-empty block at the top
    if blocks:
        name = clean_text(blocks[0]["text"]).strip()

    combined_text = "\n".join(block["text"] for block in blocks)

    # Find email without merging unrelated line breaks
    lines = [line.strip() for line in combined_text.split("\n") if line.strip()]
    for line in lines:
        email_match = EMAIL_REGEX.search(line)
        if email_match:
            email = email_match.group(0)
            break
    if not email:
        # Try joining adjacent lines only when the first line is long enough
        for i in range(len(lines) - 1):
            if len(lines[i]) < 3:
                continue
            candidate = lines[i] + lines[i + 1]
            email_match = EMAIL_REGEX.search(candidate)
            if email_match:
                email = email_match.group(0)
                break

    # Normalize whitespace for phone matching without joining letters
    combined_text_for_phone = MULTISPACE_REGEX.sub(" ", combined_text)
    phone_match = PHONE_REGEX.search(combined_text_for_phone)
    if phone_match:
        phone = phone_match.group(0)

    # Extract LinkedIn - handle URLs and emoji-prefixed usernames
    linkedin_match = LINKEDIN_REGEX.search(combined_text)
    if linkedin_match:
        try:
            # Try to get captured group (username from emoji pattern)
            if linkedin_match.group(1):
                linkedin = linkedin_match.group(1)
            else:
                linkedin = linkedin_match.group(0)
        except IndexError:
            linkedin = linkedin_match.group(0)

    # Extract GitHub - handle URLs and emoji-prefixed usernames
    github_match = GITHUB_REGEX.search(combined_text)
    if github_match:
        try:
            # Try to get captured group (username from emoji pattern)
            if github_match.group(1):
                github = github_match.group(1)
            else:
                github = github_match.group(0)
        except IndexError:
            github = github_match.group(0)

    return name, email, phone, linkedin, github


def clean_skills(skill_text: str) -> List[str]:
    """Clean and deduplicate skills into a list."""
    skill_text = clean_text(skill_text)
    skill_text = re.sub(r"\b(technical skills|soft skills)\b", " ", skill_text, flags=re.I)

    parts: List[str] = []
    for part in BULLET_SPLIT_REGEX.split(skill_text):
        for token in SKILL_SPLIT_REGEX.split(part):
            clean = clean_text(token)
            if clean:
                parts.append(clean)

    cleaned: List[str] = []
    seen = set()
    for item in parts:
        lower = item.lower()
        if len(item) < 3:
            continue
        if SKILL_GARBAGE_REGEX.match(item):
            continue
        if any(term in lower for term in EDU_TERMS):
            continue
        if lower not in seen:
            cleaned.append(item)
            seen.add(lower)
    return cleaned


def split_project(text: str) -> Dict[str, str]:
    """Split project text into title and description using action keywords."""
    cleaned = clean_text(text)
    lower = cleaned.lower()

    for keyword in PROJECT_KEYWORDS:
        idx = lower.find(keyword)
        if idx != -1:
            title = cleaned[:idx].strip(" -:")
            description = cleaned[idx:].strip()
            return {"title": title, "description": description}

    # Fallback: first sentence as title, rest as description
    if "." in cleaned:
        first, rest = cleaned.split(".", 1)
        return {"title": first.strip(), "description": rest.strip()}

    return {"title": cleaned, "description": ""}


def build_resume_json(pdf_path: str) -> Dict[str, object]:
    """Build structured resume JSON from a PDF."""
    blocks = extract_text_blocks(pdf_path)
    name, email, phone, linkedin, github = extract_contact_info(blocks)
    sections = detect_sections(blocks)

    # Clean and normalize skills
    raw_skills = " ".join(sections.get("skills", []))
    skills_parts = clean_skills(raw_skills)

    # Convert project blocks into title/description pairs
    projects = [split_project(block) for block in sections.get("projects", [])]

    # Extract summary using direct method to bypass section detection issues
    summary = extract_summary_direct(blocks)

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "summary": summary,
        "skills": skills_parts,
        "projects": projects,
        "experience": sections.get("experience", []),
        "education": sections.get("education", []),
        "certifications": sections.get("certifications", []),
        "achievements": sections.get("achievements", []),
    }
