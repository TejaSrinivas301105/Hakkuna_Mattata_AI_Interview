import json
import sys
import os

# Set Groq API key
os.environ["GROQ_API_KEY"] = "groq_api"

# Add Voice_Screening to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Voice_Screening'))

from voice_scorer import calculate_confidence_scores

# Load resume
with open("resume.json", "r") as f:
    resume_data = json.load(f)

# Load interview transcript
with open("interview_transcript.json", "r") as f:
    interview_data = json.load(f)

# Calculate scores with interview data
scores = calculate_confidence_scores(resume_data, interview_data)

if scores:
    # Save to file
    with open("confidence_scores.json", "w") as f:
        json.dump(scores, f, indent=2)
    
    # Print only JSON
    print(json.dumps(scores, indent=2))
else:
    print(json.dumps({"error": "Failed to calculate confidence scores"}, indent=2))
