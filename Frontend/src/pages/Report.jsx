import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import StatusBadge from "../components/ui/StatusBadge";
import ProgressRing from "../components/ui/ProgressRing";

const RADAR_DATA = [
  { skill: "React", A: 78 },
  { skill: "TypeScript", A: 62 },
  { skill: "Sys Design", A: 55 },
  { skill: "Testing", A: 70 },
  { skill: "Performance", A: 48 },
  { skill: "Node.js", A: 60 },
];

const SKILL_DETAILS = [
  { name: "React", score: 78, questions: 4, depth: "Advanced", level: "high" },
  { name: "TypeScript", score: 62, questions: 3, depth: "Intermediate", level: "mid" },
  { name: "System Design", score: 55, questions: 2, depth: "Advanced", level: "mid" },
  { name: "Testing", score: 70, questions: 3, depth: "Intermediate", level: "high" },
  { name: "Performance", score: 48, questions: 2, depth: "Basic", level: "low" },
  { name: "Node.js", score: 60, questions: 2, depth: "Basic", level: "mid" },
];

export default function ReportPage() {
  return (
    <div style={{ minHeight: '100vh', padding: '80px 0 80px', background: 'var(--void)' }}>
      <div style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '40px 0', marginBottom: 40 }}>
        <div className="container">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-5">
              <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'linear-gradient(135deg, var(--violet), var(--cyan))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, color: 'var(--void)', flexShrink: 0 }}>AC</div>
              <div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 26, fontWeight: 700, color: 'var(--white)', letterSpacing: '-0.03em' }}>Alex Chen</div>
                <div style={{ fontSize: 14, color: 'var(--text-2)', marginTop: 2 }}>Senior Frontend Engineer · Applied 3 days ago</div>
                <div className="flex gap-2 mt-2">
                  <StatusBadge status="Strong Hire" />
                  <span className="badge badge-active"><span className="badge-dot" />Report Ready</span>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 24 }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ position: 'relative', width: 80, height: 80 }}>
                  <ProgressRing size={80} stroke={6} pct={72} color="var(--cyan)" />
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: 'var(--white)' }}>72</div>
                  </div>
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-2)', marginTop: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Overall Score</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ position: 'relative', width: 80, height: 80 }}>
                  <ProgressRing size={80} stroke={6} pct={85} color="var(--green)" />
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: 'var(--green)' }}>85</div>
                  </div>
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-2)', marginTop: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Communication</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container">
        <div className="grid-2 mb-6">
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <div>
                <div className="section-eyebrow" style={{ marginBottom: 4 }}>Skill Radar</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600, color: 'var(--white)' }}>Competency Map</div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart data={RADAR_DATA}>
                <PolarGrid stroke="var(--border)" />
                <PolarAngleAxis dataKey="skill" tick={{ fill: "var(--text-2)", fontSize: 12, fontFamily: "var(--font-mono)" }} />
                <Radar name="Score" dataKey="A" stroke="var(--cyan)" fill="var(--cyan)" fillOpacity={0.1} strokeWidth={2} dot={{ r: 3, fill: "var(--cyan)" }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <div className="section-eyebrow mb-4" style={{ marginBottom: 4 }}>Per-Skill Breakdown</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600, color: 'var(--white)', marginBottom: 20 }}>Evaluated Scores</div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={RADAR_DATA} layout="vertical" margin={{ left: 8 }}>
                <XAxis type="number" domain={[0, 100]} tick={{ fill: "var(--text-2)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis dataKey="skill" type="category" tick={{ fill: "var(--text-2)", fontSize: 12, fontFamily: "var(--font-mono)" }} axisLine={false} tickLine={false} width={85} />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.03)" }}
                  contentStyle={{ background: "var(--lift)", border: "1px solid var(--border2)", borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="A" radius={[0, 4, 4, 0]} maxBarSize={14}>
                  {RADAR_DATA.map((entry, i) => (
                    <Cell key={i} fill={entry.A >= 70 ? "var(--green)" : entry.A >= 55 ? "var(--cyan)" : "var(--amber)"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="section-eyebrow mb-3">Skill Evaluation Cards</div>
        <div className="grid-3 mb-6">
          {SKILL_DETAILS.map(s => (
            <div key={s.name} style={{ padding: 20, background: 'var(--lift)', border: '1px solid var(--border2)', borderRadius: 12 }}>
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text-1)', fontSize: 14 }}>{s.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-2)', marginTop: 3 }}>
                    {s.questions} questions · {s.depth}
                  </div>
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: s.level === "high" ? "var(--green)" : s.level === "mid" ? "var(--cyan)" : "var(--amber)" }}>
                  {s.score}
                </div>
              </div>
              <div style={{ height: 6, background: 'var(--border2)', borderRadius: 3, overflow: 'hidden', marginBottom: 8 }}>
                <div style={{ height: '100%', borderRadius: 3, width: `${s.score}%`, background: s.level === "high" ? "linear-gradient(90deg, var(--green), #33FF9F)" : s.level === "mid" ? "linear-gradient(90deg, var(--cyan), #33ECFF)" : "linear-gradient(90deg, var(--amber), #FFCB7D)", transition: 'width 1.5s cubic-bezier(0.4, 0, 0.2, 1)' }} />
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-2)' }}>
                Depth reached: {s.depth}
              </div>
            </div>
          ))}
        </div>

        <div className="section-eyebrow mb-3">AI Contradiction Analysis</div>
        <div className="mb-6">
          <div style={{ background: 'rgba(255,181,71,0.06)', border: '1px solid rgba(255,181,71,0.25)', borderLeft: '3px solid var(--amber)', borderRadius: 10, padding: '16px 20px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, color: 'var(--amber)', fontSize: 13, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>⚠ Skill Depth Mismatch</div>
            <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6 }}>
              Candidate claimed "5+ years of Redux" in résumé (Q1 context), but struggled with middleware composition in Q3 — answer depth aligned with 1–2 years experience. Recommend follow-up.
            </div>
          </div>
          <div style={{ background: 'rgba(0,229,255,0.04)', border: '1px solid rgba(0,229,255,0.15)', borderLeft: '3px solid var(--cyan)', borderRadius: 10, padding: '16px 20px' }}>
            <div style={{ fontWeight: 600, color: 'var(--cyan)', fontSize: 13, marginBottom: 6 }}>ℹ Strong Signal Detected</div>
            <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6 }}>
              System design answer for Q4 exceeded Advanced benchmark. Candidate independently introduced CAP theorem and consistency models — rare for frontend roles. Upgrade role consideration recommended.
            </div>
          </div>
        </div>

        <div className="card card-glow mb-6">
          <div className="flex justify-between items-start">
            <div>
              <div className="section-eyebrow mb-2">AI Recommendation</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, color: 'var(--white)', marginBottom: 12 }}>
                Strong Hire — with caveat
              </div>
              <div style={{ fontSize: 14, color: 'var(--text-2)', maxWidth: 560, lineHeight: 1.7 }}>
                Alex demonstrates strong React & testing fundamentals with an unexpected aptitude for system design. The Redux depth discrepancy is worth a 15-minute targeted follow-up. Recommend advancing to technical panel with a focus on state management at scale.
              </div>
            </div>
            <div style={{ flexShrink: 0, textAlign: 'center', padding: '0 20px' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 72, fontWeight: 700, color: 'var(--green)', lineHeight: 1, letterSpacing: '-0.05em' }}>72</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-2)', marginTop: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Final Score</div>
              <div className="mt-2"><StatusBadge status="Strong Hire" /></div>
            </div>
          </div>
        </div>

        <div className="section-eyebrow mb-3">Share Report</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, background: 'var(--lift)', border: '1px solid var(--border2)', borderRadius: 10, padding: '12px 16px' }}>
          <span style={{ fontSize: 18 }}>🔗</span>
          <span style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>https://axonhire.io/report/alex-chen-sf24x·private</span>
          <button className="btn btn-ghost btn-sm">Copy Link</button>
          <button className="btn btn-primary btn-sm">Export PDF</button>
        </div>
      </div>
    </div>
  );
}
