import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import stats from '../data/stats.json';
import { SectionHeading, StatusPanel } from './Shared';
import { evidenceUrl, formatNumber, formatPercent } from '../utils/display';

const strategyLabels = {
  keyword_search: 'Keyword search',
  date_filter: 'Date filter',
  people_face_search: 'People / face search',
  album_browsing: 'Album browsing',
  scrolling_timeline: 'Timeline scrolling',
  'semantic search': 'Semantic search',
  google_lens: 'Google Lens',
  location_search: 'Location search',
  combined_filters: 'Combined filters',
  __unspecified__: 'Unspecified',
};
const workaroundLabels = {
  no_text: 'No workaround text recorded',
  scroll_mention: 'Scrolling mentioned',
  other_text: 'Other response text',
};
const sourceLabel = source => source === '__unattributed__' ? 'Unattributed' : source;
const breakdownPercent = (count, denominator) => count > 0 && count / denominator < .01 ? '<1%' : formatPercent(count, denominator);
const clusterOrder = [...stats.clusters].sort((a, b) => b.vague_memory_count - a.vague_memory_count);

function BreakdownRows({ rows, denominator, type }) {
  const maximum = Math.max(1, ...rows.map(row => row.count));
  return <div className="breakdown-rows">{rows.map(row => {
    const label = type === 'strategy' ? strategyLabels[row.value] || row.value.replaceAll('_', ' ') : workaroundLabels[row.value];
    const filter = type === 'strategy' ? { search_strategy: row.value } : { workaround_group: row.value };
    return <Link className="breakdown-row" key={row.value} to={evidenceUrl({ scope: 'in_scope', ...filter })}><span>{label}</span><strong>{formatNumber(row.count)} <small>{breakdownPercent(row.count, denominator)} of in scope</small></strong><span className="breakdown-track"><span style={{ width: (row.count / maximum * 100) + '%' }} /></span></Link>;
  })}</div>;
}

export default function BreakdownPanels() {
  const [result, setResult] = useState({ data: null, error: '', loaded: false });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/analytics/breakdowns', { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('Breakdown request failed (' + response.status + ')');
        return response.json();
      })
      .then(data => setResult({ data, error: '', loaded: true }))
      .catch(error => { if (error.name !== 'AbortError') setResult({ data: null, error: error.message, loaded: true }); });
    return () => controller.abort();
  }, [retry]);

  if (!result.loaded) return <StatusPanel title="Loading breakdowns" message="Counting in-scope records in the read-only database…" />;
  if (result.error) return <StatusPanel tone="error" title="Breakdowns unavailable" message={result.error} action={<button className="text-button" onClick={() => { setResult({ data: null, error: '', loaded: false }); setRetry(value => value + 1); }}>Try again →</button>} />;
  const data = result.data;
  if (!data?.denominator) return <StatusPanel title="No in-scope records" message="The database has no records in the selected research scope." />;
  const sourceTotals = {};
  const clusterTotals = {};
  const counts = {};
  data.source_cluster.forEach(row => {
    sourceTotals[row.source] = (sourceTotals[row.source] || 0) + row.count;
    clusterTotals[row.cluster_id] = (clusterTotals[row.cluster_id] || 0) + row.count;
    counts[row.source + ':' + row.cluster_id] = row.count;
  });
  const sources = Object.keys(sourceTotals).sort((a, b) => a === '__unattributed__' ? 1 : b === '__unattributed__' ? -1 : sourceTotals[b] - sourceTotals[a]);

  return <>
    <section className="content-section data-panel breakdown-panel"><SectionHeading eyebrow="03 / INTERSECTIONS" title="Source × cluster" description={'In-scope database records only · ' + formatNumber(data.denominator) + ' total. Select a count to inspect its source records.'} /><div className="matrix-scroll"><table className="matrix-table"><caption className="sr-only">In-scope feedback by source and cluster</caption><thead><tr><th scope="col">Source</th>{clusterOrder.map(cluster => <th scope="col" key={cluster.cluster_id}><span>#{cluster.cluster_id}</span><small>{cluster.label}{cluster.cluster_id === 0 ? ' · context' : ''}</small></th>)}<th scope="col">Total</th></tr></thead><tbody>{sources.map(source => <tr key={source}><th scope="row"><Link to={evidenceUrl({ scope: 'in_scope', source })}>{sourceLabel(source)}</Link></th>{clusterOrder.map(cluster => {
      const count = counts[source + ':' + cluster.cluster_id] || 0;
      return <td key={cluster.cluster_id}>{count ? <Link className="matrix-count" to={evidenceUrl({ scope: 'in_scope', source, cluster_id: cluster.cluster_id })} aria-label={sourceLabel(source) + ', ' + cluster.label + ': ' + count + ' records'}>{formatNumber(count)}</Link> : <span className="matrix-zero">—</span>}</td>;
    })}<td><Link className="matrix-total" to={evidenceUrl({ scope: 'in_scope', source })}>{formatNumber(sourceTotals[source])}</Link></td></tr>)}</tbody><tfoot><tr><th scope="row">All sources</th>{clusterOrder.map(cluster => <td key={cluster.cluster_id}><Link className="matrix-total" to={evidenceUrl({ scope: 'in_scope', cluster_id: cluster.cluster_id })}>{formatNumber(clusterTotals[cluster.cluster_id] || 0)}</Link></td>)}<td><Link className="matrix-total" to={evidenceUrl({ scope: 'in_scope' })}>{formatNumber(data.denominator)}</Link></td></tr></tfoot></table></div><p className="panel-footnote">“Unattributed” means the source label is blank in the database. Cluster #0 is context for missing photos and albums, even though 48 records in it passed the in-scope filter.</p></section>
    <div className="breakdown-grid"><section className="content-section data-panel breakdown-panel"><SectionHeading eyebrow="04 / EXTRACTED FIELD" title="Search strategies described" description={'Stored extraction labels among ' + formatNumber(data.denominator) + ' in-scope records; these are interpretations of complaints.'} /><BreakdownRows rows={data.strategies} denominator={data.denominator} type="strategy" /></section><section className="content-section data-panel breakdown-panel"><SectionHeading eyebrow="05 / EXTRACTED FIELD" title="Workaround text" description={'Text-field grouping among ' + formatNumber(data.denominator) + ' in-scope records; “no text” does not prove no workaround was tried.'} /><BreakdownRows rows={data.workarounds} denominator={data.denominator} type="workaround" /><p className="panel-footnote">Groups use the preserved workaround text: blank or “none”, scrolling mentions, and all other responses. Select a row for the underlying records.</p></section></div>
  </>;
}
