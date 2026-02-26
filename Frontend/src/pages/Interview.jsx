import { useState, useEffect, useRef } from "react";
import { useUploadStatus } from "../context/UploadContext";
import Waveform from "../components/ui/Waveform";
import {
  generateInterviewPlan,
  startDeepInterview,
  sendInterviewResponse,
  endInterview,
  getAudioUrl,
} from "../services/api";

export default function InterviewPage({ onNavigate }) {
  const { candidateId, confidenceScores, resumeData } = useUploadStatus();

  // State
  const [phase, setPhase] = useState("loading"); // loading | planning | ready | active | completed
  const [plan, setPlan] = useState(null);
  const [deepInterviewId, setDeepInterviewId] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [qIndex, setQIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [speaking, setSpeaking] = useState(false);
  const [recording, setRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [transcript, setTranscript] = useState([]);
  const [liveSkills, setLiveSkills] = useState([]);
  const [error, setError] = useState("");
  const [timeLeft, setTimeLeft] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(new Audio());
  const timerRef = useRef(null);
  const countdownRef = useRef(null);

  // Build live skills from confidence scores
  useEffect(() => {
    if (confidenceScores) {
      const colors = ["var(--cyan)", "var(--violet)", "var(--amber)", "var(--green)", "var(--cyan)", "var(--violet)"];
      const skills = Object.entries(confidenceScores)
        .slice(0, 6)
        .map(([name, score], i) => ({
          name,
          pct: Math.round(score * 100),
          color: colors[i % colors.length],
        }));
      setLiveSkills(skills);
    }
  }, [confidenceScores]);

  // Generate interview plan on mount
  useEffect(() => {
    if (!candidateId) return;

    async function init() {
      try {
        setPhase("planning");
        const res = await generateInterviewPlan(candidateId);
        const data = res.data;
        setPlan(data.interview_plan);
        const diId = data.deep_interview_id;
        setDeepInterviewId(diId);
        setTotalQuestions(data.total_questions);

        // Auto-start the interview (skip question preview)
        setPhase("active");
        setTimeLeft(data.total_questions * 180);

        const startRes = await startDeepInterview(candidateId, diId);
        const startData = startRes.data;

        setCurrentQuestion(startData.first_question);
        setQIndex(1);
        setTotalQuestions(startData.total_questions);

        // Play greeting audio
        setSpeaking(true);
        const audio = audioRef.current;
        audio.src = getAudioUrl(startData.greeting_audio_id);
        audio.onended = () => {
          audio.src = getAudioUrl(startData.first_question.audio_id);
          audio.onended = () => setSpeaking(false);
          audio.play().catch(() => setSpeaking(false));
        };
        audio.play().catch(() => setSpeaking(false));

        setTranscript([
          { type: "greeting", text: startData.greeting_text },
          { type: "question", text: startData.first_question.text, skill: startData.first_question.skill },
        ]);
      } catch (err) {
        setError(err.message || "Failed to start interview");
        setPhase("loading");
      }
    }
    init();
  }, [candidateId]);

  // Recording timer
  useEffect(() => {
    if (recording) {
      setRecordingTime(0);
      timerRef.current = setInterval(() => setRecordingTime(t => t + 1), 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [recording]);

  // Countdown timer
  useEffect(() => {
    if (phase === "active" && timeLeft > 0) {
      countdownRef.current = setInterval(() => setTimeLeft(t => t > 0 ? t - 1 : 0), 1000);
    }
    return () => { if (countdownRef.current) clearInterval(countdownRef.current); };
  }, [phase, timeLeft]);

  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  // Handle mic toggle (record / stop)
  const handleMic = async () => {
    if (!recording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event) => {
          audioChunksRef.current.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          stream.getTracks().forEach(track => track.stop());

          // Send to backend
          setSpeaking(true);

          try {
            const res = await sendInterviewResponse(deepInterviewId, audioBlob);
            const data = res.data;

            // Update transcript
            setTranscript(prev => [
              ...prev,
              { type: "response", text: data.response_text },
              { type: "question", text: data.next_question.text, skill: data.next_question.skill, questionType: data.next_question.type },
            ]);

            setCurrentQuestion(data.next_question);
            setQIndex(data.question_number);

            // Play next question audio
            if (data.next_question.audio_id) {
              const audio = audioRef.current;
              audio.src = getAudioUrl(data.next_question.audio_id);
              audio.onended = () => setSpeaking(false);
              audio.play().catch(() => setSpeaking(false));
            } else {
              setSpeaking(false);
            }

            // Check if interview is done
            if (data.interview_status === "completed") {
              setPhase("completed");
              setTimeout(() => onNavigate("Report"), 3000);
            }
          } catch (err) {
            setError(err.message || "Failed to process response");
            setSpeaking(false);
          }
        };

        mediaRecorder.start();
        setRecording(true);
      } catch (err) {
        setError("Microphone access denied. Please allow microphone access.");
      }
    } else {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
        setRecording(false);
      }
    }
  };

  // End interview
  const handleEndInterview = async () => {
    try {
      await endInterview(deepInterviewId);
      setPhase("completed");
      onNavigate("Report");
    } catch (err) {
      setError(err.message || "Failed to end interview");
    }
  };

  const depthLevels = ["Basic", "Intermediate", "Advanced"];
  const currentDepth = currentQuestion?.type === "FOLLOWUP" ? "Intermediate" :
    (currentQuestion?.type === "DEPTH" || currentQuestion?.type === "EDGE_CASE") ? "Advanced" : "Intermediate";

  // ─── LOADING / PLANNING PHASE ─────────────────────────────────────
  if (phase === "loading" || phase === "planning") {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--void)", paddingTop: 60 }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 20, animation: "pulse 1.5s ease-in-out infinite" }}>🧠</div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, color: "var(--white)", marginBottom: 12 }}>
            Generating Interview Plan
          </div>
          <div style={{ fontSize: 14, color: "var(--text-2)", maxWidth: 400, lineHeight: 1.6 }}>
            Analyzing your resume, confidence scores, and screening performance to create personalized technical questions...
          </div>
          <div style={{ marginTop: 24 }}>
            <div style={{ width: 200, height: 4, background: "var(--border)", borderRadius: 2, margin: "0 auto", overflow: "hidden" }}>
              <div style={{ width: "60%", height: "100%", background: "linear-gradient(90deg, var(--cyan), var(--violet))", borderRadius: 2, animation: "shimmer 1.5s ease-in-out infinite" }} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ─── ACTIVE / COMPLETED PHASE ─────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: "1fr 280px", gridTemplateRows: "60px 1fr", background: "var(--void)", paddingTop: 60 }}>
      {/* Top bar */}
      <div style={{ gridColumn: "1 / -1", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
        <div className="flex gap-4 items-center">
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 16, color: "var(--white)" }}>
            Deep Interview
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-2)" }}>
            {resumeData?.name || resumeData?.personalInfo?.name || "Candidate"} · {resumeData?.targetRole || resumeData?.target_role || ""}
          </span>
        </div>
        <div className="flex gap-2">
          {depthLevels.map(d => (
            <div key={d} style={{
              padding: "4px 12px", borderRadius: 100, fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 500, letterSpacing: "0.08em",
              color: d === currentDepth ? "var(--violet)" : "var(--text-2)",
              background: d === currentDepth ? "var(--violet-dim)" : "var(--lift)",
              border: `1px solid ${d === currentDepth ? "rgba(123,97,255,0.3)" : "var(--border2)"}`
            }}>{d}</div>
          ))}
        </div>
        <div className="flex gap-4 items-center">
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 700, color: timeLeft < 60 ? "var(--red)" : timeLeft < 180 ? "var(--amber)" : "var(--text-1)" }}>
            {formatTime(timeLeft)}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={handleEndInterview}>Finish Interview →</button>
        </div>
      </div>

      {/* Main content */}
      <div style={{ padding: 40, display: "flex", flexDirection: "column", gap: 24 }}>
        {error && (
          <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--red-dim)", border: "1px solid rgba(255,68,68,0.2)", color: "var(--red)", fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Question card */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 20, padding: 36, position: "relative", overflow: "hidden" }}>
          <div style={{ content: "", position: "absolute", top: 0, left: 0, right: 0, height: 2, background: "linear-gradient(90deg, var(--cyan) 0%, var(--violet) 100%)" }} />
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-2)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>
            Q{qIndex} of {totalQuestions} · {currentQuestion?.type || "DEPTH"}
            {currentQuestion?.is_followup && " · Follow-up"}
          </div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 24, fontWeight: 600, color: "var(--white)", lineHeight: 1.35, letterSpacing: "-0.02em" }}>
            {currentQuestion?.text || "Preparing question..."}
          </div>
          {currentQuestion?.skill && (
            <div style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 20, padding: "6px 12px", background: "var(--violet-dim)", border: "1px solid rgba(123,97,255,0.2)", borderRadius: 6, fontSize: 12, color: "var(--violet)", fontWeight: 500 }}>
              <span>⬡</span> Testing: {currentQuestion.skill}
            </div>
          )}
        </div>

        {/* Waveform + Mic */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20, padding: "20px 0" }}>
          <Waveform active={speaking || recording} />

          {phase !== "completed" && (
            <div className="flex gap-4 items-center">
              <button
                className={`btn ${recording ? "btn-danger" : "btn-ghost"}`}
                style={{ width: 72, height: 72, borderRadius: "50%", fontSize: 28, padding: 0 }}
                onClick={handleMic}
                disabled={speaking}
              >
                {recording ? "⏹" : "🎙"}
              </button>
            </div>
          )}

          {speaking && (
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--cyan)", display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ animation: "blink 1s step-end infinite", display: "inline-block" }}>●</span>
              AI Speaking...
            </div>
          )}

          {recording && (
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--red)", display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ animation: "blink 1s step-end infinite", display: "inline-block" }}>●</span>
              Recording · {formatTime(recordingTime)}
            </div>
          )}

          {phase === "completed" && (
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>✅</div>
              <div style={{ color: "var(--green)", fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Interview Complete!</div>
              <div style={{ color: "var(--text-2)", fontSize: 13 }}>Redirecting to report...</div>
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div>
          <div className="flex justify-between mb-2">
            <span style={{ fontSize: 12, color: "var(--text-2)" }}>Interview Progress</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-2)" }}>
              {qIndex}/{totalQuestions} questions
            </span>
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            {Array.from({ length: totalQuestions || 8 }).map((_, i) => (
              <div key={i} style={{
                flex: 1, height: 4, borderRadius: 2,
                background: i < qIndex ? "var(--cyan)" : i === qIndex ? "var(--border2)" : "var(--border)",
                transition: "background 0.3s"
              }} />
            ))}
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div style={{ background: "var(--surface)", borderLeft: "1px solid var(--border)", padding: "20px 16px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-2)", letterSpacing: "0.15em", textTransform: "uppercase" }}>Skill Confidence</div>
        <div style={{ fontSize: 11, color: "var(--text-2)", marginTop: -8 }}>From resume analysis</div>

        {liveSkills.map(s => (
          <div key={s.name} className="card-lift">
            <div className="flex justify-between items-center mb-2">
              <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-1)" }}>{s.name}</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700, color: s.color }}>{s.pct}%</span>
            </div>
            <div className="skill-bar-track">
              <div className="skill-bar-fill" style={{ width: `${s.pct}%`, background: `linear-gradient(90deg, ${s.color}, var(--cyan))` }} />
            </div>
          </div>
        ))}

        <div style={{ height: 1, background: "var(--border)", margin: "8px 0" }} />

        {/* Live transcript in sidebar */}
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-2)", letterSpacing: "0.15em", textTransform: "uppercase" }}>Live Transcript</div>

        {transcript.length === 0 && (
          <div style={{ fontSize: 13, color: "var(--text-2)", fontStyle: "italic" }}>
            Transcript updates as you speak...
          </div>
        )}

        {transcript.slice(-6).map((item, i) => (
          <div key={i} className="card-lift" style={{
            borderLeft: item.type === "question" || item.type === "greeting" ? "2px solid var(--cyan)" : "2px solid var(--violet)",
          }}>
            <div style={{
              fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-2)",
              letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 4,
            }}>
              {item.type === "response" ? "🎙 You" : "🤖 AI"}
              {item.skill ? ` · ${item.skill}` : ""}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-1)", lineHeight: 1.4 }}>
              {item.text.length > 120 ? item.text.substring(0, 120) + "..." : item.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
