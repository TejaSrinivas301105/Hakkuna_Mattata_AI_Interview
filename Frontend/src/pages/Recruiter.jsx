import { useState, useEffect } from "react";
import StatusBadge from "../components/ui/StatusBadge";
import { getCandidates } from "../services/api";

export default function RecruiterDashboard({ onNavigate }) {
  const [activeFilter, setActiveFilter] = useState("All");
  const [activeSideNav, setActiveSideNav] = useState("Candidates");
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCandidates() {
      try {
        const res = await getCandidates();
        const data = res.data || [];

        // Map backend data to UI format
        const mapped = data.map((c) => {
          const scores = c.confidence_scores || {};
          const scoreValues = Object.values(scores);
          const avgScore = scoreValues.length > 0
            ? Math.round(scoreValues.reduce((a, b) => a + b, 0) / scoreValues.length * 100)
            : 0;

          const skillNames = Object.keys(scores).slice(0, 3).join(", ") || "—";
          const level = avgScore >= 70 ? "high" : avgScore >= 50 ? "mid" : "low";
          const status = avgScore >= 70 ? "Strong Hire" : avgScore >= 50 ? "Consider" : "Reject";

          return {
            id: c.id,
            name: c.name || "Unknown",
            role: c.resume_refined?.targetRole || c.resume_refined?.target_role || "—",
            score: avgScore,
            status,
            date: c.created_at ? new Date(c.created_at).toLocaleDateString() : "—",
            skills: skillNames,
            level,
          };
        });

        setCandidates(mapped);
      } catch (err) {
        console.error("Failed to fetch candidates:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchCandidates();
  }, []);

  const roles = ["All", ...new Set(candidates.map(c => c.role).filter(Boolean).filter(r => r !== "—"))];
  const filtered = activeFilter === "All" ? candidates : candidates.filter(c => c.role === activeFilter);

  const totalScreened = candidates.length;
  const strongHires = candidates.filter(c => c.level === "high").length;
  const avgScore = candidates.length > 0
    ? Math.round(candidates.reduce((a, c) => a + c.score, 0) / candidates.length)
    : 0;

  const sideItems = [
    { icon: "👥", label: "Candidates" },
    { icon: "📊", label: "Analytics" },
    { icon: "⚙️", label: "Job Roles" },
    { icon: "🔔", label: "Alerts" },
    { icon: "⚡", label: "Settings" },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '220px 1fr', gridTemplateRows: '60px 1fr', paddingTop: 60 }}>
      <div style={{ background: 'var(--surface)', borderRight: '1px solid var(--border)', padding: '20px 0', display: 'flex', flexDirection: 'column', gridRow: 2 }}>
        <div style={{ padding: '8px 20px 16px', fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-2)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
          Navigation
        </div>
        {sideItems.map(item => (
          <button key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 20px', fontSize: 14, fontWeight: 500, color: activeSideNav === item.label ? 'var(--cyan)' : 'var(--text-2)', cursor: 'pointer', transition: 'all 0.15s', border: 'none', background: activeSideNav === item.label ? 'var(--cyan-dim)' : 'transparent', width: '100%', textAlign: 'left' }}
            onClick={() => setActiveSideNav(item.label)}>
            <span style={{ fontSize: 16, opacity: 0.8 }}>{item.icon}</span>
            {item.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <div style={{ padding: '0 16px' }}>
          <div className="card-lift" style={{ marginTop: 16 }}>
            <div style={{ fontSize: 11, color: 'var(--text-2)', marginBottom: 8 }}>Total Candidates</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 24, fontWeight: 700, color: 'var(--white)' }}>{totalScreened}</div>
            <div style={{ fontSize: 11, color: 'var(--text-2)', marginTop: 4 }}>in database</div>
          </div>
        </div>
      </div>

      <div style={{ background: 'var(--void)', padding: 32, overflowY: 'auto' }}>
        <div className="flex justify-between items-center mb-6">
          <div>
            <div className="section-eyebrow">Recruiter Dashboard</div>
            <h2 className="section-title">Candidate Pipeline</h2>
          </div>
          <div className="flex gap-3">
            <button className="btn btn-primary btn-sm" onClick={() => onNavigate("Upload")}>+ New Candidate</button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
          {[
            { num: String(totalScreened), label: "Total Screened", delta: "from database" },
            { num: String(strongHires), label: "Strong Hire", delta: `${totalScreened > 0 ? Math.round(strongHires / totalScreened * 100) : 0}% rate` },
            { num: `${avgScore}%`, label: "Avg. Score", delta: "across all candidates" },
            { num: `${filtered.length}`, label: "Filtered Results", delta: activeFilter === "All" ? "showing all" : activeFilter },
          ].map(s => (
            <div key={s.label} style={{ padding: 20, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700, color: 'var(--white)', letterSpacing: '-0.04em' }}>{s.num}</div>
              <div style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 4, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{s.label}</div>
              <div style={{ fontSize: 12, color: 'var(--green)', marginTop: 8, display: 'flex', alignItems: 'center', gap: 4 }}>↑ {s.delta}</div>
            </div>
          ))}
        </div>

        {roles.length > 1 && (
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 20, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12, color: 'var(--text-2)', fontWeight: 500 }}>Filter by role:</span>
            {roles.map(r => (
              <div key={r} style={{ padding: '6px 14px', borderRadius: 100, fontSize: 13, fontWeight: 500, color: activeFilter === r ? 'var(--cyan)' : 'var(--text-2)', border: `1px solid ${activeFilter === r ? 'rgba(0,229,255,0.3)' : 'var(--border2)'}`, background: activeFilter === r ? 'var(--cyan-dim)' : 'var(--surface)', cursor: 'pointer', transition: 'all 0.15s' }} onClick={() => setActiveFilter(r)}>
                {r}
              </div>
            ))}
          </div>
        )}

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr 100px', padding: '12px 20px', borderBottom: '1px solid var(--border)', background: 'var(--lift)' }}>
            {["Candidate", "Role", "Score", "Skills Tested", "Status", "Actions"].map(h => (
              <div key={h} style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 500, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-2)' }}>{h}</div>
            ))}
          </div>

          {loading ? (
            <div style={{ padding: 40, textAlign: "center", color: "var(--text-2)" }}>Loading candidates...</div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: "var(--text-2)" }}>
              No candidates yet. Upload a resume to get started!
            </div>
          ) : (
            filtered.map(c => (
              <div key={c.id} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr 100px', padding: '14px 20px', borderBottom: '1px solid var(--border)', transition: 'background 0.12s', cursor: 'pointer', alignItems: 'center' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--lift)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                <div>
                  <div style={{ fontWeight: 500, color: 'var(--text-1)', fontSize: 14 }}>{c.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 2 }}>{c.date}</div>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-2)' }}>{c.role}</div>
                <div>
                  <span style={{ display: 'inline-block', fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, padding: '2px 10px', borderRadius: 6, background: c.level === "high" ? 'var(--green-dim)' : c.level === "mid" ? 'rgba(0,229,255,0.08)' : 'var(--red-dim)', color: c.level === "high" ? 'var(--green)' : c.level === "mid" ? 'var(--cyan)' : 'var(--red)' }}>{c.score}</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-2)' }}>{c.skills}</div>
                <div><StatusBadge status={c.status} /></div>
                <div className="flex gap-2">
                  <button className="btn btn-ghost btn-sm" style={{ padding: '4px 10px', fontSize: 12 }}
                    onClick={e => { e.stopPropagation(); onNavigate("Report"); }}>
                    View →
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
