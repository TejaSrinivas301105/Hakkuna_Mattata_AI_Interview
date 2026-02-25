export default function ProgressRing({ size = 80, stroke = 6, pct, color = "#00E5FF" }) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  
  return (
    <svg width={size} height={size} className="progress-ring-svg" style={{ transform: 'rotate(-90deg)' }}>
      <circle className="progress-ring-track" cx={size/2} cy={size/2} r={r} strokeWidth={stroke} fill="none" stroke="var(--border2)" />
      <circle className="progress-ring-fill" cx={size/2} cy={size/2} r={r} strokeWidth={stroke}
        stroke={color}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        fill="none"
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 1.5s cubic-bezier(0.4,0,0.2,1)" }}
      />
    </svg>
  );
}
