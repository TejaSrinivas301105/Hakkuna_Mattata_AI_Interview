import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useUploadStatus } from "../../context/UploadContext";

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const { isUploaded, interviewId, candidateId } = useUploadStatus();

  // Step-by-step flow: only show steps, no free navigation
  const currentPath = location.pathname;

  // Determine which step we're on
  const steps = [
    { name: "Upload", path: "/upload", icon: "📄", done: isUploaded },
    { name: "Screening", path: "/voice-screen", icon: "🎙", done: !!interviewId },
    { name: "Interview", path: "/interview", icon: "💡", done: false },
    { name: "Report", path: "/report", icon: "📊", done: false },
  ];

  const currentStepIdx = steps.findIndex(s => s.path === currentPath);

  return (
    <nav className="nav">
      <div className="nav-logo" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
        <div className="nav-logo-dot" />
        AXON<span style={{ color: "var(--text-2)", fontWeight: 400 }}>hire</span>
      </div>

      <div className="nav-tabs">
        {isAuthenticated && (
          <>
            {/* Home is always clickable */}
            <button
              className={`nav-tab ${currentPath === "/" ? "active" : ""}`}
              onClick={() => navigate("/")}
            >
              Home
            </button>

            {/* Step indicators — not clickable, just shows progress */}
            {steps.map((s, idx) => {
              const isCurrent = currentPath === s.path;
              const isPast = idx < currentStepIdx;
              const isAccessible = false; // never clickable — steps are auto-navigated

              return (
                <div
                  key={s.name}
                  style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "6px 12px", borderRadius: 6,
                    fontSize: 13, fontWeight: 500,
                    color: isCurrent ? "var(--white)" : isPast ? "var(--green)" : "var(--text-2)",
                    background: isCurrent ? "var(--violet-dim)" : "transparent",
                    border: isCurrent ? "1px solid rgba(123,97,255,0.3)" : "1px solid transparent",
                    opacity: isPast || isCurrent ? 1 : 0.5,
                    cursor: "default",
                  }}
                >
                  <span style={{ fontSize: 12 }}>
                    {isPast ? "✓" : s.icon}
                  </span>
                  {s.name}
                </div>
              );
            })}

            {/* History is always clickable for authenticated users */}
            <button
              className={`nav-tab ${currentPath === "/history" ? "active" : ""}`}
              onClick={() => navigate("/history")}
            >
              📋 History
            </button>
          </>
        )}

        {!isAuthenticated && (
          <button
            className={`nav-tab ${currentPath === "/" ? "active" : ""}`}
            onClick={() => navigate("/")}
          >
            Home
          </button>
        )}
      </div>

      <div className="flex gap-2 items-center">
        {isAuthenticated ? (
          <>
            <span style={{ fontSize: 13, color: "var(--text-2)", fontWeight: 500 }}>
              {user?.name}
            </span>
            <button className="btn btn-ghost btn-sm" onClick={() => { logout(); navigate("/"); }}>
              Sign Out
            </button>
          </>
        ) : (
          <>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate("/signin")}>
              Sign In
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => navigate("/signup")}>
              Sign Up
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
