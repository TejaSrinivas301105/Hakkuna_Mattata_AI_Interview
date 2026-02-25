# Resume Parser - Data Flow Documentation

## Overview

This resume parser uses a **two-stage pipeline** to extract and refine structured data from PDF resumes.

```
PDF File → Stage 1 (PyMuPDF) → Raw JSON → Stage 2 (Groq AI) → Refined JSON
```

---

## Stage 1: PyMuPDF Extraction

### Input
- **File**: PDF resume (binary file)
- **Path**: Temporary file path

### Process (`resume_parser.py`)

1. **Extract Text Blocks**
   ```python
   extract_text_blocks(pdf_path) → List[Dict[str, str]]
   ```
   - Uses PyMuPDF (fitz) to extract text blocks from each page
   - Returns list of text blocks with content

2. **Extract Contact Info**
   ```python
   extract_contact_info(blocks) → (name, email, phone)
   ```
   - Name: First text block at top
   - Email: Regex pattern matching
   - Phone: Regex pattern matching

3. **Detect Sections**
   ```python
   detect_sections(blocks) → Dict[str, List[str]]
   ```
   - Identifies section headers (skills, projects, experience, etc.)
   - Groups content under each section
   - Exact match for headers like "Skills", "Projects", "Experience"

4. **Clean Skills**
   ```python
   clean_skills(skill_text) → List[str]
   ```
   - Splits by commas, semicolons, bullets
   - Removes duplicates
   - Filters garbage tokens (< 3 chars, education terms)

5. **Split Projects**
   ```python
   split_project(text) → {"title": "", "description": ""}
   ```
   - Uses action keywords (developed, created, built, engineered)
   - Separates title from description

### Output (Stage 1)

```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1-234-567-8900",
  "linkedin": "https://linkedin.com/in/johndoe",
  "github": "https://github.com/johndoe",
  "summary": "Experienced software engineer with 5+ years in full-stack development",
  "skills": ["Python", "React", "AWS", "Docker"],
  "projects": [
    {
      "title": "E-commerce Platform",
      "description": "Developed a full-stack e-commerce platform using React and Node.js"
    }
  ],
  "experience": ["Software Engineer at ABC Corp (2020-2023)"],
  "education": ["B.Tech Computer Science, XYZ University (2016-2020)"],
  "certifications": ["AWS Solutions Architect"],
  "achievements": ["Won Hackathon 2022"]
}
```

**Characteristics:**
- May contain broken words from PDF formatting
- May have section headers mixed in skills
- Raw text with minimal cleanup
- Projects may have improper title/description splits

---

## Stage 2: Groq AI Refinement

### Input
- **Data**: Raw JSON from Stage 1 (Python Dict)

### Process (`groq_parser.py`)

1. **Call Groq API**
   ```python
   call_groq(parsed_json) → Optional[str]
   ```
   - Sends parsed JSON to Groq API
   - Model: `llama-3.1-8b-instant`
   - Temperature: 0 (deterministic)
   - Prompt instructs AI to refine and clean the JSON

2. **Groq API Request Structure**
   ```json
   {
     "model": "llama-3.1-8b-instant",
     "messages": [
       {
         "role": "system",
         "content": "You are an intelligent resume parser."
       },
       {
         "role": "user",
         "content": "Refine this JSON: {...}"
       }
     ],
     "temperature": 0
   }
   ```

3. **Parse JSON Response**
   ```python
   parse_json(groq_response) → Optional[Dict]
   ```
   - Extracts JSON from Groq response
   - Handles markdown code blocks
   - Falls back to regex extraction if needed

### AI Refinement Tasks
- ✅ Fix broken words (e.g., "Teleg\nram" → "Telegram")
- ✅ Remove section headers from skills
- ✅ Deduplicate skills
- ✅ Clean garbage tokens
- ✅ Fix email/phone formatting issues
- ✅ Properly split project titles and descriptions
- ✅ Standardize field names
- ✅ Remove irrelevant data

### Output (Final)

```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1-234-567-8900",
  "linkedin": "https://linkedin.com/in/johndoe",
  "github": "https://github.com/johndoe",
  "summary": "Experienced software engineer with 5+ years in full-stack development",
  "skills": ["Python", "React.js", "AWS", "Docker"],
  "projects": [
    {
      "title": "E-commerce Platform",
      "description": "Developed a full-stack e-commerce platform using React and Node.js with integrated payment gateway"
    }
  ],
  "experience": ["Software Engineer at ABC Corp (2020-2023)"],
  "education": ["B.Tech Computer Science, XYZ University (2016-2020)"],
  "certifications": ["AWS Solutions Architect"],
  "achievements": ["Won Hackathon 2022"]
}
```

---

## Integration Points

### 1. Upload Resume (Streamlit App)

```python
# streamlit_app.py
uploaded_file = st.file_uploader("Upload resume (PDF)", type=["pdf"])

# Save to temp file
with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
    tmp_file.write(uploaded_file.getbuffer())
    tmp_path = tmp_file.name
```

### 2. Stage 1 Extraction

```python
from resume_parser import build_resume_json

initial_json = build_resume_json(tmp_path)
# Returns: Dict with raw extracted data
```

### 3. Stage 2 Refinement

```python
from groq_parser import refine_with_groq

final_json = refine_with_groq(initial_json)
# Returns: Dict with cleaned, refined data
```

### 4. Display/Export

```python
import json

# Display
st.code(json.dumps(final_json, indent=2), language="json")

# Download
json_string = json.dumps(final_json, indent=2)
st.download_button("Download JSON", json_string, "resume.json")
```

---

## Environment Setup

### Required Environment Variables

Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### Dependencies

```txt
streamlit
PyMuPDF
python-dotenv
requests
```

Install:
```bash
pip install -r requirements.txt
```

---

## API Integration Example

### Using in Your Application

```python
from resume_parser import build_resume_json
from groq_parser import refine_with_groq
import json

# Parse a resume
def parse_resume(pdf_file_path: str) -> dict:
    """
    Full two-stage resume parsing pipeline
    
    Args:
        pdf_file_path: Path to PDF resume file
        
    Returns:
        dict: Structured resume data
    """
    # Stage 1: Extract with PyMuPDF
    raw_data = build_resume_json(pdf_file_path)
    
    # Stage 2: Refine with Groq AI
    refined_data = refine_with_groq(raw_data)
    
    return refined_data

# Usage
result = parse_resume("path/to/resume.pdf")
print(json.dumps(result, indent=2))
```

### REST API Endpoint Example

```python
from flask import Flask, request, jsonify
import tempfile
import os

app = Flask(__name__)

@app.route('/parse-resume', methods=['POST'])
def parse_resume_endpoint():
    """Parse uploaded resume and return JSON"""
    
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file.save(tmp.name)
        temp_path = tmp.name
    
    try:
        # Stage 1: PyMuPDF extraction
        raw_data = build_resume_json(temp_path)
        
        # Stage 2: Groq AI refinement
        final_data = refine_with_groq(raw_data)
        
        return jsonify(final_data), 200
        
    finally:
        # Clean up temp file
        os.unlink(temp_path)

if __name__ == '__main__':
    app.run(debug=True)
```

---

## Data Flow Diagram

```
┌─────────────────┐
│   PDF Upload    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Stage 1: PyMuPDF Parser    │
├─────────────────────────────┤
│ • extract_text_blocks()     │
│ • extract_contact_info()    │
│ • detect_sections()         │
│ • clean_skills()            │
│ • split_project()           │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    Raw JSON Output          │
│  (may have errors/noise)    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Stage 2: Groq AI Refiner   │
├─────────────────────────────┤
│ • call_groq()               │
│ • parse_json()              │
│ • Fix broken words          │
│ • Clean duplicates          │
│ • Standardize format        │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Final Refined JSON        │
│  (clean, structured data)   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Display / Download / API   │
└─────────────────────────────┘
```

---

## Error Handling

### PDF Parsing Errors
- Empty PDF or corrupted file → Returns empty JSON structure
- Missing sections → Returns empty arrays for those fields

### Groq API Errors
- API key missing → Raises `ValueError`
- Network timeout → Returns None, falls back to raw JSON
- JSON parsing fails → Returns empty JSON structure

### Fallback Strategy
```python
try:
    refined_data = refine_with_groq(raw_data)
except Exception as e:
    print(f"AI refinement failed: {e}")
    refined_data = raw_data  # Use raw data as fallback
```

---

## Performance Notes

- **Stage 1**: ~0.5-2 seconds (depends on PDF size)
- **Stage 2**: ~2-5 seconds (Groq API call + processing)
- **Total**: ~3-7 seconds per resume

### Optimization Tips
- Use async/await for batch processing
- Cache Groq API responses for identical inputs
- Consider rate limiting for API calls

---

## Next Steps

1. **Test with your resume**: Upload a PDF and verify output
2. **Integrate API**: Use `parse_resume()` function in your app
3. **Customize sections**: Add more section headers in `resume_parser.py`
4. **Adjust Groq prompt**: Modify prompt in `groq_parser.py` for specific needs

---

## File Structure

```
Hacksrm/
├── .env                    # API keys
├── .gitignore             # Ignore sensitive files
├── requirements.txt       # Dependencies
├── resume_parser.py       # Stage 1: PyMuPDF extraction
├── groq_parser.py         # Stage 2: Groq AI refinement
├── streamlit_app.py       # Web UI
└── data_flow.md          # This file
```

---

## Support

For issues or questions:
- Check `.env` for correct API key
- Verify PDF is not password-protected
- Ensure all dependencies are installed
- Check Groq API status and rate limits
