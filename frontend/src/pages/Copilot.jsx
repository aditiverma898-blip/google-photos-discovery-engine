import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { PageHeader, RecordCard, StatusPanel } from '../components/Shared';

const sampleQuestions = ['What do people remember about a photo?', 'What happens when people search for a background object?', 'How do users describe relative time searches?'];
const sampleComplaints = [
  'The video where my dog was barking at the TV',
  'Photos from a few days after my birthday',
  'I know she was holding a blue coffee mug',
  "I'm looking for a rainy day at a cafe",
  'A screenshot of a funny meme about cats',
  'My photos disappeared after I backed up',
];

function getClassifierTone(classification) {
  if (classification.synthetic_fallback) return 'warning';
  if (classification.match_status === 'Confident Match') return 'success';
  if (classification.match_status === 'Out of scope: data loss') return 'danger';
  return 'warning';
}

export default function Copilot() {
  const [params, setParams] = useSearchParams();
  const tool = params.get('tool') === 'classifier' ? 'classifier' : 'ask';
  const [question, setQuestion] = useState('');
  const [complaint, setComplaint] = useState('');
  const [answer, setAnswer] = useState(null);
  const [classification, setClassification] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const classifierTone = classification ? getClassifierTone(classification) : 'warning';

  function selectTool(next) { setParams(next === 'classifier' ? { tool: 'classifier' } : {}); setError(''); }
  async function submit(event, example) {
    event?.preventDefault();
    const input = (example ?? (tool === 'ask' ? question : complaint)).trim();
    if (!input) return;
    if (tool === 'ask') { setQuestion(input); setAnswer(null); } else { setComplaint(input); setClassification(null); }
    setLoading(true); setError('');
    try {
      const endpoint = tool === 'ask' ? '/api/copilot' : '/api/test-search';
      const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(tool === 'ask' ? { question: input } : { query: input }) });
      if (!response.ok) throw new Error(`${tool === 'ask' ? 'Copilot' : 'Classifier'} request failed (${response.status}).`);
      const result = await response.json();
      if (tool === 'ask') setAnswer(result); else setClassification(result);
    } catch (err) { setError(err.message || 'The request could not be completed.'); }
    finally { setLoading(false); }
  }

  return <div className="page-enter"><PageHeader eyebrow="RESEARCH / TOOLS" title="Ask the evidence" description="Explore a research question with cited records, or try the existing complaint classifier. These tools support the research; they do not replace source review." />
    <div className="tool-switch" role="group" aria-label="Research tools"><button type="button" aria-pressed={tool === 'ask'} disabled={loading} className={tool === 'ask' ? 'active' : ''} onClick={() => selectTool('ask')}><span aria-hidden="true">?</span><strong>Evidence Q&A</strong><small>Answers grounded in saved synthesis and records</small></button><button type="button" aria-pressed={tool === 'classifier'} disabled={loading} className={tool === 'classifier' ? 'active' : ''} onClick={() => selectTool('classifier')}><span aria-hidden="true">≡</span><strong>Complaint classifier</strong><small>Try the existing cluster matching model</small></button></div>
    <div className="copilot-grid"><section className="copilot-main">{tool === 'ask' ? <><div className="tool-heading"><span className="eyebrow">EVIDENCE Q&A</span><h2>Ask the corpus</h2><p>Responses cite record IDs when support is found. If the available evidence is too weak, Copilot will say so.</p></div><form className="prompt-form" onSubmit={submit}><label htmlFor="copilot-question">Your research question</label><textarea id="copilot-question" rows="4" placeholder="What patterns appear when people search by a partial memory?" value={question} onChange={event => setQuestion(event.target.value)} /><div><small>Draws from the preserved database and saved synthesis.</small><button className="button button-primary" disabled={loading || !question.trim()}>{loading ? 'Searching…' : 'Ask Copilot →'}</button></div></form><ExampleList items={sampleQuestions} onChoose={example => submit(null, example)} />{loading && <StatusPanel title="Searching the evidence" message="Finding records and checking support…" />}{error && <StatusPanel tone="error" title="Could not answer" message={error} action={<button className="text-button" onClick={() => submit(null, question)}>Try again →</button>} />}{answer && <div className="answer-panel"><div className="answer-top"><span className={`answer-status ${answer.status === 'abstained' ? 'abstained' : ''}`}>{answer.status === 'abstained' ? 'Insufficient support' : 'Evidence-backed answer'}</span><span>{answer.mode === 'gemini' ? 'Gemini-written · cited' : answer.mode === 'extractive' ? 'Extractive · cited' : 'No answer generated'}</span></div><p className="answer-text">{answer.answer}</p>{answer.citations?.length > 0 && <div className="answer-citations"><h3>Records cited</h3>{answer.citations.map(citation => <Link to={`/evidence/${citation.id}`} key={citation.id}><span>#{citation.id} · {citation.source || 'Source unavailable'}</span><p>“{citation.excerpt}”</p><small>Open record ↗</small></Link>)}</div>}{answer.limitations?.length > 0 && <div className="answer-limits"><strong>Limits of this answer</strong><ul>{answer.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul></div>}</div>}</> : <><div className="tool-heading"><span className="eyebrow">COMPLAINT CLASSIFIER</span><h2>Test a complaint</h2><p>Submit a search failure in the user’s words. This uses the project’s existing cluster matching algorithm and thresholds.</p></div><form className="prompt-form" onSubmit={submit}><label htmlFor="complaint-input">Complaint text</label><textarea id="complaint-input" rows="4" placeholder="I remember the photo had a blue umbrella, but search cannot find it…" value={complaint} onChange={event => setComplaint(event.target.value)} /><div><small>Classification is a demonstration, not a research count.</small><button className="button button-primary" disabled={loading || !complaint.trim()}>{loading ? 'Classifying…' : 'Classify complaint →'}</button></div></form><ExampleList items={sampleComplaints} onChoose={example => submit(null, example)} />{loading && <StatusPanel title="Matching complaint" message="Comparing it with existing cluster signals…" />}{error && <StatusPanel tone="error" title="Could not classify" message={error} action={<button className="text-button" onClick={() => submit(null, complaint)}>Try again →</button>} />}{classification && <div className="answer-panel"><div className="answer-top"><span className={`answer-status classifier-status classifier-status-${classifierTone}`}>{classification.synthetic_fallback ? 'Illustrative classification' : classification.match_status || 'Classification result'}</span></div>{classification.synthetic_fallback && <p className="classifier-status-detail">Underlying model status: {classification.match_status}</p>}{classification.nearest_cluster ? <><h3>{classification.nearest_cluster.label}</h3><p>{classification.nearest_cluster.description}</p><div className={`classifier-meta classifier-meta-${classifierTone}`}><span>Cluster #{classification.nearest_cluster.cluster_id}</span>{typeof classification.nearest_cluster.distance === 'number' && <span className="classifier-score">Distance {classification.nearest_cluster.distance.toFixed(4)}</span>}{classification.threshold !== undefined && <span className="classifier-score">Threshold {classification.threshold}</span>}</div><Link className="text-link" to={`/cluster/${classification.nearest_cluster.cluster_id}`}>Open cluster →</Link></> : <p>No cluster match was returned.</p>}{(classification.synthetic_fallback || classification.evidence_notice) && <div className="synthetic-banner"><strong>Synthetic demonstration fallback</strong><p>{classification.evidence_notice || 'The classifier used illustrative fallback output. Similar examples below are synthetic and are not retrieved research evidence.'}</p></div>}{classification.similar_records?.length > 0 && <div className="classifier-records"><h3>{classification.synthetic_fallback ? 'Illustrative examples' : 'Nearest historical records'}</h3>{classification.similar_records.map((record, index) => classification.synthetic_fallback ? <div className="synthetic-example" key={`${record.id}-${index}`}><span>SIMULATED EXAMPLE</span><p>“{record.raw_text}”</p></div> : <ClassifierRecord record={record} key={record.id} />)}</div>}</div>}</>}</section><aside className="copilot-aside"><span className="eyebrow">HOW TO READ RESULTS</span><h3>Grounded, with limits.</h3><p>Evidence Q&A links every supporting quote to a database record. The complaint classifier is a separate model demonstration; its fallback may use synthetic examples.</p><div><span>01</span> Open citations to inspect source text.</div><div><span>02</span> Treat small clusters as emerging signals.</div><div><span>03</span> Check the methodology before making decisions.</div><Link to="/methodology">Read methodology →</Link></aside></div>
  </div>;
}

function ExampleList({ items, onChoose }) { return <div className="example-list"><span>TRY AN EXAMPLE</span><div>{items.map(item => <button type="button" key={item} onClick={() => onChoose(item)}>{item} ↗</button>)}</div></div>; }

function ClassifierRecord({ record }) {
  return <div className="classifier-record-entry">
    <span className={`classifier-record-confidence ${record.is_confident ? 'is-confident' : 'is-low-confidence'}`}>
      {record.is_confident ? '✓ High-confidence record' : '⚠ Low-confidence reference'}
      {typeof record.distance === 'number' && ` · Distance ${record.distance.toFixed(4)}`}
    </span>
    <RecordCard record={record} compact />
  </div>;
}
