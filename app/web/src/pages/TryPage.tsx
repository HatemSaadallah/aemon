import { useCallback, useEffect, useRef, useState } from 'react';
import { api, errorText, postJSON } from '../api.ts';
import { Chip } from '../Chip.tsx';
import { Icon } from '../components/Icon.tsx';
import { Pairs } from '../components/Run.tsx';
import { JourneyMap, TheoryBoard } from '../components/Trace.tsx';
import { StepDetail, WorkflowCanvas } from '../components/Workflow.tsx';
import { shortCompany, stopName, text, when } from '../labels.ts';
import type { HistoryEntry, RunRecord, TryRun, TryStatus, Workspace } from '../types.ts';

// Try it as a workflow editor: the company and its saved investigations on the left, the selected investigation drawn
// as a workflow in the middle, and the selected step, the theories and the outcome on the right. Each workspace runs
// only on its own company's dossier, and its history is kept on the server per user.

type Ask = { question: string; caseId: string; asCase: boolean };
interface Opened { id: string; question: string; record: RunRecord | null; status: string; error: string | null; cachedAt: number | null; identity: Record<string, unknown> | null; ask?: Ask }


const configLine = (id: Record<string, unknown>): string => {
  const adapter = Array.isArray(id.adapter) ? `${String(id.adapter[0])} (${String(id.adapter[1]).slice(0, 12)})` : 'no adapter';
  const base = typeof id.base === 'string' ? id.base.split('/').pop() : 'unknown base';
  return `${String(base)}, ${adapter}, ${String(id.prompt)} prompt, llama.cpp ${String(id.build)}, context ${String(id.context)}, code ${String(id.code)}`;
};

function statusOf(e: HistoryEntry): { kind: 'good' | 'bad' | 'warn'; label: string } {
  if (e.status === 'running') return { kind: 'warn', label: 'Running' };
  if (e.status === 'interrupted') return { kind: 'bad', label: 'Interrupted' };
  if (e.status === 'failed') return { kind: 'bad', label: 'Failed' };
  return e.summary?.finished ? { kind: 'good', label: 'Finished' } : { kind: 'bad', label: stopName(e.summary?.stop_reason) };
}

function Outcome({ record }: { record: RunRecord }) {
  if (record.final) {
    const f = record.final;
    const rows: [string, unknown][] = ([['Recommendation', f.recommendation], ['Favoured theory', f.favoured_theory], ['Customer', f.target_customer], ['Next action', f.next_action], ['Uncertainty', f.uncertainty]] as [string, unknown][]).filter(([, v]) => v);
    return (
      <section className="panel-section outcome-panel good">
        <h3><Icon name="spark" size={16} /> Recommendation</h3>
        <Pairs rows={rows} />
        {Array.isArray(f.would_change_if) && f.would_change_if.length ? <><p className="small muted">Would change if</p><ul>{f.would_change_if.map((x, i) => <li key={i}>{text(x)}</li>)}</ul></> : null}
      </section>
    );
  }
  if (!record.stop_reason) return null;
  return (
    <section className="panel-section outcome-panel bad">
      <h3><Icon name="cross" size={16} /> {stopName(record.stop_reason)}</h3>
      <p className="small">It stopped before a recommendation. The canvas shows where.</p>
      {record.position ? <p className="small">Position so far: favours {text(record.position.favoured_theory)}. {text(record.position.recommendation)}</p> : null}
    </section>
  );
}

export function TryPage({ workspace: w, onError }: { workspace: Workspace; onError: (error: unknown) => void }) {
  const [data, setData] = useState<TryStatus | null>(null);
  const ws = w.id;
  const [history, setHistory] = useState<Record<string, HistoryEntry[]>>({});
  const [opened, setOpened] = useState<Opened | null>(null);
  const [step, setStep] = useState<number | null>(null);
  const [input, setInput] = useState('');
  const [starting, setStarting] = useState(false);
  const watching = useRef<string | null>(null);

  useEffect(() => { document.body.classList.add('app-full'); return () => document.body.classList.remove('app-full'); }, []);

  const refresh = useCallback(async () => {
    const d = await api<TryStatus>('/api/try');
    setData(d);
    return d;
  }, []);
  useEffect(() => { refresh().catch(onError); }, [refresh, onError]);

  const loadHistory = useCallback(async (id: string) => {
    const { entries } = await api<{ entries: HistoryEntry[] }>(`/api/workspaces/${id}/history`);
    setHistory((all) => ({ ...all, [id]: [...entries].sort((a, b) => (b.started ?? 0) - (a.started ?? 0)) }));
  }, []);
  useEffect(() => { if (ws) loadHistory(ws).catch(onError); }, [ws, loadHistory, onError]);

  // The opened run, while it runs: poll it until it ends, then refresh the history and the server status.
  const runningId = opened && opened.status === 'running' ? opened.id : null;
  useEffect(() => {
    if (!runningId || !ws) return undefined;
    watching.current = runningId;
    const id = runningId, wsId = ws;
    let timer: number | undefined;
    const tick = async () => {
      try {
        const d = await api<TryRun>(`/api/try/${id}`);
        if (watching.current !== id) return;
        setOpened((o) => (o && o.id === id ? { ...o, record: d.record ?? o.record, status: d.status, error: d.error, cachedAt: d.cached_at ?? null, identity: d.identity ?? null } : o));
        if (d.status === 'running') timer = window.setTimeout(() => { void tick(); }, 2000);
        else { await loadHistory(wsId); await refresh(); }
      } catch (error: unknown) {
        // A run from before a server restart is no longer held in memory: show what the history recorded.
        await loadHistory(wsId).catch(() => {});
        setOpened((o) => (o && o.id === id ? { ...o, status: 'interrupted', error: errorText(error) } : o));
      }
    };
    void tick();
    return () => { watching.current = null; if (timer) window.clearTimeout(timer); };
  }, [runningId, ws, loadHistory, refresh]);

  // While another investigation holds the model server, check again every five seconds.
  const elsewhere = Boolean(data?.busy) && !runningId;
  useEffect(() => {
    if (!elsewhere) return undefined;
    const timer = window.setTimeout(() => { refresh().catch(onError); }, 5000);
    return () => window.clearTimeout(timer);
  }, [elsewhere, refresh, onError, data]);

  const openEntry = async (e: HistoryEntry): Promise<void> => {
    if (!ws) return;
    setStep(null);
    const base: Opened = { id: e.id, question: e.question, record: null, status: e.status, error: e.error, cachedAt: e.cached_at, identity: null };
    setOpened(base);
    if (e.status === 'running') return;  // the watcher above fetches it
    try {
      const { record } = await api<{ record: RunRecord }>(`/api/workspaces/${ws}/history/${e.id}`);
      setOpened((o) => (o && o.id === e.id ? { ...o, record, identity: (record as RunRecord & { generated_by?: Record<string, unknown> }).generated_by ?? null } : o));
    } catch (error: unknown) { onError(error); }
  };

  const start = async (ask: Ask, fresh = false): Promise<void> => {
    const question = text(ask.question).trim();
    if (!question || starting) return;
    setStarting(true);
    setStep(null);
    try {
      const body: { workspace: string; case: string; shown?: string; question?: string; fresh?: boolean } = { workspace: w.id, case: ask.caseId };
      if (ask.asCase) body.shown = question; else body.question = question;
      if (fresh) body.fresh = true;
      const { id, cached_at: cachedAt } = await postJSON<{ id: string; cached_at?: number }>('/api/try', body);
      setOpened({ id, question, record: null, status: 'running', error: null, cachedAt: cachedAt ?? null, identity: null, ask });
      setInput('');
      await loadHistory(w.id);
    } catch (error: unknown) {
      onError(new Error(`I could not start: ${errorText(error)}`));
    } finally { setStarting(false); }
  };

  if (!data) return <div className="card"><p className="muted">Loading…</p></div>;
  const ready = data.model_ready && data.model.available;
  const problem = !data.model_ready ? 'The model server is not running: start ./app/run_model.sh.' : !data.model.available ? `${data.model.label} is not loaded on the model server yet.` : null;
  const blocked = !ready || Boolean(runningId) || elsewhere || starting;
  const entries = history[w.id] ?? [];
  const record = opened?.record ?? null;

  return (
    <div className="studio">
      <aside className="studio-side" aria-label="Company and history">
        <div className="company-card">
          <span className="start-mark" aria-hidden="true">{shortCompany(w.company).charAt(0)}</span>
          <div><p className="company-name">{text(w.company)}</p><p className="small muted">Workspace · its own dossier and history</p></div>
        </div>
        <button type="button" className="new-run" aria-pressed={!opened} onClick={() => { setOpened(null); setStep(null); }}><Icon name="spark" size={14} /> New investigation</button>
        <p className="side-label">History</p>
        <ol className="history" aria-label={`Investigations of ${shortCompany(w.company)}`}>
          {entries.length ? entries.map((e) => {
            const s = statusOf(e);
            return (
              <li key={e.id}>
                <button type="button" className="history-item" aria-pressed={opened?.id === e.id} onClick={() => { void openEntry(e); }}>
                  <span className={`history-dot ${s.kind}`} aria-hidden="true" />
                  <span className="history-text">
                    <span className="history-q">{e.question}</span>
                    <span className="history-meta">{s.label}{e.summary ? ` · ${e.summary.calls} steps` : ''}{e.started ? ` · ${when(e.started)}` : ''}{e.cached_at ? ' · saved' : ''}</span>
                  </span>
                </button>
              </li>
            );
          }) : <li className="small muted history-empty">No investigations yet in this workspace.</li>}
        </ol>
      </aside>

      <section className="studio-main" aria-label="Investigation">
        {opened ? (
          <WorkflowCanvas record={record} question={opened.question} selected={step} onSelect={setStep}
            header={
              <div className="canvas-bar">
                <div className="canvas-title">
                  <span className="canvas-company">{shortCompany(w.company)}</span>
                  {record ? <Chip kind={record.stop_reason ? (record.final ? 'good' : 'bad') : 'warn'}>{record.stop_reason ? stopName(record.stop_reason) : 'Running'}</Chip> : <Chip kind="warn">Starting</Chip>}
                  {record ? <span className="small muted">{(record.calls || []).length} steps, {(record.calls || []).filter((c) => !c.accepted).length} refused</span> : null}
                  {opened.cachedAt ? <Chip kind="warn">Saved result · {when(opened.cachedAt)}</Chip> : null}
                </div>
                {record ? <JourneyMap record={record} onPick={(stage) => { const i = (record.calls || []).findIndex((c) => c.stage === stage); if (i >= 0) setStep(i + 1); }} /> : null}
                {opened.cachedAt ? (
                  <p className="small muted">A saved investigation for this configuration: the same case and evidence, model, adapter file, model server build and code. A live run can differ, because a retry after a refused step samples at temperature 0.4.{opened.identity ? ` Recorded configuration: ${configLine(opened.identity)}.` : ''}{' '}
                    {opened.ask ? <button type="button" className="link" disabled={blocked} onClick={() => { if (opened.ask) void start(opened.ask, true); }}>Run it again live</button> : null}
                  </p>
                ) : null}
                {opened.error ? <p className="small bad-text">{text(opened.error)}</p> : null}
              </div>
            } />
        ) : (
          <div className="wf-canvas">
            <div className="start">
              <div className="start-head">
                <span className="start-mark" aria-hidden="true">{shortCompany(w.company).charAt(0)}</span>
                <div><h2>{text(w.company)}</h2><p className="lead">{text(w.description)}</p></div>
              </div>
              <p className="small muted">The agent frames the problem, builds rival theories, weighs quoted evidence from this company’s own dossier, challenges its favourite, designs a test or says why one is not worth it, and recommends. Each run takes one to three minutes and starts from scratch.</p>
              <div className="composer">
                <textarea rows={3} maxLength={400} aria-label="Your question" placeholder={`What should ${shortCompany(w.company)} find out?`} value={input} disabled={blocked}
                  onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); void start({ question: input, caseId: w.base_case, asCase: false }); } }} />
                <div className="composer-row">
                  <span className="small muted">{text(data.model.label)}. A development model: it often stops before finishing.</span>
                  <button type="button" className="primary" disabled={blocked || !input.trim()} onClick={() => { void start({ question: input, caseId: w.base_case, asCase: false }); }}><Icon name="zap" size={14} /> Run</button>
                </div>
              </div>
              {problem ? <p className="small warn-text">{problem}</p> : null}
              {elsewhere ? <p className="small warn-text" role="status">Another investigation is running on the model server. This page will be ready when it ends.</p> : null}
              <p className="side-label">Start from a question</p>
              <div className="templates">
                {w.examples.map((q, i) => (
                  <button key={i} type="button" className="template" disabled={blocked} onClick={() => { void start({ question: q, caseId: w.base_case, asCase: i === 0 }); }}>
                    <span className="wf-icon f-problem"><Icon name="target" size={16} /></span><span>{text(q)}</span>
                  </button>
                ))}
              </div>
              {w.scenarios.length ? <>
                <p className="side-label">Or a what-if, with simulated new evidence</p>
                <div className="templates">
                  {w.scenarios.map((s) => (
                    <button key={s.case} type="button" className="template" disabled={blocked} onClick={() => { void start({ question: s.label, caseId: s.case, asCase: true }); }}>
                      <span className="wf-icon f-revision"><Icon name="refresh" size={16} /></span><span>{text(s.label)}</span>
                    </button>
                  ))}
                </div>
              </> : null}
            </div>
          </div>
        )}
      </section>

      <aside className="studio-panel" aria-label="Details">
        {record && step ? (
          <section className="panel-section">
            <div className="row spread"><p className="side-label">Selected step</p><button type="button" className="quiet-button" onClick={() => setStep(null)}>Close</button></div>
            <StepDetail record={record} n={step} />
          </section>
        ) : null}
        {record ? <Outcome record={record} /> : null}
        {record ? (
          <section className="panel-section">
            <p className="side-label">Theories</p>
            <TheoryBoard record={record} onPick={setStep} />
            {!Object.keys(record.theories || {}).length ? <p className="small muted">No theory yet.</p> : null}
          </section>
        ) : (
          <section className="panel-section">
            <p className="side-label">How to read the canvas</p>
            <ul className="legend-list small">
              <li><span className="wf-icon f-problem"><Icon name="target" size={12} /></span>Framing the problem</li>
              <li><span className="wf-icon f-evidence"><Icon name="search" size={12} /></span>Searching and reading evidence</li>
              <li><span className="wf-icon f-theory"><Icon name="bulb" size={12} /></span>Rival theories</li>
              <li><span className="wf-icon f-assess"><Icon name="scale" size={12} /></span>Weighing evidence, one branch per theory</li>
              <li><span className="wf-icon f-challenge"><Icon name="zap" size={12} /></span>Challenging the favourite</li>
              <li><span className="wf-icon f-experiment"><Icon name="flask" size={12} /></span>Designing a test</li>
              <li><span className="wf-icon f-conclusion"><Icon name="flag" size={12} /></span>Position and recommendation</li>
              <li><span className="wf-icon refused-icon"><Icon name="cross" size={12} /></span>Refused by the harness; it changed nothing</li>
            </ul>
            <p className="small muted">Click a step to see exactly what the model sent and what the harness returned. Identical calls in a row are drawn once with a count.</p>
          </section>
        )}
      </aside>
    </div>
  );
}
