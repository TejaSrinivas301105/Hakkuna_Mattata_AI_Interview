export default function StatusBadge({ status }) {
  const map = {
    "Strong Hire": "badge-hire",
    "Consider": "badge-consider",
    "Reject": "badge-reject",
  };
  return <span className={`badge ${map[status]}`}><span className="badge-dot" />{status}</span>;
}
