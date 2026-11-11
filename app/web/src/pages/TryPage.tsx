import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, errorText, postJSON, sendJSON } from '../api.ts';
import { HistoryPanel } from '../components/HistoryPanel.tsx';
import { Icon } from '../components/Icon.tsx';
import { Progress } from '../components/Progress.tsx';
import { ResultView } from '../components/ResultView.tsx';
import { day, shortCompany, text } from '../labels.ts';
import type { HistoryEntry, MemoryState, Project, RunDetail, RunRecord, TryRun, TryStatus, Workspace } from '../types.ts';

// Investigate: the company's investigations on the left (pinned, projects, recent), one reading column on the right.
// Before a run it asks for the decision; while it runs it shows progress; afterwards the result, answer first, with
// follow-ups. Each company runs only on its own sources, and its history is kept on the server per person.

type Ask = { question: string; caseId: string; asCase: boolean };
interface Opened { id: string; question: string; record: RunRecord | null; status: string; error: string | null; started: number; ask?: Ask; stopping?: boolean }

function statusOf(e: HistoryEntry): { kind: 'good' | 'bad' | 'warn'; label: string } {
  if (e.status === 'running') return { kind: 'warn', label: 'Running…' };
  if (e.status === 'interrupted') return { kind: 'bad', label: 'Interrupted' };
  if (e.status === 'failed') return { kind: 'bad', label: 'Could not finish' };
  if (e.status === 'stopped') return { kind: 'bad', label: 'Stopped by you' };
  return e.summary?.finished ? { kind: 'good', label: 'Finished' } : { kind: 'bad', label: 'Stopped early' };
}

export function TryPage({ workspace: w, onError, onMemory }: { workspace: Workspace; onError: (error: unknown) => void; onMemory: (project: string | null, name?: string) => void }) {
  const navigate = useNavigate();
  const { id: routeId } = useParams();
  const [data, setData] = useState<TryStatus | null>(null);
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [opened, setOpened] = useState<Opened | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [projectView, setProjectView] = useState<string | null>(null);
  const [target, setTarget] = useState<string>('');  // the project a new investigation is saved in
  const [memoryCount, setMemoryCount] = useState(0);
  const [memoryOn, setMemoryOn] = useState(true);
  const [input, setInput] = useState('');
  const [starting, setStarting] = useState(false);
  const [live, setLive] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const watching = useRef<string | null>(null);

  useEffect(() => { document.body.classList.add('app-full'); return () => document.body.classList.remove('app-full'); }, []);
  const refresh = useCallback(async () => { const d = await api<TryStatus>('/api/try'); setData(d); return d; }, []);
  useEffect(() => { refresh().catch(onError); }, [refresh, onError]);

  const loadHistory = useCallback(async () => {
    const d = await api<{ entries: HistoryEntry[]; projects?: Project[] }>(`/api/workspaces/${w.id}/history`);
    setEntries([...d.entries].sort((a, b) => (b.started ?? 0) - (a.started ?? 0)));
    setProjects(d.projects ?? []);
    setLoaded(true);
  }, [w.id]);
  useEffect(() => { loadHistory().catch(onError); }, [loadHistory, onError]);

  const scope = projectView ?? (target || null);
  const loadMemory = useCallback(async () => {
    const q = new URLSearchParams({ workspace: w.id, ...(scope ? { project: scope } : {}) });
    const m = await api<MemoryState>(`/api/memory?${q.toString()}`);
    setMemoryOn(m.enabled);
    setMemoryCount(m.global.length + m.company.length + m.project.length);
  }, [w.id, scope]);
  useEffect(() => {
    loadMemory().catch(() => {});
    const again = (): void => { loadMemory().catch(() => {}); };
    window.addEventListener('memory-changed', again);
    window.addEventListener('memory-counted', again);
    return () => { window.removeEventListener('memory-changed', again); window.removeEventListener('memory-counted', again); };
  }, [loadMemory]);

  const loadDetail = useCallback(async (id: string) => {
    const d = await api<RunDetail>(`/api/workspaces/${w.id}/history/${id}`);
    setDetail(d);
  }, [w.id]);

  // Open the investigation named in the address (from the history, the mind map or a link).
  useEffect(() => {
    if (!routeId) { setOpened(null); setDetail(null); return; }
    if (opened?.id === routeId) return;
    const e = entries.find((x) => x.id === routeId);
    if (!e) { if (loaded) navigate('/investigate', { replace: true }); return; }
    setProjectView(null);
    setDetail(null);
    setOpened({ id: e.id, question: e.question, record: null, status: e.status, error: e.error, started: (e.started ?? Date.now() / 1000) * 1000 });
    if (e.status !== 'running') loadDetail(e.id).catch(() => setOpened((o) => (o && o.id === e.id ? { ...o, status: 'unavailable' } : o)));
  }, [routeId, entries, opened?.id, loadDetail, loaded, navigate]);

  // While it runs: poll, then load the full result.
  const runningId = opened && opened.status === 'running' ? opened.id : null;
  useEffect(() => {
    if (!runningId) return undefined;
    watching.current = runningId;
    const id = runningId;
    let timer: number | undefined;
    const tick = async (): Promise<void> => {
      try {
        const d = await api<TryRun>(`/api/try/${id}`);
        if (watching.current !== id) return;
        setOpened((o) => (o && o.id === id ? { ...o, record: d.record ?? o.record, status: d.status, error: d.error } : o));
        if (d.status === 'running') timer = window.setTimeout(() => { void tick(); }, 2000);
        else {
          await loadHistory(); await refresh();
          if (d.record) await loadDetail(id).catch(() => {});
          if (d.status === 'finished' && !document.hasFocus()) document.title = '✓ Done · Aemon';
        }
      } catch (error: unknown) {
        await loadHistory().catch(() => {});
        setOpened((o) => (o && o.id === id ? { ...o, status: 'interrupted', error: errorText(error) } : o));
      }
    };
    void tick();
    return () => { watching.current = null; if (timer) window.clearTimeout(timer); };
  }, [runningId, loadHistory, refresh, loadDetail]);

  const elsewhere = Boolean(data?.busy) && !runningId;
  useEffect(() => {
    if (!elsewhere) return undefined;
    const timer = window.setTimeout(() => { refresh().catch(onError); }, 5000);
    return () => window.clearTimeout(timer);
  }, [elsewhere, refresh, onError, data]);
  useEffect(() => { const reset = (): void => { document.title = 'Aemon'; }; window.addEventListener('focus', reset); return () => window.removeEventListener('focus', reset); }, []);

  const start = async (ask: Ask, fresh = false): Promise<void> => {
    const question = text(ask.question).trim();
    if (!question || starting) return;
    setStarting(true);
    try {
      const project = projectView ?? (target || null);
      const body: Record<string, unknown> = { workspace: w.id, case: ask.caseId };
      if (ask.asCase) body.shown = question; else body.question = question;
      if (fresh) body.fresh = true;
      if (live) body.live_research = true;
      if (project) body.project = project;
      const { id } = await postJSON<{ id: string }>('/api/try', body);
      setDetail(null);
      setProjectView(null);
      setOpened({ id, question, record: null, status: 'running', error: null, started: Date.now(), ask });
      setInput('');
      await loadHistory();
      navigate(`/investigate/${id}`);
    } catch (error: unknown) {
      onError(new Error(`Could not start the investigation: ${errorText(error)}`));
    } finally { setStarting(false); }
  };

  const change = async (fn: () => Promise<unknown>): Promise<void> => { try { await fn(); await loadHistory(); } catch (e: unknown) { onError(e); } };
  const current = opened ? entries.find((e) => e.id === opened.id) : undefined;

  if (!data) return <div className="page-pad"><p className="muted">Loading…</p></div>;
  const ready = data.model_ready && data.model.available;
  const blocked = !ready || Boolean(runningId) || elsewhere || starting;
  const viewProject = projects.find((p) => p.id === projectView);
  const projectEntries = viewProject ? entries.filter((e) => e.project === viewProject.id) : [];
  const rerun = (e: HistoryEntry): void => { void start({ question: e.question.replace(/ \(live web\)$/, ''), caseId: e.case, asCase: e.case !== w.base_case }, true); };

  const composer = (
    <div className="composer">
      <textarea rows={3} maxLength={400} aria-label="Your question" placeholder={`e.g. Should ${shortCompany(w.company)} sell to a new kind of customer?`} value={input} disabled={blocked}
        onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void start({ question: input, caseId: w.base_case, asCase: false }); } }} />
      <div className="composer-row">
        <button type="button" className="chip-button" onClick={() => onMemory(scope, viewProject?.name ?? projects.find((p) => p.id === target)?.name)}>
          <Icon name="bulb" size={13} /> {memoryOn ? (memoryCount ? `Using ${memoryCount} memory note${memoryCount === 1 ? '' : 's'}` : 'Memory: none yet') : 'Memory off'}
        </button>
        {!viewProject && projects.length ? (
          <label className="chip-button select-chip"><Icon name="folder" size={13} />
            <select aria-label="Save in project" value={target} onChange={(e) => setTarget(e.target.value)}>
              <option value="">No project</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
        ) : null}
        <details className="options"><summary className="chip-button">Options</summary>
          <label className="check"><input type="checkbox" checked={live} disabled={blocked} onChange={(e) => setLive(e.target.checked)} /> Search the live web (experimental; pages are saved and labelled unchecked)</label>
        </details>
        <span className="grow" />
        <button type="button" className="button primary big" disabled={blocked || !input.trim()} onClick={() => { void start({ question: input, caseId: w.base_case, asCase: false }); }}>Start investigation</button>
      </div>
      {!ready ? <p className="notice warn">The assistant is not running yet. Start it with <code>./app/run_model.sh</code>, then reload.</p> : null}
      {elsewhere ? <p className="notice" role="status">Another investigation is running. You can start yours as soon as it finishes.</p> : null}
    </div>
  );

  let main;
  if (opened) {
    if (opened.status === 'running') {
      main = <Progress question={opened.question} record={opened.record} started={opened.started} stopping={Boolean(opened.stopping)}
        onStop={() => { setOpened((o) => (o ? { ...o, stopping: true } : o)); postJSON(`/api/try/${opened.id}/stop`, {}).catch(onError); }} />;
    } else if (detail && detail.record) {
      main = <ResultView key={opened.id} workspace={w.id} company={w.company} id={opened.id} question={opened.question} started={current?.started ?? null}
        pinned={Boolean(current?.pinned)} project={current?.project ?? null} projects={projects} detail={detail} onError={onError}
        onPin={() => { void change(() => sendJSON(`/api/workspaces/${w.id}/history/${opened.id}`, 'PATCH', { pinned: !current?.pinned })); }}
        onMove={(p) => { void change(() => sendJSON(`/api/workspaces/${w.id}/history/${opened.id}`, 'PATCH', p ? { project: p } : { clear_project: true })); }}
        onDelete={() => { void change(async () => { await sendJSON(`/api/workspaces/${w.id}/history/${opened.id}`, 'DELETE'); navigate('/investigate'); }); }}
        onRerun={!detail.record.final && current ? () => rerun(current) : null} />;
    } else if (['unavailable', 'interrupted', 'failed'].includes(opened.status)) {
      main = (
        <div className="empty"><h1>{text(opened.question)}</h1>
          <p>{opened.status === 'failed' ? 'This investigation could not finish.' : 'This investigation was interrupted before it saved a result.'}</p>
          {current ? <button type="button" className="button primary" onClick={() => rerun(current)}>Run it again</button> : null}
        </div>
      );
    } else main = <p className="muted">Loading…</p>;
  } else if (viewProject) {
    main = (
      <div className="project-page">
        <p className="eyebrow"><Icon name="folder" size={13} /> Project</p>
        <h1>{viewProject.name}</h1>
        <p className="lead">Investigations started here use this project's memory as well as your company's.</p>
        <button type="button" className="chip-button" onClick={() => onMemory(viewProject.id, viewProject.name)}><Icon name="bulb" size={13} /> Project memory</button>
        <h2>New investigation in this project</h2>
        {composer}
        <h2>In this project</h2>
        {projectEntries.length ? (
          <ul className="cards">{projectEntries.map((e) => { const s = statusOf(e); return (
            <li key={e.id}><button type="button" className="inv-card" onClick={() => navigate(`/investigate/${e.id}`)}>
              <span className={`status-chip ${s.kind}`}>{s.label}</span><b>{text(e.question)}</b>
              {e.summary?.recommendation ? <span className="muted small">{text(e.summary.recommendation).slice(0, 180)}</span> : null}
              <span className="muted small">{day(e.started)}</span></button></li>); })}</ul>
        ) : <p className="muted">No investigations here yet. Start one above, or move one in from its menu.</p>}
      </div>
    );
  } else {
    main = (
      <div className="home">
        <p className="eyebrow">{text(w.company)}</p>
        <h1>What decision are you facing?</h1>
        <p className="lead">The assistant reads public sources about {shortCompany(w.company)}, lists possible reasons customers would buy, weighs the evidence for and against each, and recommends what to do, with a small test when one is worth running. It takes a few minutes.</p>
        {composer}
        {!entries.length ? (
          <ol className="welcome">
            <li><b>Ask a decision question</b>, or pick an example below.</li>
            <li><b>Watch it work.</b> It gathers sources and weighs the evidence.</li>
            <li><b>Get a recommendation</b>, how sure it is, and a test you could run. Ask follow-ups, or download a PDF.</li>
          </ol>
        ) : null}
        <h2>Try one of these</h2>
        <div className="templates">
          {w.examples.map((q, i) => (
            <button key={i} type="button" className="template" disabled={blocked} onClick={() => { void start({ question: q, caseId: w.base_case, asCase: i === 0 }); }}>
              <Icon name="target" size={16} /><span>{text(q)}</span>
            </button>
          ))}
        </div>
        {w.scenarios.length ? <>
          <h2>What if new evidence appeared?</h2>
          <p className="muted small">These add a simulated result halfway through, to see how the assistant updates its view. Simulated results are never treated as real evidence.</p>
          <div className="templates">
            {w.scenarios.map((s) => (
              <button key={s.case} type="button" className="template" disabled={blocked} onClick={() => { void start({ question: s.label, caseId: s.case, asCase: true }); }}>
                <Icon name="refresh" size={16} /><span>{text(s.label)}</span><span className="sim-chip">Simulated</span>
              </button>
            ))}
          </div>
        </> : null}
      </div>
    );
  }

  return (
    <div className="studio">
      <aside className="studio-side" aria-label="Your investigations">
        <button type="button" className="new-run" onClick={() => { setProjectView(null); navigate('/investigate'); }}><Icon name="plus" size={15} /> New investigation</button>
        <HistoryPanel workspace={w.id} company={shortCompany(w.company)} entries={entries} projects={projects}
          openedId={opened?.id ?? null} onOpen={(e) => navigate(`/investigate/${e.id}`)} onChanged={loadHistory} onError={onError}
          onDeleted={(id) => { if (opened?.id === id) navigate('/investigate'); }}
          onOpenProject={(id) => { setProjectView(id); navigate('/investigate'); }}
          status={statusOf}
          meta={(e) => (e.started ? ` · ${day(e.started)}` : '')} />
      </aside>
      <section className="studio-main" aria-label="Investigation"><div className="reading">{main}</div></section>
    </div>
  );
}
