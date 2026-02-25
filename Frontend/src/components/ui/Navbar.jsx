import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  const tabs = isAuthenticated
    ? [
      { name: "Home", path: "/" },
      { name: "Upload", path: "/upload" },
      { name: "Voice Screen", path: "/voice-screen" },
      { name: "Interview", path: "/interview" },
      { name: "Report", path: "/report" },
      { name: "Recruiter", path: "/recruiter" },
    ]
    : [
      { name: "Home", path: "/" },
    ];

  return (
    <nav className="nav">
      <div className="nav-logo" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
        <div className="nav-logo-dot" />
        AXON<span style={{ color: "var(--text-2)", fontWeight: 400 }}>hire</span>
      </div>
      <div className="nav-tabs">
        {tabs.map(t => (
          <button
            key={t.name}
            className={`nav-tab ${location.pathname === t.path ? "active" : ""}`}
            onClick={() => navigate(t.path)}
          >
            {t.name}
          </button>
        ))}
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
