import { useState, useEffect } from "react";
import { getMyReports } from "../services/api";

export default function History() {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [expandedId, setExpandedId] = useState(null);

    useEffect(() => {
        (async () => {
            try {
                setLoading(true);
                const res = await getMyReports();
                setReports(res.data?.reports || []);
            } catch (err) {
                setError(err.message || "Failed to load reports");
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    if (loading) {
        return (
            <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--void)" }}>
                <div style={{ textAlign: "center" }}>
                    <div className="spinner" style={{ width: 40, height: 40, border: "3px solid var(--border)", borderTopColor: "var(--violet)", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto 16px" }} />
                    <div style={{ fontSize: 14, color: "var(--text-2)" }}>Loading your reports...</div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--void)" }}>
                <div style={{ padding: "16px 24px", borderRadius: 12, background: "var(--red-dim)", border: "1px solid rgba(255,68,68,0.2)", color: "var(--red)", fontSize: 14 }}>
                    {error}
                </div>
            </div>
        );
    }



    const cfg = { icon: "📊", label: "Evaluation Report", color: "var(--green)", bg: "var(--green-dim)", border: "rgba(0,255,136,0.2)" };

    const statusColors = {
        completed: { bg: "var(--green-dim)", color: "var(--green)", text: "Completed" },
    };

    const formatDate = (iso) => {
        if (!iso) return "—";
        const d = new Date(iso);
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
    };

    return (
        <div style={{ minHeight: "100vh", padding: "80px 0 40px", background: "var(--void)" }}>
            <div className="container" style={{ maxWidth: 900 }}>
                {/* Header */}
                <div style={{ marginBottom: 32 }}>
                    <div style={{ fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 700, color: "var(--white)", marginBottom: 8 }}>
                        📊 Interview Reports
                    </div>
                    <div style={{ fontSize: 14, color: "var(--text-2)" }}>
                        {reports.length} report{reports.length !== 1 ? "s" : ""} generated
                    </div>
                </div>

                {/* Empty State */}
                {reports.length === 0 && (
                    <div style={{
                        textAlign: "center", padding: "60px 20px", borderRadius: 16,
                        background: "var(--surface)", border: "1px solid var(--border)",
                    }}>
                        <div style={{ fontSize: 48, marginBottom: 16 }}>📭</div>
                        <div style={{ fontSize: 16, color: "var(--text-2)" }}>No reports generated yet</div>
                    </div>
                )}

                {/* Report Cards */}
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {reports.map((item) => {
                        const isExpanded = expandedId === item.id;
                        const summary = item.report?.candidate_summary || {};

                        return (
                            <div key={item.id} style={{
                                background: "var(--surface)", border: `1px solid ${isExpanded ? cfg.border : "var(--border)"}`,
                                borderRadius: 14, overflow: "hidden", transition: "all 0.3s ease",
                                boxShadow: isExpanded ? `0 4px 24px ${cfg.border}` : "none",
                            }}>
                                {/* Card Header */}
                                <div
                                    onClick={() => setExpandedId(isExpanded ? null : item.id)}
                                    style={{
                                        display: "flex", alignItems: "center", gap: 16, padding: "16px 20px",
                                        cursor: "pointer", transition: "background 0.2s",
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.background = "var(--lift)"}
                                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                                >
                                    <div style={{
                                        width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                                        background: cfg.bg, border: `1px solid ${cfg.border}`,
                                        display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20,
                                    }}>
                                        {cfg.icon}
                                    </div>

                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                                            <span style={{ fontSize: 15, fontWeight: 600, color: "var(--white)" }}>{cfg.label}</span>
                                            {summary.overall_recommendation && (
                                                <span style={{
                                                    padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 500,
                                                    background: summary.overall_recommendation.includes("HIRE") ? "var(--green-dim)" : "rgba(255,170,0,0.1)",
                                                    color: summary.overall_recommendation.includes("HIRE") ? "var(--green)" : "#ffaa00",
                                                }}>
                                                    {summary.overall_recommendation.replace(/_/g, " ")}
                                                </span>
                                            )}
                                        </div>
                                        <div style={{ fontSize: 12, color: "var(--text-2)" }}>
                                            {formatDate(item.created_at)}
                                            {summary.overall_score && ` · Score: ${summary.overall_score}/10`}
                                        </div>
                                    </div>

                                    {/* Score ring */}
                                    {summary.overall_score && (
                                        <div style={{
                                            width: 48, height: 48, borderRadius: "50%", flexShrink: 0,
                                            background: `conic-gradient(var(--green) ${summary.overall_score * 10}%, var(--lift) 0%)`,
                                            display: "flex", alignItems: "center", justifyContent: "center",
                                        }}>
                                            <div style={{
                                                width: 38, height: 38, borderRadius: "50%", background: "var(--surface)",
                                                display: "flex", alignItems: "center", justifyContent: "center",
                                                fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700, color: "var(--white)",
                                            }}>
                                                {summary.overall_score}
                                            </div>
                                        </div>
                                    )}

                                    <div style={{
                                        fontSize: 16, color: "var(--text-2)", transition: "transform 0.3s",
                                        transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                                    }}>
                                        ▼
                                    </div>
                                </div>

                                {/* Expanded Report Details */}
                                {isExpanded && (
                                    <div style={{
                                        borderTop: `1px solid ${cfg.border}`, padding: "20px",
                                        background: "rgba(0,0,0,0.15)",
                                    }}>
                                        <ReportDetail item={item} />
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}



function ReportDetail({ item }) {
    const report = item.report || {};
    const summary = report.candidate_summary || {};
    const skills = report.skill_assessment || {};
    const evaluation = report.detailed_evaluation || {};
    const nextSteps = report.next_steps || {};

    const recColors = {
        STRONG_HIRE: { bg: "var(--green-dim)", color: "var(--green)" },
        HIRE: { bg: "var(--green-dim)", color: "var(--green)" },
        MAYBE: { bg: "rgba(255,170,0,0.1)", color: "#ffaa00" },
        NO_HIRE: { bg: "var(--red-dim)", color: "var(--red)" },
    };

    const rec = recColors[summary.overall_recommendation] || recColors.MAYBE;

    return (
        <div>
            {/* Summary */}
            <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 20, flexWrap: "wrap" }}>
                <div style={{
                    width: 64, height: 64, borderRadius: "50%",
                    background: `conic-gradient(var(--green) ${(summary.overall_score || 0) * 10}%, var(--lift) 0%)`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                    <div style={{
                        width: 52, height: 52, borderRadius: "50%", background: "var(--surface)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 700, color: "var(--white)",
                    }}>{summary.overall_score || "—"}</div>
                </div>
                <div>
                    <div style={{
                        padding: "4px 12px", borderRadius: 6, fontSize: 13, fontWeight: 600,
                        background: rec.bg, color: rec.color, display: "inline-block", marginBottom: 4,
                    }}>
                        {(summary.overall_recommendation || "N/A").replace(/_/g, " ")}
                    </div>
                    <div style={{ fontSize: 13, color: "var(--text-2)", maxWidth: 500 }}>{summary.summary}</div>
                </div>
            </div>

            {/* Strengths & Concerns */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
                <div style={{ padding: 14, borderRadius: 10, background: "var(--green-dim)", border: "1px solid rgba(0,255,136,0.15)" }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--green)", marginBottom: 8 }}>✓ Strengths</div>
                    {(summary.key_strengths || []).map((s, i) => (
                        <div key={i} style={{ fontSize: 12, color: "var(--text-1)", marginBottom: 4 }}>• {s}</div>
                    ))}
                </div>
                <div style={{ padding: 14, borderRadius: 10, background: "var(--red-dim)", border: "1px solid rgba(255,68,68,0.15)" }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--red)", marginBottom: 8 }}>⚠ Concerns</div>
                    {(summary.key_concerns || []).map((c, i) => (
                        <div key={i} style={{ fontSize: 12, color: "var(--text-1)", marginBottom: 4 }}>• {c}</div>
                    ))}
                </div>
            </div>

            {/* Skill Scores */}
            {Object.keys(skills).length > 0 && (
                <div style={{ marginBottom: 20 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--white)", marginBottom: 10 }}>Skill Assessment</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        {Object.entries(skills).map(([skill, data]) => (
                            <div key={skill} style={{
                                padding: "8px 12px", borderRadius: 8, background: "var(--surface)", border: "1px solid var(--border)",
                                minWidth: 120,
                            }}>
                                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-1)", marginBottom: 4 }}>{skill}</div>
                                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                    <div style={{
                                        flex: 1, height: 4, borderRadius: 2, background: "var(--lift)",
                                    }}>
                                        <div style={{
                                            width: `${((typeof data === "object" ? data.final_rating : data) / 10) * 100}%`,
                                            height: "100%", borderRadius: 2,
                                            background: "linear-gradient(90deg, var(--violet), var(--cyan))",
                                        }} />
                                    </div>
                                    <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-1)", fontFamily: "var(--font-mono)" }}>
                                        {typeof data === "object" ? data.final_rating : data}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Detailed Evaluation */}
            {Object.keys(evaluation).length > 0 && (
                <div style={{ marginBottom: 20 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--white)", marginBottom: 10 }}>Evaluation Scores</div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8 }}>
                        {Object.entries(evaluation).map(([key, val]) => (
                            <div key={key} style={{
                                padding: "10px 14px", borderRadius: 8, background: "var(--surface)", border: "1px solid var(--border)",
                            }}>
                                <div style={{ fontSize: 11, color: "var(--text-2)", marginBottom: 4, textTransform: "capitalize" }}>
                                    {key.replace(/_/g, " ")}
                                </div>
                                <div style={{ fontSize: 18, fontWeight: 700, color: "var(--white)", fontFamily: "var(--font-mono)" }}>
                                    {typeof val === "object" ? val.score : val}<span style={{ fontSize: 12, color: "var(--text-2)" }}>/10</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Next Steps */}
            {nextSteps.recommendation && (
                <div style={{
                    padding: 14, borderRadius: 10, background: "var(--violet-dim)", border: "1px solid rgba(123,97,255,0.15)",
                }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--violet)", marginBottom: 6 }}>
                        Next Step: {nextSteps.recommendation.replace(/_/g, " ")}
                    </div>
                    {(nextSteps.focus_areas_for_next_round || []).map((a, i) => (
                        <div key={i} style={{ fontSize: 12, color: "var(--text-1)", marginBottom: 2 }}>→ {a}</div>
                    ))}
                </div>
            )}
        </div>
    );
}

