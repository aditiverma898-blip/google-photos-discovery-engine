import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import stats from '../data/stats.json';
import { PageHeader, SectionHeading, StatusPanel } from '../components/Shared';
import { evidenceUrl, formatNumber, formatPercent } from '../utils/display';

const patterns = stats.clusters
  .filter(cluster => cluster.primary_category === 'vague_memory_retrieval')
  .sort((a, b) => b.vague_memory_count - a.vague_memory_count);
const context = stats.clusters.find(cluster => cluster.cluster_id === 0);
const quoteIds = [147, 474, 126];

function EvidenceExamples({ featured = false }) {
  const [result, setResult] = useState({ records: [], error: '', loaded: false });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all((featured ? [147] : quoteIds).map(id => fetch('/api/evidence/' + id, { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('Evidence request failed (' + response.status + ')');
      return (await response.json()).record;
    })))
      .then(records => setResult({ records, error: '', loaded: true }))
      .catch(error => { if (error.name !== 'AbortError') setResult({ records: [], error: error.message, loaded: true }); });
    return () => controller.abort();
  }, [retry, featured]);

  if (!result.loaded) return <StatusPanel title="Loading source examples" message="Reading cited records from the database…" />;
  if (result.error) return <StatusPanel tone="error" title="Source examples unavailable" message={result.error} action={<button className="text-button" onClick={() => { setResult({ records: [], error: '', loaded: false }); setRetry(value => value + 1); }}>Try again →</button>} />;
  if (featured) return <article className="featured-evidence"><small>One example from the stored evidence</small><blockquote>“{result.records[0].raw_text}”</blockquote><div className="featured-source"><span>{result.records[0].source || 'Source unavailable'}</span><Link to="/evidence/147">Record #147 →</Link></div></article>;
  return <div className="overview-quote-grid">{result.records.map(record => <Link className="overview-quote" to={'/evidence/' + record.id} key={record.id}>
    <span className="overview-quote-source">{record.source || 'Source unavailable'} <span>Record #{record.id} ↗</span></span>
    <blockquote>“{record.raw_text}”</blockquote>
    <span className="overview-quote-cluster">{record.cluster_name}</span>
  </Link>)}</div>;
}

function Finding({ finding, index }) {
  return <details className="overview-finding"><summary><span>{String(index + 1).padStart(2, '0')}</span><strong>{finding.question_text}</strong><span className="finding-chevron" aria-hidden="true">⌄</span></summary><div className="overview-finding-body"><p>{finding.answer_text}</p><div className="citation-row">{(finding.evidence?.verbatim_quotes || []).map((quote, quoteIndex) => {
    const id = quote.match(/\[ID:\s*(\d+)/)?.[1];
    return id ? <Link key={id + '-' + quoteIndex} to={'/evidence/' + id}>Record #{id} ↗</Link> : <span key={quoteIndex}>Saved quote</span>;
  })}{(finding.evidence?.cited_clusters || []).map(id => <Link key={'cluster-' + id} to={evidenceUrl({ cluster_id: id, scope: 'in_scope' })}>Cluster {id} evidence →</Link>)}</div></div></details>;
}

export default function Overview() {
  return <div className="page-enter overview-page">
    <PageHeader eyebrow="GOOGLE PHOTOS / INDEPENDENT CASE STUDY" title="Finding photos from partial memories" description="What public feedback can tell us about the gap between remembering a photo and retrieving it." action={<Link className="button button-primary" to={evidenceUrl({ scope: 'in_scope' })}>Browse evidence <span>→</span></Link>} />

    <section className="study-feature" aria-label="Featured research finding">
      <div><span className="study-feature-label">A starting point for the research</span><h2>Background-object recall is the largest saved pattern.</h2><p><strong>{formatNumber(patterns[0].vague_memory_count)} of {formatNumber(stats.funnel.in_scope)} in-scope complaints ({formatPercent(patterns[0].vague_memory_count, stats.funnel.in_scope)})</strong> belong to this saved grouping. Inspect the source text before translating the grouping into a product requirement.</p><Link className="text-link" to={'/cluster/' + patterns[0].cluster_id}>Understand this pattern →</Link></div>
      <EvidenceExamples featured />
    </section>

    <section className="overview-metrics" aria-label="Saved snapshot metrics">
      <Link className="overview-metric" to="/analytics"><strong>{formatNumber(stats.funnel.total_ingested)}</strong><b>collected items</b><small>Across five labeled sources</small></Link>
      <Link className="overview-metric" to="/analytics"><strong>{formatNumber(stats.funnel.evaluated_relevant)}</strong><b>relevant complaints</b><small>Saved relevance pass</small></Link>
      <Link className="overview-metric" to={evidenceUrl({ scope: 'in_scope' })}><strong>{formatNumber(stats.funnel.in_scope)}</strong><b>in-scope complaints</b><small>Partial-memory retrieval</small></Link>
    </section>

    <div className="overview-provenance"><p>Snapshot note: 12,808 saved items; the database has 12,818 records and a different relevance count.</p><Link to="/methodology">Read the differences →</Link></div>

    <div className="overview-dashboard">
      <section className="overview-panel"><SectionHeading title="Retrieval patterns" description="Share of 690 in-scope complaints in the saved snapshot." action={<Link className="text-link" to="/analytics">Compare all →</Link>} /><div className="overview-bar-list">{patterns.map(cluster => <Link className="overview-bar-row" to={evidenceUrl({ cluster_id: cluster.cluster_id, scope: 'in_scope' })} key={cluster.cluster_id}><span className="overview-bar-label">{cluster.label}{cluster.is_emerging && <em>Small sample</em>}</span><span className="overview-bar-value">{formatNumber(cluster.vague_memory_count)} <small>{(cluster.vague_memory_count / stats.funnel.in_scope * 100).toFixed(1)}%</small></span><span className="overview-bar-track"><span style={{ width: (cluster.vague_memory_count / stats.funnel.in_scope * 100) + '%' }} /></span></Link>)}</div>{context && <Link className="overview-context-row" to={evidenceUrl({ cluster_id: context.cluster_id, scope: 'in_scope' })}><span>The remaining <strong>{formatNumber(context.vague_memory_count)}</strong> complaints sit in the missing-photos context cluster.</span><span>Inspect →</span></Link>}</section>
      <section className="overview-panel"><SectionHeading title="Research questions" description="The five saved answers, with supporting record and cluster links." /><div className="overview-findings">{stats.synthesis.map((finding, index) => <Finding finding={finding} index={index} key={finding.question_id} />)}</div><p className="overview-panel-note"><strong>Keep the source mix in view.</strong> Play Store accounts for {formatPercent(stats.source_counts['Play Store'], stats.funnel.total_ingested)} of labeled items. Counts describe the collected feedback, not population prevalence. <Link className="text-link" to="/methodology">About the sources →</Link></p></section>
    </div>

    <section className="content-section overview-section"><SectionHeading eyebrow="SOURCE EXAMPLES" title="See the complaint behind the count" description="Three illustrative in-scope records from different sources. They are examples, not representative samples." action={<Link className="text-link" to={evidenceUrl({ scope: 'in_scope' })}>Browse all 690 →</Link>} /><EvidenceExamples /></section>

  </div>;
}
