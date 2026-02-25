import { useState, useEffect } from "react";

const INTERVIEW_QUESTIONS = [
  {
    q: "You're building a real-time collaborative editor. How would you architect the state synchronization across clients?",
    skill: "System Design",
    depth: "Advanced",
    number: "Q4",
  },
  {
    q: "Explain the trade-offs between optimistic and pessimistic UI updates in a React application.",
    skill: "React Patterns",
    depth: "Intermediate",
    number: "Q5",
  },
];

const LIVE_SKILLS = [
  { name: "React", pct: 78, color: "var(--cyan)" },
  { name: "TypeScript", pct: 62, color: "var(--violet)" },
  { name: "System Design", pct: 55, color: "var(--amber)" },
  { name: "Testing", pct: 70, color: "var(--green)" },
  { name: "Performance", pct: 48, color: "var(--cyan)" },
];

export default function InterviewPage({ onNavigate }) {
  const [qIndex, setQIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(180);
  const [answer, setAnswer] = useState("");
  const q = INTERVIEW_QUESTIONS[qIndex];

  useEffect(() => {
    const t = setInterval(() => setTimeLeft(s => s > 0 ? s - 1 : 0), 1000);
    return () => clearInterval(t);
  }, []);

  const fmt = s => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  const timerClass = timeLeft < 30 ? "critical" : timeLeft < 60 ? "warning" : "";
  const depthLevels = ["Basic", "Intermediate", "Advanced"];

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '1fr 280px', gridTemplateRows: '60px 1fr', background: 'var(--void)', paddingTop: 60 }}>
      <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
        <div className="flex gap-4 items-center">
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 16, color: "var(--white)" }}>
            Deep Interview
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-2)" }}>
            Alex Chen · Senior Frontend Engineer
          </span>
        </div>
        <div className="flex gap-2">
          {depthLevels.map(d => (
            <div key={d} style={{ padding: '4px 12px', borderRadius: 100, fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 500, letterSpacing: '0.08em', color: d === q.depth ? 'var(--violet)' : 'var(--text-2)', background: d === q.depth ? 'var(--violet-dim)' : 'var(--lift)', border: `1px solid ${d === q.depth ? 'rgba(123,97,255,0.3)' : 'var(--border2)'}` }}>{d}</div>
          ))}
        </div>
        <div className="flex gap-4 items-center">
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: timeLeft < 30 ? 'var(--red)' : timeLeft < 60 ? 'var(--amber)' : 'var(--text-1)' }}>{fmt(timeLeft)}</div>
          <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("Report")}>Finish Interview →</button>
        </div>
      </div>

      <div style={{ padding: 40, display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 20, padding: 36, position: 'relative', overflow: 'hidden' }}>
          <div style={{ content: '', position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg, var(--cyan) 0%, var(--violet) 100%)' }} />
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-2)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 16 }}>{q.number} of 8 · {q.depth} Depth</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 600, color: 'var(--white)', lineHeight: 1.35, letterSpacing: '-0.02em' }}>{q.q}</div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 20, padding: '6px 12px', background: 'var(--violet-dim)', border: '1px solid rgba(123,97,255,0.2)', borderRadius: 6, fontSize: 12, color: 'var(--violet)', fontWeight: 500 }}>
            <span>⬡</span> Testing: {q.skill}
          </div>
        </div>

        <div>
          <div className="label">Your Answer</div>
          <textarea
            className="input"
            value={answer}
            onChange={e => setAnswer(e.target.value)}
            placeholder="Type your answer here, or click the mic to speak..."
            style={{ minHeight: 160, resize: 'vertical', fontFamily: 'var(--font-body)', fontSize: 15, lineHeight: 1.7 }}
          />
        </div>

        <div className="flex justify-between items-center">
          <div className="flex gap-2 items-center">
            <button className="btn btn-ghost btn-sm">🎙 Speak</button>
            <span style={{ fontSize: 12, color: "var(--text-2)" }}>{answer.length} chars</span>
          </div>
          <div className="flex gap-3">
            <button className="btn btn-ghost btn-sm" onClick={() => setQIndex(i => Math.max(0, i - 1))}>← Prev</button>
            <button className="btn btn-primary btn-sm" onClick={() => {
              if (qIndex < INTERVIEW_QUESTIONS.length - 1) {
                setQIndex(i => i + 1);
                setAnswer("");
                setTimeLeft(180);
              } else {
                onNavigate("Report");
              }
            }}>
              {qIndex < INTERVIEW_QUESTIONS.length - 1 ? "Next Question →" : "Submit Interview →"}
            </button>
          </div>
        </div>

        <div>
          <div className="flex justify-between mb-2">
            <span style={{ fontSize: 12, color: "var(--text-2)" }}>Interview Progress</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-2)" }}>
              {qIndex + 1}/8 questions
            </span>
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} style={{
                flex: 1, height: 4, borderRadius: 2,
                background: i < qIndex + 1 ? "var(--cyan)" : i === qIndex + 1 ? "var(--border2)" : "var(--border)",
                transition: "background 0.3s"
              }} />
            ))}
          </div>
        </div>
      </div>

      <div style={{ background: 'var(--surface)', borderLeft: '1px solid var(--border)', padding: '20px 16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-2)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>Skill Confidence</div>
        <div style={{ fontSize: 11, color: "var(--text-2)", marginTop: -8 }}>Updates in real-time</div>

        {LIVE_SKILLS.map(s => (
          <div key={s.name} className="card-lift">
            <div className="flex justify-between items-center mb-2">
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-1)' }}>{s.name}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: s.color }}>{s.pct}%</span>
            </div>
            <div className="skill-bar-track">
              <div className="skill-bar-fill" style={{ width: `${s.pct}%`, background: `linear-gradient(90deg, ${s.color}, var(--cyan))` }} />
            </div>
          </div>
        ))}

        <div style={{ height: 1, background: 'var(--border)', margin: '8px 0' }} />

        <div className="card-lift">
          <div className="label mb-2">Depth Trajectory</div>
          <div style={{ fontSize: 12, color: "var(--text-2)" }}>
            AI has escalated to <span style={{ color: "var(--violet)" }}>Advanced</span> depth based on your previous answers — strong signal detected in system design.
          </div>
        </div>

        <div className="card-lift" style={{ borderLeft: "2px solid var(--amber)" }}>
          <div style={{ fontSize: 11, color: "var(--amber)", fontWeight: 600, marginBottom: 6 }}>⚠ Note</div>
          <div style={{ fontSize: 12, color: "var(--text-2)" }}>
            Contradict detected: earlier claim about Redux experience diverges from Q2 answer.
          </div>
        </div>
      </div>
    </div>
  );
}
