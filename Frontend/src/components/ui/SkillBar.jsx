import { useState, useEffect } from "react";

export default function SkillBar({ name, pct, color = "cyan", delay = 0 }) {
  const [width, setWidth] = useState(0);
  useEffect(() => { 
    const t = setTimeout(() => setWidth(pct), delay + 200); 
    return () => clearTimeout(t); 
  }, [pct, delay]);
  
  return (
    <div className="skill-row">
      <span className="skill-name">{name}</span>
      <div className="skill-bar-track">
        <div className="skill-bar-fill" style={{ 
          width: `${width}%`, 
          background: color === "violet" ? "linear-gradient(90deg, var(--violet), var(--cyan))" : "linear-gradient(90deg, var(--cyan), var(--green))" 
        }} />
      </div>
      <span className="skill-pct">{pct}%</span>
    </div>
  );
}
