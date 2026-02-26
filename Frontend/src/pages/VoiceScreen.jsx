import { useState, useEffect, useRef } from "react";
import Waveform from "../components/ui/Waveform";
import { useUploadStatus } from "../context/UploadContext";
import { startScreening, sendScreeningResponse, getAudioUrl } from "../services/api";

export default function VoiceScreenPage({ onNavigate }) {
  const { candidateId, setInterviewId } = useUploadStatus();

  const [speaking, setSpeaking] = useState(true);
  const [recording, setRecording] = useState(false);
  const [qIndex, setQIndex] = useState(0);
  const [currentQuestion, setCurrentQuestion] = useState("Starting your screening call...");
  const [interviewIdLocal, setInterviewIdLocal] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | active | completed
  const [transcript, setTranscript] = useState([]);
  const [error, setError] = useState("");
  const [recordingTime, setRecordingTime] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(new Audio());
  const timerRef = useRef(null);

  // Start screening on mount
  useEffect(() => {
    if (!candidateId) return;

    async function init() {
      try {
        const res = await startScreening(candidateId);
        const data = res.data;
        setInterviewIdLocal(data.interview_id);
        setInterviewId(data.interview_id);
        setCurrentQuestion(data.greeting_text);
        setQIndex(1);

        // Play greeting audio
        if (data.greeting_audio_id) {
          const audio = audioRef.current;
          audio.src = getAudioUrl(data.greeting_audio_id);
          audio.onended = () => setSpeaking(false);
          audio.play().catch(() => setSpeaking(false));
        } else {
          setTimeout(() => setSpeaking(false), 2000);
        }

        setStatus("active");
      } catch (err) {
        setError(err.message || "Failed to start screening");
        setStatus("active");
        setSpeaking(false);
      }
    }
    init();

    return () => {
      audioRef.current.pause();
      if (timerRef.current) clearInterval(timerRef.current);
    };
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

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  const handleMic = async () => {
    if (!recording) {
      // Start recording
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
          setCurrentQuestion("Processing your response...");

          try {
            const res = await sendScreeningResponse(interviewIdLocal, audioBlob);
            const data = res.data;

            // Update transcript
            setTranscript(prev => [
              ...prev,
              { type: "response", text: data.response_text },
              { type: "question", text: data.next_question_text },
            ]);

            setCurrentQuestion(data.next_question_text);
            setQIndex(data.question_number);

            // Play next question audio
            if (data.next_question_audio_id) {
              const audio = audioRef.current;
              audio.src = getAudioUrl(data.next_question_audio_id);
              audio.onended = () => setSpeaking(false);
              audio.play().catch(() => setSpeaking(false));
            } else {
              setSpeaking(false);
            }

            // Check if interview is done
            if (data.interview_status === "completed") {
              setStatus("completed");
              setTimeout(() => onNavigate("Interview"), 3000);
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
      // Stop recording
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
        setRecording(false);
      }
    }
  };

  const endCall = async () => {
    setStatus("completed");
    // interviewId is already set in context via setInterviewId
    onNavigate("Interview");
  };

  const totalQuestions = 7;

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '1fr 320px', gridTemplateRows: '60px 1fr', background: 'var(--void)', paddingTop: 60 }}>
      <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 32px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
        <div className="flex gap-3 items-center">
          <div className="nav-logo-dot" />
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 600, color: "var(--white)" }}>AI Screening Call</span>
          <span className="badge badge-active"><span className="badge-dot" />
            {status === "completed" ? "Completed" : "Live"}
          </span>
        </div>
        <div className="flex gap-3 items-center">
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-2)" }}>
            Q {qIndex}/{totalQuestions}
          </span>
          <button className="btn btn-danger btn-sm" onClick={endCall}>End Call</button>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, gap: 40, position: 'relative' }}>
        {error && (
          <div style={{
            position: "absolute", top: 20, left: 20, right: 20,
            padding: "12px 16px", borderRadius: 10,
            background: "var(--red-dim)", border: "1px solid rgba(255,68,68,0.2)",
            color: "var(--red)", fontSize: 13,
          }}>
            {error}
          </div>
        )}

        <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{
            width: 120, height: 120, borderRadius: '50%',
            background: 'linear-gradient(135deg, #0D0D12, #1A1A26)',
            border: `2px solid ${speaking ? 'var(--cyan)' : 'var(--border2)'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 48,
            position: 'relative', zIndex: 1,
            boxShadow: speaking
              ? '0 0 0 8px rgba(0,229,255,0.1), 0 0 60px rgba(0,229,255,0.25)'
              : '0 0 0 8px rgba(0,229,255,0.05), 0 0 40px rgba(0,229,255,0.15)'
          }}>
            🤖
          </div>
        </div>

        <Waveform active={speaking} />

        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16,
          padding: '24px 28px', maxWidth: 600, textAlign: 'center'
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-2)',
            letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 12
          }}>
            {speaking ? "AI is speaking..." : status === "completed" ? "Interview Complete" : "Question " + qIndex}
          </div>
          <div style={{
            fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 600,
            color: 'var(--white)', lineHeight: 1.4
          }}>
            {currentQuestion}
          </div>
        </div>

        {status !== "completed" && (
          <div className="flex gap-4 items-center">
            <button
              className={`btn ${recording ? 'btn-danger' : 'btn-ghost'}`}
              style={{ width: 72, height: 72, borderRadius: '50%', fontSize: 28, padding: 0 }}
              onClick={handleMic}
              disabled={speaking}
            >
              {recording ? "⏹" : "🎙"}
            </button>
          </div>
        )}

        {recording && (
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--red)", display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ animation: "blink 1s step-end infinite", display: "inline-block" }}>●</span>
            Recording · {formatTime(recordingTime)}
          </div>
        )}

        {status === "completed" && (
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>✅</div>
            <div style={{ color: "var(--green)", fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Screening Complete!</div>
            <div style={{ color: "var(--text-2)", fontSize: 13 }}>Redirecting to detailed interview...</div>
          </div>
        )}
      </div>

      <div style={{ background: 'var(--surface)', borderLeft: '1px solid var(--border)', padding: '24px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-2)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
          Live Transcript
        </div>
        <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: -8 }}>Updates as you speak</div>

        {transcript.length === 0 && (
          <div style={{ fontSize: 13, color: "var(--text-2)", fontStyle: "italic", padding: "20px 0" }}>
            Transcript will appear here as the interview progresses...
          </div>
        )}

        {transcript.map((item, i) => (
          <div key={i} className="card-lift" style={{
            borderLeft: item.type === "question" ? "2px solid var(--cyan)" : "2px solid var(--violet)",
          }}>
            <div style={{
              fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-2)",
              letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6,
            }}>
              {item.type === "question" ? "🤖 AI" : "🎙 You"}
            </div>
            <div style={{ fontSize: 13, color: "var(--text-1)", lineHeight: 1.5 }}>
              {item.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
