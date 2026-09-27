import { Link } from 'react-router-dom';

export function PageHeader({ eyebrow, title, description, action }) {
  return <header className="page-header"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action && <div className="page-action">{action}</div>}</header>;
}
export function SectionHeading({ eyebrow, title, description, action }) {
  return <div className="section-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2>{description && <p>{description}</p>}</div>{action && <div>{action}</div>}</div>;
}
export function StatusPanel({ title, message, action, tone = 'neutral' }) {
  return <div className={`status-panel tone-${tone}`} role={tone === 'error' ? 'alert' : 'status'}><span className="status-symbol" aria-hidden="true">{tone === 'error' ? '!' : '·'}</span><div><strong>{title}</strong><p>{message}</p>{action}</div></div>;
}
export function SourcePill({ source }) {
  return <span className="source-pill"><span className="source-dot" />{source || 'Source unavailable'}</span>;
}
export function RecordCard({ record, compact = false }) {
  return <article className={`record-item ${compact ? 'compact' : ''}`}><div className="record-item-top"><SourcePill source={record.source} /><Link className="record-id" to={`/evidence/${record.id}`}>Record #{record.id} ↗</Link></div><p className="record-quote">“{record.raw_text || record.excerpt || 'No text available'}”</p><div className="record-item-bottom">{record.cluster_name && <span>{record.cluster_name}</span>}{record.emotional_signal && <span>{record.emotional_signal}</span>}{record.cluster_id !== null && record.cluster_id !== undefined && <Link to={`/cluster/${record.cluster_id}`}>Cluster {record.cluster_id} →</Link>}</div></article>;
}
