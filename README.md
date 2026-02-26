
---

## 🔥 Key Features

### 🧠 Skill Graph Extraction
- Extracts skills from resume
- Assigns confidence scores per skill
- Detects contradictions during screening

### 🎙 AI Voice Interview (ElevenLabs)
- Natural human-like interviewer voice
- Adaptive questioning
- Real-time transcript generation

### 🔍 RAG-Based Adaptive Engine
- Uses resume + screening transcript
- Depth-first skill probing
- Difficulty control based on confidence scores

### 👁 Real-Time Proctoring
- YOLO-based face detection
- Multi-face detection
- No-face detection
- Glitch suppression (sliding window logic)
- Warning → Termination state machine

### 📊 AI Evaluation
Each answer is scored based on:
- Technical Accuracy
- Depth of Knowledge
- Consistency
- Communication clarity

### 🔐 Decentralized Data Storage
Stored securely on DataHaven:
- Resume
- Screening transcript
- Interview transcript
- Skill graph
- Evaluation report

Candidates retain ownership of their data.

---

## 🛠 Tech Stack

### Frontend
- React
- TailwindCSS
- Framer Motion
- Recharts

### Backend
- FastAPI
- Python
- Node.js (optional modules)

### AI & ML
- LLM (Groq / GPT)
- RAG Architecture
- ElevenLabs (Voice AI)
- Ultralytics YOLO (Face Detection)
- OpenCV

### Storage
- DataHaven (Testnet)

---

## 📁 Project Structure
