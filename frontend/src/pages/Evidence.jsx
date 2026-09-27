import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import stats from '../data/stats.json';
import { PageHeader, RecordCard, StatusPanel } from '../components/Shared';
import { formatNumber } from '../utils/display';

const PAGE_SIZE = 20;
const strategies = [
  ['keyword_search', 'Keyword search'],
  ['date_filter', 'Date filter'],
  ['people_face_search', 'People / face search'],
  ['album_browsing', 'Album browsing'],
  ['scrolling_timeline', 'Timeline scrolling'],
  ['semantic search', 'Semantic search'],
  ['google_lens', 'Google Lens'],
  ['location_search', 'Location search'],
  ['combined_filters', 'Combined filters'],
  ['__unspecified__', 'Unspecified'],
];
const workaroundGroups = [
  ['no_text', 'No workaround text recorded'],
  ['scroll_mention', 'Scrolling mentioned'],
  ['other_text', 'Other response text'],
];

export default function Evidence() {
  const [params, setParams] = useSearchParams();
  const [draftState, setDraftState] = useState({ search: params.get('search') || '', value: params.get('search') || '' });
  const [result, setResult] = useState({ key: '', data: null, error: '' });
  const [retry, setRetry] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [copyStatus, setCopyStatus] = useState('');
  const search = params.get('search') || '';
  const source = params.get('source') || '';
  const clusterId = params.get('cluster_id') || '';
  const emotion = params.get('emotion') || '';
  const scope = params.get('scope') || '';
  const searchStrategy = params.get('search_strategy') || '';
  const workaroundGroup = params.get('workaround_group') || '';
  const page = Math.max(1, Number(params.get('page')) || 1);
  const requestKey = JSON.stringify([search, source, clusterId, emotion, scope, searchStrategy, workaroundGroup, page, retry]);
  const loading = result.key !== requestKey;
  const data = result.data;
  const error = result.error;
  const draft = draftState.search === search ? draftState.value : search;

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE) });
    if (search) query.set('search', search);
    if (source) query.set('source', source);
    if (clusterId) query.set('cluster_id', clusterId);
    if (emotion) query.set('emotion', emotion);
    if (scope) query.set('scope', scope);
    if (searchStrategy) query.set('search_strategy', searchStrategy);
    if (workaroundGroup) query.set('workaround_group', workaroundGroup);
    fetch('/api/evidence?' + query, { signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error('Evidence request failed (' + response.status + ')'); return response.json(); })
      .then(data => setResult({ key: requestKey, data, error: '' }))
      .catch(err => { if (err.name !== 'AbortError') setResult({ key: requestKey, data: null, error: err.message || 'Could not load evidence.' }); });
    return () => controller.abort();
  }, [search, source, clusterId, emotion, scope, searchStrategy, workaroundGroup, page, requestKey]);

  function updateFilter(key, value) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    next.delete('page');
    setParams(next);
  }
  function submitSearch(event) { event.preventDefault(); updateFilter('search', draft.trim()); }
  async function copyView() {
    try {
      if (!navigator.clipboard) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(window.location.href);
      setCopyStatus('View link copied.');
    } catch {
      setCopyStatus('Could not copy the link. Copy the address from your browser instead.');
    }
  }
  function goToPage(nextPage) {
    const next = new URLSearchParams(params);
    next.set('page', String(nextPage));
    setParams(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  const activeCount = [search, source, clusterId, emotion, scope, searchStrategy, workaroundGroup].filter(Boolean).length;

  return <div className="page-enter">
    <PageHeader eyebrow="RESEARCH / EVIDENCE" title="Explore the feedback" description="Search the source complaints, compare their context, and follow each record back to its research grouping." action={<span className="live-badge">Read-only research snapshot</span>} />
    <div className="evidence-layout">
      <aside className="filter-panel">
        <div className="filter-panel-top"><h2>Filters</h2><span>{activeCount} active</span></div>
        <form onSubmit={submitSearch} className="filter-search"><label htmlFor="evidence-search">Search records</label><div><input id="evidence-search" type="search" placeholder="Keywords, failure points…" value={draft} onChange={event => setDraftState({ search, value: event.target.value })} /><button type="submit" aria-label="Search evidence">⌕</button></div></form>
        <button className="mobile-filter-toggle" aria-expanded={filtersOpen} aria-controls="filter-controls" onClick={() => setFiltersOpen(!filtersOpen)}>{filtersOpen ? 'Hide filters' : `Show filters (${activeCount} active)`}</button>
        <div id="filter-controls" className={`filter-controls ${filtersOpen ? 'filters-open' : ''}`}>
        <div className="filter-field"><label htmlFor="source-filter">Source</label><select id="source-filter" value={source} onChange={event => updateFilter('source', event.target.value)}><option value="">All sources</option>{Object.keys(stats.source_counts).map(name => <option key={name} value={name}>{name}</option>)}<option value="__unattributed__">Unattributed</option></select></div>
        <div className="filter-field"><label htmlFor="cluster-filter">Cluster</label><select id="cluster-filter" value={clusterId} onChange={event => updateFilter('cluster_id', event.target.value)}><option value="">All clusters</option>{stats.clusters.map(cluster => <option value={cluster.cluster_id} key={cluster.cluster_id}>#{cluster.cluster_id} · {cluster.label}</option>)}</select></div>
        <div className="filter-field"><label htmlFor="scope-filter">Research scope</label><select id="scope-filter" value={scope} onChange={event => updateFilter('scope', event.target.value)}><option value="">All records</option><option value="in_scope">In-scope retrieval</option><option value="data_loss">Data loss / sync</option><option value="other_relevant">Other relevant</option><option value="irrelevant">Irrelevant to retrieval</option></select></div>
        <div className="filter-field"><label htmlFor="strategy-filter">Extracted search strategy</label><select id="strategy-filter" value={searchStrategy} onChange={event => updateFilter('search_strategy', event.target.value)}><option value="">All strategies</option>{strategies.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
        <div className="filter-field"><label htmlFor="workaround-filter">Extracted workaround text</label><select id="workaround-filter" value={workaroundGroup} onChange={event => updateFilter('workaround_group', event.target.value)}><option value="">All responses</option>{workaroundGroups.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
        <div className="filter-field"><label htmlFor="emotion-filter">Emotional signal</label><select id="emotion-filter" value={emotion} onChange={event => updateFilter('emotion', event.target.value)}><option value="">All signals</option>{['angry', 'frustrated', 'disappointed', 'neutral', 'sad', 'resigned', 'anxious', 'annoyed'].map(value => <option key={value}>{value}</option>)}</select></div>
        {activeCount > 0 && <button className="clear-filters" type="button" onClick={() => setParams({})}>Clear all filters ↺</button>}
        <div className="filter-hint">Filters live in the URL, so you can copy this view for a teammate. Strategy, workaround, and emotional labels are extracted interpretations of source text.</div>
        </div>
      </aside>
      <section className="evidence-results" aria-live="polite">
        <div className="results-heading"><div><span className="eyebrow">MATCHING RECORDS</span><h2>{loading ? 'Loading…' : error ? 'Results unavailable' : formatNumber(data?.total) + ' results'}</h2>{!loading && data && <p>Showing page {data.page} of {data.pages} · {formatNumber(data.total_corpus)} records in database</p>}</div><button className="copy-link" type="button" onClick={copyView}>Copy view link ↗</button></div>
        {copyStatus && <p className="copy-feedback" role="status">{copyStatus}</p>}
        {loading && <StatusPanel title="Loading evidence" message="Reading the selected database records…" />}
        {!loading && error && <StatusPanel tone="error" title="Evidence unavailable" message={error} action={<button className="text-button" onClick={() => setRetry(value => value + 1)}>Try again →</button>} />}
        {!loading && !error && data?.records?.length === 0 && <StatusPanel title="No matching records" message="Try a broader keyword or clear one of the filters." action={<button className="text-button" onClick={() => setParams({})}>Clear filters →</button>} />}
        {!loading && !error && data?.records?.length > 0 && <><div className="record-list">{data.records.map(record => <RecordCard key={record.id} record={record} />)}</div><div className="pagination"><button type="button" disabled={page <= 1} onClick={() => goToPage(page - 1)}>← Previous</button><span>Page {data.page} / {data.pages}</span><button type="button" disabled={page >= data.pages} onClick={() => goToPage(page + 1)}>Next →</button></div></>}
      </section>
    </div>
    <div className="provenance-note"><span className="note-icon">i</span><p><strong>Evidence database:</strong> {formatNumber(data?.total_corpus || 12818)} records, queried live. Of the preserved database rows, 10 have no source label. A record’s presence here does not mean it passed the retrieval relevance filter.</p><Link to="/methodology">Read methodology →</Link></div>
  </div>;
}
