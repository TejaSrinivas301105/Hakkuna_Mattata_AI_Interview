import json
import speech_recognition as sr
from elevenlabs.client import ElevenLabs
import wave
import os
from groq import Groq
from pygame import mixer
import time
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Load resume
with open("resume.json", "r") as f:
    resume = json.load(f)

# Initialize clients
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
recognizer = sr.Recognizer()
recognizer.pause_threshold = 5.0  # Wait 2 seconds of silence before stopping
recognizer.energy_threshold = 300  # Adjust sensitivity
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
mixer.init()

interview_data = {"questions": [], "responses": []}
audio_files = []
conversation_history = []

# Initial greeting
greeting = f"Hello {resume['personalInfo']['name']}, I am your AI interviewer. Welcome to the screening call."
print(f"\n[Question 1]\n{greeting}")

audio = client.text_to_speech.convert(
    voice_id="Xb7hH8MSUJpSbSDYk0k2",
    text=greeting,
    model_id="eleven_multilingual_v2"
)

with open("q1.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)

audio_files.append("q1.mp3")
interview_data["questions"].append({"id": 1, "text": greeting, "audio": "q1.mp3"})
conversation_history.append({"role": "assistant", "content": greeting})

# Play greeting
mixer.music.load("q1.mp3")
mixer.music.play()
while mixer.music.get_busy():
    time.sleep(0.1)

# Interview loop
for i in range(2, 11):
    print("\n[Your turn - Press Enter when ready to speak, press Enter again when done]")
    input()
    
    print("Recording... (Press Enter when finished)")
    
    # Start recording in a separate thread
    import threading
    frames = []
    is_recording = True
    
    def record_audio():
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            while is_recording:
                try:
                    audio_chunk = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    frames.append(audio_chunk)
                except:
                    pass
    
    record_thread = threading.Thread(target=record_audio)
    record_thread.start()
    
    # Wait for user to press Enter
    input()
    is_recording = False
    record_thread.join()
    
    # Combine audio frames
    if frames:
        audio_input = frames[0]
        for frame in frames[1:]:
            audio_input = sr.AudioData(
                audio_input.get_raw_data() + frame.get_raw_data(),
                audio_input.sample_rate,
                audio_input.sample_width
            )
    else:
        print("No audio recorded")
        continue
    
    # Save response audio
    r_file = f"r{i}.wav"
    with open(r_file, "wb") as f:
        f.write(audio_input.get_wav_data())
    
    audio_files.append(r_file)
    
    # Transcribe response
    try:
        response_text = recognizer.recognize_google(audio_input)
        print(f"You said: {response_text}")
    except:
        response_text = "[Could not transcribe]"
    
    interview_data["responses"].append({"id": i, "text": response_text, "audio": r_file})
    conversation_history.append({"role": "user", "content": response_text})
    
    # Generate next question using AI
    messages = [
        {"role": "system", "content": f"""
    You are ARIA (AI Recruiter for Intelligent Assessment), a professional and warm technical screening interviewer.
    You are conducting an initial screening interview for {resume['personalInfo']['name']} who has applied for the role of {resume['targetRole']}.

    ---

    # CANDIDATE PROFILE
    - Name: {resume['personalInfo']['name']}
    - Role Applied: {resume['targetRole']}
    - Projects: {resume['projects']}
    - Experience: {resume['experience']}
    - Education: {resume['education']}
    - Skills: {resume['skills']}

    ---

    # YOUR GOALS
    1. Verify and validate the skills listed in the candidate's resume through natural conversation
    2. Assess depth of knowledge — not just surface-level familiarity
    3. Identify any contradictions between resume claims and verbal answers
    4. Complete the screening in under 7 minutes

    ---

    # STRICT RULES
    - ONLY ask about skills mentioned in the resume
    - NEVER ask about skills not mentioned in the resume
    - Ask ONE question at a time — never stack multiple questions
    - If the candidate says "I don't know", "no idea", or similar, politely say "No problem, let's move to the next question" and ask about a different skill
    - Ask follow-up questions if an answer is vague or too short
    - If the candidate says 'repeat', 'come again', 'say that again', or 'can you repeat' — repeat the last question word for word
    - If the candidate says 'bye', 'thank you', or indicates they want to end — immediately use the CLOSING MESSAGE and stop asking questions
    - Do not reveal scores, internal reasoning, or evaluation logic to the candidate
    - Do not ask HR or behavioural questions — this is a technical screening only
    - Keep your tone warm, professional, and encouraging — never robotic
    - After delivering the CLOSING MESSAGE, do not ask any more questions or continue the conversation

    ---

    # QUESTION STRATEGY
    - Start with a skill the candidate is most confident in to build comfort
    - Go depth-first: if a candidate answers well, ask a follow-up on the same skill before moving on
    - If a candidate gives a weak or vague answer, note it and move to the next skill
    - If the candidate's answer contradicts what is on their resume, ask ONE calm clarifying question:
    "I noticed your resume mentions X — could you elaborate a bit more on that?"

    ---

    # QUESTION TYPES TO USE
    - Project-based: "Walk me through a project where you used [skill]."
    - Depth probe: "What was the most challenging part of working with [skill]?"
    - Trade-off: "When would you choose [X] over [Y]?"
    - Contradiction probe: "Your resume mentions [X] — can you tell me more about how you used it?"
    - Follow-up: "Interesting — and how did you handle [edge case]?"

    ---

    # FLOW
    1. Greet the candidate warmly and introduce yourself
    2. Ask 5 to 7 questions based on the rules above
    3. After the final question, thank the candidate and close the session professionally

    ---

    # OPENING MESSAGE
    "Hi {resume['personalInfo']['name']}! I'm ARIA, your AI screening assistant today. 
    This will be a short conversation — around 5 to 7 minutes — where I'd love to learn more about your experience and background. 
    There are no trick questions here, just a chance for you to tell me about your work. 
    Ready to begin?"

    ---

    # CLOSING MESSAGE
    "That's all from my side, {resume['personalInfo']['name']}! 
    Thank you for your time today — you'll hear back from the team shortly regarding next steps. 
    Have a great day!"
    """}
    ]

    
    for msg in conversation_history[-6:]:
        messages.append(msg)
    
    messages.append({"role": "user", "content": f"Based on the candidate's response: If they said 'I don't know' or similar, move to next skill. If they said 'bye' or 'thank you' after closing message, output only 'END_INTERVIEW'. If they asked for clarification, repeat previous question. Otherwise ask next question (question {i} of 10). If question 7 or higher, wrap up with closing message."})
    
    response = groq_client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile",
        max_tokens=100,
        temperature=0.7
    )
    
    next_question = response.choices[0].message.content.strip()
    
    # Check if interview should end after question 6
    if i >= 7:
        closing = f"That's all from my side, {resume['personalInfo']['name']}! Thank you for your time today — you'll hear back from the team shortly regarding next steps. Have a great day!"
        print(f"\n[Closing Message]\n{closing}")
        
        # Generate and play closing audio
        audio = client.text_to_speech.convert(
            voice_id="Xb7hH8MSUJpSbSDYk0k2",
            text=closing,
            model_id="eleven_multilingual_v2"
        )
        
        q_file = f"q{i}_closing.mp3"
        with open(q_file, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        
        audio_files.append(q_file)
        interview_data["questions"].append({"id": i, "text": closing, "audio": q_file})
        
        mixer.music.load(q_file)
        mixer.music.play()
        while mixer.music.get_busy():
            time.sleep(0.1)
        
        break
    
    if "END_INTERVIEW" in next_question:
        break
    print(f"\n[Question {i}]\n{next_question}")
    
    # Generate AI voice
    audio = client.text_to_speech.convert(
        voice_id="Xb7hH8MSUJpSbSDYk0k2",
        text=next_question,
        model_id="eleven_multilingual_v2"
    )
    
    q_file = f"q{i}.mp3"
    with open(q_file, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    
    audio_files.append(q_file)
    interview_data["questions"].append({"id": i, "text": next_question, "audio": q_file})
    conversation_history.append({"role": "assistant", "content": next_question})
    
    # Play question
    mixer.music.load(q_file)
    mixer.music.play()
    while mixer.music.get_busy():
        time.sleep(0.1)

# Save interview transcript
with open("interview_transcript.json", "w") as f:
    json.dump(interview_data, f, indent=2)

print("\n✓ Interview completed!")
print(f"✓ Audio files saved: {', '.join(audio_files)}")
print("✓ Transcript saved: interview_transcript.json")
