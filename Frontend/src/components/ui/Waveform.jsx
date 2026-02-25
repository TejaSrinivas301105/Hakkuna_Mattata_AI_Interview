export default function Waveform({ active }) {
  return (
    <div className="waveform" style={{ display: 'flex', alignItems: 'center', gap: '3px', height: '40px' }}>
      {Array.from({ length: 12 }).map((_, i) => (
        <div key={i} className={`wave-bar ${active ? "active" : ""}`}
          style={{ 
            width: '3px',
            background: 'var(--cyan)',
            borderRadius: '2px',
            opacity: active ? 1 : 0.7,
            height: active ? undefined : "4px",
            animation: active ? `wave-dance 0.8s ease-in-out infinite` : 'none',
            animationDelay: active ? `${i * 0.1}s` : '0s'
          }} 
        />
      ))}
      <style>{`
        @keyframes wave-dance {
          0%, 100% { height: 4px; }
          50% { height: ${[16,30,24,38,28,34,20,40,26,18,32,22][0]}px; }
        }
      `}</style>
    </div>
  );
}
