import { useState, useEffect, useRef } from "react";
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import StatusBadge from "../components/ui/StatusBadge";
import ProgressRing from "../components/ui/ProgressRing";
import { useUploadStatus } from "../context/UploadContext";
import { generateReport, getReport } from "../services/api";

export default function ReportPage() {
  const { candidateId, resumeData, confidenceScores } = useUploadStatus();

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const generatingRef = useRef(false); // Prevent double-call from React StrictMode

  // Fetch or generate report on mount
  useEffect(() => {
    if (!candidateId) return;

    async function loadReport() {
      try {
        // Try to fetch existing report first
        const res = await getReport(candidateId);
        setReport(res.data.report);
        setLoading(false);
      } catch {
        // No report exists, generate one — but only once
        if (generatingRef.current) return;
        generatingRef.current = true;
        try {
          setGenerating(true);
          const res = await generateReport(candidateId);
          setReport(res.data.report);
          setLoading(false);
          setGenerating(false);
        } catch (err) {
          setError(err.message || "Failed to generate report");
          setLoading(false);
          setGenerating(false);
          generatingRef.current = false;
        }
      }
    }
    loadReport();
  }, [candidateId]);

  // ─── LOADING STATE ────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--void)", paddingTop: 60 }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 48, marginBottom: 20, animation: "pulse 1.5s ease-in-out infinite" }}>
            {generating ? "📊" : "🔍"}
          </div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, color: "var(--white)", marginBottom: 12 }}>
            {generating ? "Generating Evaluation Report" : "Loading Report"}
          </div>
          <div style={{ fontSize: 14, color: "var(--text-2)", maxWidth: 400, lineHeight: 1.6 }}>
            {generating
              ? "Our AI is analyzing your resume, confidence scores, screening and interview data to create a comprehensive evaluation..."
              : "Fetching your evaluation report..."}
          </div>
          <div style={{ marginTop: 24 }}>
            <div style={{ width: 200, height: 4, background: "var(--border)", borderRadius: 2, margin: "0 auto", overflow: "hidden" }}>
              <div style={{ width: "70%", height: "100%", background: "linear-gradient(90deg, var(--cyan), var(--violet))", borderRadius: 2, animation: "shimmer 1.5s ease-in-out infinite" }} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ─── ERROR STATE ──────────────────────────────────────────────────
  if (error && !report) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--void)", paddingTop: 60 }}>
        <div style={{ textAlign: "center", maxWidth: 400 }}>
          <div style={{ fontSize: 48, marginBottom: 20 }}>❌</div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, color: "var(--white)", marginBottom: 12 }}>
            Report Generation Failed
          </div>
          <div style={{ fontSize: 14, color: "var(--text-2)", lineHeight: 1.6, marginBottom: 24 }}>{error}</div>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>Try Again</button>
        </div>
      </div>
    );
  }

  // ─── EXTRACT REPORT DATA ─────────────────────────────────────────
  const summary = report?.candidate_summary || {};
  const skillAssessment = report?.skill_assessment || {};
  const interviewAnalysis = report?.interview_analysis || {};
  const detailedEval = report?.detailed_evaluation || {};
  const nextSteps = report?.next_steps || {};

  const candidateName = summary.name || resumeData?.name || resumeData?.personalInfo?.name || "Candidate";
  const initials = candidateName.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
  const role = summary.role || resumeData?.targetRole || resumeData?.target_role || "";
  const overallScore = Math.round((summary.overall_score || 0) * 10); // normalize to 0-100
  const recommendation = summary.overall_recommendation || "MAYBE";

  // Build radar data from skill assessment
  const radarData = Object.entries(skillAssessment).slice(0, 8).map(([skill, data]) => ({
    skill: skill.length > 12 ? skill.substring(0, 12) + "…" : skill,
    A: Math.round((data.final_rating || 5) * 10),
  }));

  // Build skill detail cards
  const skillDetails = Object.entries(skillAssessment).map(([name, data]) => {
    const score = Math.round((data.final_rating || 5) * 10);
    const level = score >= 70 ? "high" : score >= 50 ? "mid" : "low";
    return {
      name,
      score,
      performance: data.interview_performance || "NOT_ASSESSED",
      evidence: data.evidence || "",
      gaps: data.gaps || "",
      level,
      initialConfidence: Math.round((data.initial_confidence || 0) * 100),
    };
  });

  // Evaluation scores
  const evalScores = [
    { label: "Technical Depth", ...detailedEval.technical_depth },
    { label: "Communication", ...detailedEval.communication },
    { label: "Problem Solving", ...detailedEval.problem_solving },
    { label: "Honesty", ...detailedEval.honesty },
    { label: "Cultural Fit", ...detailedEval.cultural_fit },
  ].filter(e => e.score !== undefined);

  const commScore = Math.round((detailedEval.communication?.score || 5) * 10);

  // Map recommendation to badge text
  const badgeMap = {
    "STRONG_HIRE": "Strong Hire",
    "HIRE": "Hire",
    "MAYBE": "Maybe",
    "NO_HIRE": "No Hire",
  };

  return (
    <div style={{ minHeight: "100vh", padding: "80px 0 80px", background: "var(--void)" }}>
      {/* Header */}
      <div style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", padding: "40px 0", marginBottom: 40 }}>
        <div className="container">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-5">
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "linear-gradient(135deg, var(--violet), var(--cyan))", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, color: "var(--void)", flexShrink: 0 }}>{initials}</div>
              <div>
                <div style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: "var(--white)", letterSpacing: "-0.03em" }}>{candidateName}</div>
                <div style={{ fontSize: 14, color: "var(--text-2)", marginTop: 2 }}>{role}</div>
                <div className="flex gap-2 mt-2">
                  <StatusBadge status={badgeMap[recommendation] || recommendation} />
                  <span className="badge badge-active"><span className="badge-dot" />Report Ready</span>
                </div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 24 }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ position: "relative", width: 80, height: 80 }}>
                  <ProgressRing size={80} stroke={6} pct={overallScore} color="var(--cyan)" />
                  <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700, color: "var(--white)" }}>{overallScore}</div>
                  </div>
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-2)", marginTop: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>Overall Score</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ position: "relative", width: 80, height: 80 }}>
                  <ProgressRing size={80} stroke={6} pct={commScore} color="var(--green)" />
                  <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700, color: "var(--green)" }}>{commScore}</div>
                  </div>
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-2)", marginTop: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>Communication</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container">
        {/* Charts row */}
        {radarData.length > 0 && (
          <div className="grid-2 mb-6">
            <div className="card">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <div className="section-eyebrow" style={{ marginBottom: 4 }}>Skill Radar</div>
                  <div style={{ fontFamily: "var(--font-display)", fontSize: 18, fontWeight: 600, color: "var(--white)" }}>Competency Map</div>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="skill" tick={{ fill: "var(--text-2)", fontSize: 12, fontFamily: "var(--font-mono)" }} />
                  <Radar name="Score" dataKey="A" stroke="var(--cyan)" fill="var(--cyan)" fillOpacity={0.1} strokeWidth={2} dot={{ r: 3, fill: "var(--cyan)" }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="section-eyebrow mb-4" style={{ marginBottom: 4 }}>Per-Skill Breakdown</div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: 18, fontWeight: 600, color: "var(--white)", marginBottom: 20 }}>Evaluated Scores</div>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={radarData} layout="vertical" margin={{ left: 8 }}>
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: "var(--text-2)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis dataKey="skill" type="category" tick={{ fill: "var(--text-2)", fontSize: 12, fontFamily: "var(--font-mono)" }} axisLine={false} tickLine={false} width={85} />
                  <Tooltip
                    cursor={{ fill: "rgba(255,255,255,0.03)" }}
                    contentStyle={{ background: "var(--lift)", border: "1px solid var(--border2)", borderRadius: 8, fontSize: 12 }}
                  />
                  <Bar dataKey="A" radius={[0, 4, 4, 0]} maxBarSize={14}>
                    {radarData.map((entry, i) => (
                      <Cell key={i} fill={entry.A >= 70 ? "var(--green)" : entry.A >= 55 ? "var(--cyan)" : "var(--amber)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Skill evaluation cards */}
        {skillDetails.length > 0 && (
          <>
            <div className="section-eyebrow mb-3">Skill Evaluation Cards</div>
            <div className="grid-3 mb-6">
              {skillDetails.map(s => (
                <div key={s.name} style={{ padding: 20, background: "var(--lift)", border: "1px solid var(--border2)", borderRadius: 12 }}>
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div style={{ fontWeight: 600, color: "var(--text-1)", fontSize: 14 }}>{s.name}</div>
                      <div style={{ fontSize: 11, color: "var(--text-2)", marginTop: 3 }}>
                        {s.performance} · Initial: {s.initialConfidence}%
                      </div>
                    </div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 700, color: s.level === "high" ? "var(--green)" : s.level === "mid" ? "var(--cyan)" : "var(--amber)" }}>
                      {s.score}
                    </div>
                  </div>
                  <div style={{ height: 6, background: "var(--border2)", borderRadius: 3, overflow: "hidden", marginBottom: 8 }}>
                    <div style={{
                      height: "100%", borderRadius: 3, width: `${s.score}%`,
                      background: s.level === "high" ? "linear-gradient(90deg, var(--green), #33FF9F)" : s.level === "mid" ? "linear-gradient(90deg, var(--cyan), #33ECFF)" : "linear-gradient(90deg, var(--amber), #FFCB7D)",
                      transition: "width 1.5s cubic-bezier(0.4, 0, 0.2, 1)"
                    }} />
                  </div>
                  {s.evidence && (
                    <div style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.5, marginBottom: 4 }}>
                      ✓ {s.evidence.length > 100 ? s.evidence.substring(0, 100) + "..." : s.evidence}
                    </div>
                  )}
                  {s.gaps && (
                    <div style={{ fontSize: 12, color: "var(--amber)", lineHeight: 1.5 }}>
                      ⚠ {s.gaps.length > 80 ? s.gaps.substring(0, 80) + "..." : s.gaps}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        {/* Detailed evaluation scores */}
        {evalScores.length > 0 && (
          <>
            <div className="section-eyebrow mb-3">Detailed Evaluation</div>
            <div className="grid-3 mb-6">
              {evalScores.map(e => {
                const pct = Math.round((e.score || 0) * 10);
                const color = pct >= 70 ? "var(--green)" : pct >= 50 ? "var(--cyan)" : "var(--amber)";
                return (
                  <div key={e.label} style={{ padding: 20, background: "var(--lift)", border: "1px solid var(--border2)", borderRadius: 12 }}>
                    <div className="flex justify-between items-center mb-2">
                      <span style={{ fontWeight: 600, color: "var(--text-1)", fontSize: 14 }}>{e.label}</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700, color }}>{pct}</span>
                    </div>
                    <div style={{ height: 4, background: "var(--border2)", borderRadius: 2, overflow: "hidden", marginBottom: 8 }}>
                      <div style={{ height: "100%", borderRadius: 2, width: `${pct}%`, background: color, transition: "width 1.5s" }} />
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.5 }}>{e.comment || ""}</div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* Interview analysis - Red flags & highlights */}
        {(interviewAnalysis.screening || interviewAnalysis.deep_technical) && (
          <>
            <div className="section-eyebrow mb-3">Interview Analysis</div>
            <div className="mb-6">
              {interviewAnalysis.screening?.red_flags?.length > 0 && interviewAnalysis.screening.red_flags.map((flag, i) => (
                <div key={`s-${i}`} style={{ background: "rgba(255,181,71,0.06)", border: "1px solid rgba(255,181,71,0.25)", borderLeft: "3px solid var(--amber)", borderRadius: 10, padding: "16px 20px", marginBottom: 12 }}>
                  <div style={{ fontWeight: 600, color: "var(--amber)", fontSize: 13, marginBottom: 6, display: "flex", alignItems: "center", gap: 8 }}>⚠ Screening Flag</div>
                  <div style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.6 }}>{flag}</div>
                </div>
              ))}
              {interviewAnalysis.deep_technical?.highlights?.length > 0 && interviewAnalysis.deep_technical.highlights.map((highlight, i) => (
                <div key={`d-${i}`} style={{ background: "rgba(0,229,255,0.04)", border: "1px solid rgba(0,229,255,0.15)", borderLeft: "3px solid var(--cyan)", borderRadius: 10, padding: "16px 20px", marginBottom: 12 }}>
                  <div style={{ fontWeight: 600, color: "var(--cyan)", fontSize: 13, marginBottom: 6 }}>ℹ Strong Signal</div>
                  <div style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.6 }}>{highlight}</div>
                </div>
              ))}
              {interviewAnalysis.deep_technical?.red_flags?.length > 0 && interviewAnalysis.deep_technical.red_flags.map((flag, i) => (
                <div key={`df-${i}`} style={{ background: "rgba(255,68,68,0.06)", border: "1px solid rgba(255,68,68,0.15)", borderLeft: "3px solid var(--red)", borderRadius: 10, padding: "16px 20px", marginBottom: 12 }}>
                  <div style={{ fontWeight: 600, color: "var(--red)", fontSize: 13, marginBottom: 6 }}>⛔ Concern</div>
                  <div style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.6 }}>{flag}</div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* AI Recommendation */}
        <div className="card card-glow mb-6">
          <div className="flex justify-between items-start">
            <div>
              <div className="section-eyebrow mb-2">AI Recommendation</div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, color: "var(--white)", marginBottom: 12 }}>
                {badgeMap[recommendation] || recommendation}
              </div>
              <div style={{ fontSize: 14, color: "var(--text-2)", maxWidth: 560, lineHeight: 1.7 }}>
                {summary.summary || "Report analysis complete."}
              </div>
              {summary.key_strengths?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--green)", marginBottom: 6 }}>Key Strengths</div>
                  {summary.key_strengths.map((s, i) => (
                    <div key={i} style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.6 }}>✓ {s}</div>
                  ))}
                </div>
              )}
              {summary.key_concerns?.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--amber)", marginBottom: 6 }}>Key Concerns</div>
                  {summary.key_concerns.map((c, i) => (
                    <div key={i} style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.6 }}>⚠ {c}</div>
                  ))}
                </div>
              )}
            </div>
            <div style={{ flexShrink: 0, textAlign: "center", padding: "0 20px" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 72, fontWeight: 700, color: overallScore >= 70 ? "var(--green)" : overallScore >= 50 ? "var(--cyan)" : "var(--amber)", lineHeight: 1, letterSpacing: "-0.05em" }}>{overallScore}</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-2)", marginTop: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>Final Score</div>
              <div className="mt-2"><StatusBadge status={badgeMap[recommendation] || recommendation} /></div>
            </div>
          </div>
        </div>

        {/* Next steps */}
        {nextSteps.recommendation && (
          <>
            <div className="section-eyebrow mb-3">Next Steps</div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, background: "var(--lift)", border: "1px solid var(--border2)", borderRadius: 10, padding: "16px 20px", marginBottom: 12 }}>
              <span style={{ fontSize: 18 }}>📋</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-1)", marginBottom: 4 }}>
                  {nextSteps.recommendation?.replace(/_/g, " ")}
                </div>
                {nextSteps.focus_areas_for_next_round?.length > 0 && (
                  <div style={{ fontSize: 12, color: "var(--text-2)" }}>
                    Focus areas: {nextSteps.focus_areas_for_next_round.join(", ")}
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
