import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function SignIn({ onNavigate }) {
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await login(email, password);
            onNavigate("Upload");
        } catch (err) {
            setError(err.message || "Invalid email or password");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
            <div style={{ width: "100%", maxWidth: 440, padding: 40 }}>
                <div style={{ textAlign: "center", marginBottom: 40 }}>
                    <div className="hero-badge" style={{ display: "inline-flex", marginBottom: 16 }}>
                        <div className="hero-badge-dot" />
                        Welcome Back
                    </div>
                    <h2 className="section-title" style={{ marginBottom: 8 }}>Sign In</h2>
                    <p className="section-sub">Enter your credentials to access the platform.</p>
                </div>

                <form onSubmit={handleSubmit}>
                    {error && (
                        <div style={{
                            padding: "12px 16px", marginBottom: 20, borderRadius: 10,
                            background: "var(--red-dim)", border: "1px solid rgba(255,68,68,0.2)",
                            color: "var(--red)", fontSize: 13, fontWeight: 500,
                        }}>
                            {error}
                        </div>
                    )}

                    <div className="mb-6">
                        <label className="label">Email</label>
                        <input
                            className="input"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@example.com"
                            required
                        />
                    </div>

                    <div className="mb-6">
                        <label className="label">Password</label>
                        <input
                            className="input"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            required
                        />
                    </div>

                    <button
                        className="btn btn-primary btn-lg w-full"
                        type="submit"
                        disabled={loading}
                        style={{ justifyContent: "center", opacity: loading ? 0.6 : 1 }}
                    >
                        {loading ? "Signing in..." : "⚡ Sign In"}
                    </button>
                </form>

                <div style={{ textAlign: "center", marginTop: 24, fontSize: 14, color: "var(--text-2)" }}>
                    Don't have an account?{" "}
                    <span
                        onClick={() => onNavigate("Sign Up")}
                        style={{ color: "var(--cyan)", cursor: "pointer", fontWeight: 500 }}
                    >
                        Sign Up
                    </span>
                </div>
            </div>
        </div>
    );
}
