import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { PageHeader, SourcePill, StatusPanel } from '../components/Shared';

const fields = [
  ['Photo type', 'photo_type'], ['Remembered attributes', 'remembered_attributes'], ['Forgotten attributes', 'forgotten_attributes'],
  ['Search strategy', 'search_strategy'], ['Failure point', 'failure_point'], ['Workaround', 'workaround'], ['Emotional signal', 'emotional_signal'],
];
const display = value => { if (!value) return 'Not extracted'; try { const parsed = JSON.parse(value); return Array.isArray(parsed) ? parsed.join(', ') : String(parsed); } catch { return String(value); } };

export default function RecordDetail() {
  const { id } = useParams();
  const [result, setResult] = useState({ key: '', record: null, error: '' });
  const [retry, setRetry] = useState(0);
  const requestKey = `${id}:${retry}`;
  const loading = result.key !== requestKey;
  const { record, error } = result;
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/evidence/${encodeURIComponent(id)}`, { signal: controller.signal }).then(async response => { if (!response.ok) throw new Error(response.status === 404 ? 'This record was not found.' : `Record request failed (${response.status})`); return response.json(); }).then(data => setResult({ key: requestKey, record: data.record || data, error: '' })).catch(err => { if (err.name !== 'AbortError') setResult({ key: requestKey, record: null, error: err.message }); });
    return () => controller.abort();
  }, [id, requestKey]);
  return <div className="page-enter detail-page"><div className="breadcrumb"><Link to="/evidence">Evidence</Link><span>/</span><span>Record #{id}</span></div><PageHeader eyebrow="EVIDENCE / RECORD" title={`Record #${id}`} description="A single feedback item from the read-only research database." action={<Link className="button button-outline" to="/evidence">← Back to evidence</Link>} />
    {loading && <StatusPanel title="Loading record" message="Retrieving source text and extracted fields…" />}
    {!loading && error && <StatusPanel tone="error" title="Record unavailable" message={error} action={<button className="text-button" onClick={() => setRetry(value => value + 1)}>Try again →</button>} />}
    {!loading && !error && record && <><article className="detail-quote-panel"><div><SourcePill source={record.source} /><span>Record #{record.id}</span></div><blockquote>“{record.raw_text}”</blockquote><small>Verbatim feedback from the research database</small></article><Section title="Extracted context"><div className="detail-field-grid">{fields.map(([label, key]) => <div key={key}><span>{label}</span><strong>{display(record[key])}</strong></div>)}</div></Section><Section title="Research grouping"><div className="detail-cluster"><div><span>ASSIGNED CLUSTER</span><h3>{record.cluster_name || `Cluster #${record.cluster_id ?? 'unassigned'}`}</h3></div>{record.cluster_id !== null && record.cluster_id !== undefined && <Link className="text-link" to={`/cluster/${record.cluster_id}`}>Open cluster →</Link>}</div></Section></>}
  </div>;
}
function Section({ title, children }) { return <section className="detail-section"><h2>{title}</h2>{children}</section>; }
