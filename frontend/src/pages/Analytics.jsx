import { Link } from 'react-router-dom';
import stats from '../data/stats.json';
import BreakdownPanels from '../components/BreakdownPanels';
import { PageHeader, SectionHeading } from '../components/Shared';
import { evidenceUrl, formatNumber, formatPercent } from '../utils/display';

const funnel = [
  { name: 'Raw items ingested', count: stats.funnel.total_ingested, description: 'Collected across five feedback sources' },
  { name: 'Relevant complaints', count: stats.funnel.evaluated_relevant, description: 'Passed the saved relevance pass' },
  { name: 'In-scope retrieval', count: stats.funnel.in_scope, description: 'Vague memory retrieval failures' },
  { name: 'Out-of-scope context', count: stats.funnel.out_of_scope, description: 'Data loss and sync complaints' },
];
const clusters = [...stats.clusters].sort((a, b) => b.vague_memory_count - a.vague_memory_count);

export default function Analytics() {
  return <div className="page-enter"><PageHeader eyebrow="RESEARCH / PATTERNS" title="Retrieval patterns and source coverage" description="Compare the saved research groupings, inspect the collection, and follow each count to the underlying evidence." action={<Link className="button button-outline" to="/methodology">How this was measured ↗</Link>} />
    <div className="analytics-overview"><div><span>IN-SCOPE SHARE OF RELEVANT COMPLAINTS</span><strong>{formatPercent(stats.funnel.in_scope, stats.funnel.evaluated_relevant)}</strong><small>{formatNumber(stats.funnel.in_scope)} of {formatNumber(stats.funnel.evaluated_relevant)} · saved snapshot</small></div><p>The analysis focuses on complaints about finding existing photos from partial memories. Data loss and sync issues remain visible as context.</p></div>
    <section className="content-section"><SectionHeading eyebrow="01 / COVERAGE" title="From collection to scope" description="Saved pipeline counts. The relevance pass and scope categories describe different steps, so the bars are not a single subtraction chain." /><div className="funnel-grid">{funnel.map((step, index) => <div className="funnel-step" key={step.name}><span className="step-index">0{index + 1}</span><strong>{formatNumber(step.count)}</strong><h3>{step.name}</h3><p>{step.description}</p><div className="meter"><span style={{ width: Math.max(3, step.count / funnel[0].count * 100) + '%' }} /></div><small>{formatPercent(step.count, funnel[0].count)} of ingested snapshot</small></div>)}</div></section>
    <section className="content-section data-panel analytics-cluster-panel"><SectionHeading eyebrow="02 / PATTERNS & PRIORITIZATION" title="Cluster comparison: where to look first" description="Compare saved in-scope volume, severity, and interpretation in one place. Severity is the existing project score; no new scoring is applied." /><div className="rank-table-wrap"><table className="rank-table cluster-comparison-table"><thead><tr><th>Pattern</th><th>In-scope volume</th><th>Severity score</th><th>Evidence</th></tr></thead><tbody>{clusters.map(cluster => <tr key={cluster.cluster_id}><td><Link to={'/cluster/' + cluster.cluster_id}>{cluster.label} ↗</Link><small className={cluster.is_emerging ? 'pattern-status-emerging' : cluster.cluster_id === 0 ? 'pattern-status-context' : 'pattern-status-tracked'}>{cluster.is_emerging ? 'Emerging / small sample' : cluster.cluster_id === 0 ? 'Out-of-scope cluster context' : 'Tracked retrieval pattern'}</small></td><td><div className="comparison-volume"><span><strong>{formatNumber(cluster.vague_memory_count)}</strong> of {formatNumber(stats.funnel.in_scope)}</span><div className="bar-track coral" aria-hidden="true"><span style={{ width: cluster.vague_memory_count / clusters[0].vague_memory_count * 100 + '%' }} /></div></div></td><td>{Number(cluster.severity_score).toFixed(2)}<small>Existing score</small></td><td><Link to={evidenceUrl({ cluster_id: cluster.cluster_id, scope: 'in_scope' })}>Inspect records →</Link></td></tr>)}</tbody></table></div><p className="panel-footnote">Counts are from the saved snapshot and bars are normalized to the largest cluster. Open a pattern for details or inspect the current database records.</p></section>
    <BreakdownPanels />
    <div className="provenance-note"><span className="note-icon">i</span><p><strong>Snapshot and database differ.</strong> The saved pipeline lists 12,808 ingested items; the evidence database contains 12,818 records, including 10 without a source label. Charts identify the artifact and denominator they use.</p><Link to="/methodology">Read the limits →</Link></div>
  </div>;
}
