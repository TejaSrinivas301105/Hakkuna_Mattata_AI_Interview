import { useState, useRef } from "react";
import SkillBar from "../components/ui/SkillBar";
import { useUploadStatus } from "../context/UploadContext";
import { parseResume, getConfidenceScores } from "../services/api";

export default function UploadPage({ onNavigate }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [fileName, setFileName] = useState("");
  const [file, setFile] = useState(null);
  const [role, setRole] = useState("Senior Frontend Engineer");
  const [parsing, setParsing] = useState(false);
  const [skills, setSkills] = useState([]);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);
  const {
    setIsUploaded,
    setCandidateId,
    setResumeData,
    setConfidenceScores,
  } = useUploadStatus();

  const handleFileSelect = async (selectedFile) => {
    if (!selectedFile) return;
    setFileName(selectedFile.name);
    setFile(selectedFile);
    setError("");
    setParsing(true);

    try {
      // Stage 1: Parse resume
      const parseRes = await parseResume(selectedFile);
      const candidate = parseRes.data;
      setCandidateId(candidate.id);
      setResumeData(candidate.resume_refined);

      // Stage 2: Get confidence scores
      try {
        const scoreRes = await getConfidenceScores(candidate.id);
        const scores = scoreRes.data;
        setConfidenceScores(scores);

        // Convert scores to skill bar format
        const skillBars = Object.entries(scores)
          .map(([name, pct]) => ({ name, pct: Math.round(pct * 100) }))
          .sort((a, b) => b.pct - a.pct)
          .slice(0, 10);
        setSkills(skillBars);
      } catch {
        // Confidence scores optional, continue without
        const resumeSkills = candidate.resume_refined?.skills || [];
        setSkills(resumeSkills.slice(0, 10).map((s) => ({ name: s, pct: 50 })));
      }

      setUploaded(true);
      setIsUploaded(true);
    } catch (err) {
      setError(err.message || "Failed to parse resume. Please try again.");
    } finally {
      setParsing(false);
    }
  };

  return (
    <div className="page">
      <div className="container-narrow">
        <div className="mb-8">
          <div className="section-eyebrow">Stage 01 · Resume Analysis</div>
          <h2 className="section-title">Upload your résumé</h2>
          <p className="section-sub">AI will extract your skill graph and tailor the screening to your background.</p>
        </div>

        <div className="mb-6">
          <label className="label">Target Role</label>
          <select className="input select" value={role} onChange={e => setRole(e.target.value)}>
            <option>Senior Frontend Engineer</option>
            <option>Backend Engineer (Go / Python)</option>
            <option>Full Stack Engineer</option>
            <option>Staff Engineer</option>
            <option>Engineering Manager</option>
            <option>ML Engineer</option>
          </select>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          style={{ display: 'none' }}
          onChange={e => handleFileSelect(e.target.files[0])}
        />

        {error && (
          <div style={{
            padding: "12px 16px", marginBottom: 20, borderRadius: 10,
            background: "var(--red-dim)", border: "1px solid rgba(255,68,68,0.2)",
            color: "var(--red)", fontSize: 13, fontWeight: 500,
          }}>
            {error}
          </div>
        )}

        <div
          className={`upload-zone mb-6 ${dragOver ? "drag-over" : ""}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={e => { e.preventDefault(); setDragOver(false); handleFileSelect(e.dataTransfer.files[0]); }}
          onClick={() => !parsing && fileInputRef.current?.click()}
        >
          {parsing ? (
            <>
              <div style={{ fontSize: 40, marginBottom: 12, animation: "spin 1s linear infinite" }}>⚙️</div>
              <div className="upload-title" style={{ color: "var(--cyan)" }}>Parsing resume with AI...</div>
              <div className="upload-sub">Extracting skills, experience, and projects</div>
            </>
          ) : !uploaded ? (
            <>
              <div className="upload-icon">📄</div>
              <div className="upload-title">Drop your résumé here</div>
              <div className="upload-sub">PDF — up to 10 MB</div>
              <div style={{ marginTop: 20 }}>
                <button className="btn btn-ghost btn-sm" onClick={e => { e.stopPropagation(); fileInputRef.current?.click(); }}>
                  Browse files
                </button>
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: 40, marginBottom: 12 }}>✅</div>
              <div className="upload-title" style={{ color: "var(--green)" }}>{fileName}</div>
              <div className="upload-sub">Parsed successfully</div>
            </>
          )}
        </div>

        {uploaded && skills.length > 0 && (
          <div className="skill-graph-wrap mb-6">
            <div className="flex justify-between items-center mb-4">
              <div>
                <div className="label" style={{ marginBottom: 4 }}>Extracted Skill Graph</div>
                <div style={{ fontSize: 12, color: "var(--text-2)" }}>Confidence based on résumé evidence</div>
              </div>
              <span className="badge badge-active"><span className="badge-dot" />AI Analysis Complete</span>
            </div>
            {skills.map((s, i) => (
              <SkillBar key={s.name} name={s.name} pct={s.pct} delay={i * 100} />
            ))}
          </div>
        )}

        <button className="btn btn-primary btn-lg w-full" onClick={() => onNavigate("Voice Screen")}
          style={{ justifyContent: "center", opacity: uploaded ? 1 : 0.4, pointerEvents: uploaded ? "auto" : "none" }}>
          <span>🎙</span> Start Screening Call
        </button>
      </div>
    </div>
  );
}
