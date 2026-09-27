import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import stats from '../data/stats.json';
import { PageHeader, RecordCard, StatusPanel } from '../components/Shared';
import { evidenceUrl, formatNumber } from '../utils/display';

export default function ClusterOverview() {
  const { id } = useParams();
  const cluster = stats.clusters.find(item => String(item.cluster_id) === id);
  const [result, setResult] = useState({ key: '', records: [], total: 0, error: '' });
  const [retry, setRetry] = useState(0);
  const requestKey = `${id}:${retry}`;
  const loading = result.key !== requestKey;
  const { records, total, error } = result;
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/evidence?cluster_id=${encodeURIComponent(id)}&limit=12`, { signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error(`Cluster request failed (${response.status})`); return response.json(); })
      .then(data => setResult({ key: requestKey, records: data.records || [], total: data.total || 0, error: '' }))
      .catch(err => { if (err.name !== 'AbortError') setResult({ key: requestKey, records: [], total: 0, error: err.message }); });
    return () => controller.abort();
  }, [id, requestKey]);
  if (!cluster) return <div className="page-enter"><StatusPanel tone="error" title="Cluster not found" message="This cluster is not part of the saved snapshot." action={<Link className="text-link" to="/analytics">Back to analytics →</Link>} /></div>;
  return <div className="page-enter"><div className="breadcrumb"><Link to="/analytics">Analytics</Link><span>/</span><span>{cluster.label}</span></div><PageHeader eyebrow={`CLUSTER / ${String(id).padStart(2, '0')}`} title={cluster.label} description={cluster.description} action={<Link className="button button-primary" to={evidenceUrl({ cluster_id: id, scope: 'in_scope' })}>Explore in-scope evidence ↗</Link>} />
    <div className="cluster-summary"><div><span>IN-SCOPE COMPLAINTS</span><strong>{formatNumber(cluster.vague_memory_count)}</strong><small>Saved snapshot · of 690 in-scope complaints</small></div><div><span>EXISTING SEVERITY SCORE</span><strong>{Number(cluster.severity_score).toFixed(2)}</strong><small>Original project score</small></div><div><span>INTERPRETATION</span><strong className="cluster-summary-label">{cluster.cluster_id === 0 ? 'Context only' : cluster.is_emerging ? 'Emerging signal' : 'Tracked pattern'}</strong><small>{cluster.cluster_id === 0 ? 'Data loss and sync grouping' : cluster.is_emerging ? 'Small sample; treat cautiously' : 'See source records below'}</small></div></div>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">EXTRACTED THEMES</span><h2>Failure points</h2><p>Labels from the preserved clustering output.</p></div></div><div className="theme-pills">{(cluster.top_failure_points || []).map(point => <span key={point}>{point}</span>)}</div></section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">DATABASE RECORDS</span><h2>Historical complaints</h2><p>Records currently assigned to this cluster in the read-only database. Counts can differ from the saved snapshot above.</p></div><Link className="text-link" to={evidenceUrl({ cluster_id: id })}>Search within this cluster →</Link></div>{loading && <StatusPanel title="Loading cluster records" message="Reading database evidence…" />}{!loading && error && <StatusPanel tone="error" title="Records unavailable" message={error} action={<button className="text-button" onClick={() => setRetry(value => value + 1)}>Try again →</button>} />}{!loading && !error && records.length === 0 && <StatusPanel title="No records found" message="No database records are assigned to this cluster." />}{!loading && !error && records.length > 0 && <><div className="cluster-record-count">{formatNumber(total)} database records · showing first {records.length}</div><div className="record-list">{records.map(record => <RecordCard key={record.id} record={{ ...record, cluster_name: cluster.label }} />)}</div>{total > records.length && <Link className="button button-outline more-records" to={evidenceUrl({ cluster_id: id })}>Browse all records →</Link>}</>}</section>
  </div>;
}
