import { useCallback, useEffect, useState } from 'react';
import { api, sendJSON } from '../api.ts';
import { cut, text } from '../labels.ts';

// The reviewer's page for teacher examples: each kept answer in full, with Keep and Drop. The decision is written into
// the batch file (reviews/v2_round*/<batch>_kept_for_review.json), and only examples marked Keep can train.

interface Batch { batch: string; examples: number; kept: number; dropped: number; advisory: string[] }
interface Example {
  n: number; case: string; case_date: string; origin: string; question: string; student_turn: number;
  theories: Record<string, string>; sources_read: Record<string, string>; call: { name: string; arguments: Record<string, unknown> };
  justification: Record<string, string>; flags: string[]; keep: boolean | null; review_note?: string | null; reviewed_at?: string;
  skill?: string; student_action?: { name: string; arguments: Record<string, unknown> } | null; why_wrong?: string; quality_notes?: string[];
}
type Args = Record<string, unknown>;

function ExampleCard({ batch, ex, onSaved }: { batch: string; ex: Example; onSaved: (n: number, keep: boolean | null, note: string) => void }) {
  const [note, setNote] = useState(ex.review_note ?? '');
  const [saving, setSaving] = useState(false);
  const a = ex.call.arguments as Args;
  const save = async (keep: boolean | null): Promise<void> => {
    setSaving(true);
    try { await sendJSON(`/api/review/${batch}/${ex.n}`, 'PATCH', { keep, note }); onSaved(ex.n, keep, note); } finally { setSaving(false); }
  };
  return (
    <article className={`review-card ${ex.keep === true ? 'kept' : ex.keep === false ? 'dropped' : ''}`}>
      <header className="row spread">
        <p className="eyebrow">#{ex.n} · {text(ex.case)} · {text(ex.case_date)} · from the {text(ex.origin)}</p>
        <span className={`status-chip ${ex.keep === true ? 'good' : ex.keep === false ? 'bad' : 'quiet'}`}>{ex.keep === true ? 'Keep' : ex.keep === false ? 'Drop' : 'Not reviewed'}</span>
      </header>
      <h2>{text(ex.question)}</h2>
      <ul className="plain">{Object.entries(ex.theories).map(([k, v]) => <li key={k}><b>{k}:</b> {text(v)}</li>)}</ul>
      <p className="small muted"><b>Sources read:</b> {Object.entries(ex.sources_read).map(([s, d]) => `${s} (${d})`).join(', ')}</p>
      {ex.why_wrong !== undefined ? (
        <div className="review-student">
          <p className="small"><b>Student's action ({text(ex.skill)}):</b> {ex.student_action ? `${ex.student_action.name} ${cut(JSON.stringify(ex.student_action.arguments))}` : 'not on record'}</p>
          <p className="small"><b>Why it was wrong:</b> {text(ex.why_wrong)}</p>
          <p className="small"><b>Correction:</b></p>
        </div>
      ) : null}
      {ex.call.name === 'propose_test' ? (
        <div className="review-test">
          <p><b>Test:</b> {text(a.name)}. {cut(a.method)}</p>
          <p><b>Sample:</b> {cut(a.sample)} · <b>Measure:</b> {cut(a.measure)} · <b>Cost:</b> €{text(a.cost_eur)}, {text(a.weeks)} weeks</p>
          <ul className="plain">{Object.entries((a.prediction_by_theory as Record<string, unknown>) ?? {}).map(([k, v]) => <li key={k}><b>Predicts {k}:</b> {cut(v)}</li>)}</ul>
          <p className="rule-text"><b>Decision rule:</b> {cut(a.decision_rule)}</p>
        </div>
      ) : <p><b>{text(ex.call.name)}:</b> {cut(JSON.stringify(a))}</p>}
      <details><summary className="small">Teacher's reasoning</summary>
        <p className="small"><b>Learned:</b> {cut(ex.justification.learned)}</p>
        <p className="small"><b>Uncertain:</b> {cut(ex.justification.uncertain)}</p>
        <p className="small"><b>Why next:</b> {cut(ex.justification.why_next)}</p>
      </details>
      {ex.flags.length ? <p className="small muted"><b>Flags (keyword aids, not judgments):</b> {ex.flags.join('; ')}</p> : null}
      {ex.quality_notes?.length ? <p className="small"><b>Automated quality notes (advisory):</b> {ex.quality_notes.join('; ')}</p> : null}
      <textarea rows={2} value={note} placeholder="Note (optional): why keep or drop" onChange={(e) => setNote(e.target.value)} />
      <div className="row">
        <button type="button" className="button primary" disabled={saving} aria-pressed={ex.keep === true} onClick={() => { void save(true); }}>Keep</button>
        <button type="button" className="button danger" disabled={saving} aria-pressed={ex.keep === false} onClick={() => { void save(false); }}>Drop</button>
        {ex.keep !== null ? <button type="button" className="button ghost" disabled={saving} onClick={() => { void save(null); }}>Undo</button> : null}
        {ex.reviewed_at ? <span className="small muted">Saved {ex.reviewed_at.replace('T', ' ')}</span> : null}
      </div>
    </article>
  );
}

export function ReviewPage({ onError }: { onError: (e: unknown) => void }) {
  const [batches, setBatches] = useState<Batch[] | null>(null);
  const [current, setCurrent] = useState<string | null>(null);
  const [examples, setExamples] = useState<Example[]>([]);
  const [advisory, setAdvisory] = useState<Record<string, string>>({});
  const loadBatches = useCallback(async () => { const d = await api<{ batches: Batch[] }>('/api/review'); setBatches(d.batches); setCurrent((c) => c ?? d.batches[d.batches.length - 1]?.batch ?? null); }, []);
  useEffect(() => { loadBatches().catch(onError); }, [loadBatches, onError]);
  useEffect(() => {
    if (!current) return;
    api<{ examples: Example[]; advisory: Record<string, string> }>(`/api/review/${current}`).then((d) => { setExamples(d.examples); setAdvisory(d.advisory); }).catch(onError);
  }, [current, onError]);
  if (!batches) return <div className="page-pad"><p className="muted">Loading…</p></div>;
  const done = examples.filter((e) => e.keep !== null).length;
  return (
    <div className="page review-page">
      <p className="eyebrow">Review</p>
      <h1>Teacher examples for version 2</h1>
      <p className="lead">Only examples you mark Keep can train. Your decision is saved into the batch file straight away. The advisory reviews are advice; the decision is yours.</p>
      <div className="row">{batches.map((b) => (
        <button key={b.batch} type="button" className="chip-button toggle-chip" aria-pressed={current === b.batch} onClick={() => setCurrent(b.batch)}>
          {b.batch.split('/').pop()?.replace('_kept_for_review', '')} · {b.examples} examples · {b.kept} keep · {b.dropped} drop
        </button>))}
      </div>
      {examples.length ? <p className="small muted">{done} of {examples.length} reviewed in this batch.</p> : <p className="muted">No examples in this batch.</p>}
      {Object.keys(advisory).length ? (
        <details className="advisory"><summary>Advisory reviews ({Object.keys(advisory).join(', ')})</summary>
          {Object.entries(advisory).map(([k, v]) => <div key={k}><h3>{k}</h3><pre>{v}</pre></div>)}
        </details>
      ) : null}
      {examples.map((ex) => <ExampleCard key={`${current}-${ex.n}`} batch={current ?? ''} ex={ex}
        onSaved={(n, keep, note) => { setExamples((all) => all.map((e) => (e.n === n ? { ...e, keep, review_note: note, reviewed_at: new Date().toISOString().slice(0, 19) } : e))); loadBatches().catch(() => {}); }} />)}
    </div>
  );
}
