import { useAuth } from "../context/AuthContext";

export default function LandingPage({ onNavigate }) {
  const { isAuthenticated } = useAuth();

  return (
    <div className="landing">
      <div className="hero-grid-bg" />
      <div className="hero-glow-ring" />
      <div className="hero-glow-ring" />
      <div className="hero-glow-ring" />

      <div style={{ position: "absolute", top: "22%", left: "8%", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "12px 16px", opacity: 0.7 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 700, color: "var(--green)" }}>94%</div>
        <div style={{ fontSize: 11, color: "var(--text-2)", marginTop: 2 }}>Match Accuracy</div>
      </div>

      <div style={{ position: "absolute", top: "30%", right: "7%", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: "12px 16px", opacity: 0.7 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 700, color: "var(--cyan)" }}>3.2×</div>
        <div style={{ fontSize: 11, color: "var(--text-2)", marginTop: 2 }}>Faster Screening</div>
      </div>

      <div style={{ position: "relative", zIndex: 2 }}>
        <div className="hero-badge">
          <div className="hero-badge-dot" />
          Next-gen AI Hiring OS · v2.0
        </div>

        <h1 className="hero-title">
          Hire with<br />
          <span className="hero-title-accent">Precision Intelligence</span>
        </h1>

        <p className="hero-sub">
          Adaptive AI interviews that go beyond résumés — probing depth, catching contradictions, and delivering evidence-based hire signals in minutes.
        </p>

        <div className="hero-cta-group">
          {isAuthenticated ? (
            <>
              <button className="btn btn-primary btn-lg" onClick={() => onNavigate("Upload")}>
                <span>⚡</span> Start AI Screening
              </button>
              <button className="btn btn-ghost btn-lg" onClick={() => onNavigate("Recruiter")}>
                Recruiter Dashboard
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-primary btn-lg" onClick={() => onNavigate("Sign Up")}>
                <span>🚀</span> Get Started
              </button>
              <button className="btn btn-ghost btn-lg" onClick={() => onNavigate("Sign In")}>
                Sign In
              </button>
            </>
          )}
        </div>

        <div className="flex gap-8 items-center justify-center mt-6" style={{ opacity: 0.5 }}>
          {["Resume Parsing", "Voice Screening", "Adaptive Depth", "Bias-Free Eval"].map(f => (
            <div key={f} className="flex gap-2 items-center text-sm text-muted">
              <span style={{ color: "var(--cyan)" }}>✦</span> {f}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
