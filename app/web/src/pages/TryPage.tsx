import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { api, errorText, postJSON, sendJSON } from '../api.ts';
import { type Attached, AttachmentPicker } from '../components/Attachments.tsx';
import { Icon } from '../components/Icon.tsx';
import { Progress } from '../components/Progress.tsx';
import { ResultView } from '../components/ResultView.tsx';
import { asksOnline, day, runKey, shortCompany, text } from '../labels.ts';
import type { Running } from '../App.tsx';
import type { HistoryEntry, MemoryState, Project, RunDetail, RunRecord, TryRun, TryStatus, Workspace } from '../types.ts';

// Investigate: before a run, one focused question with its options folded away; while it runs, progress; afterwards
// the result, answer first, with follow-ups. The workspace sidebar lists recent investigations and the library manages
// them, so this page has no list of its own. Each company runs only on its own sources; history is kept per person.

type Ask = { question: string; caseId: string; asCase: boolean };
interface Opened { id: string; question: string; record: RunRecord | null; status: string; error: string | null; started: number; ask?: Ask; stopping?: boolean; wrapping?: boolean }

const DEPTH_HINT: Record<string, string> = {
  quick: 'Quick: 5 searches and up to 100 steps. Faster, with fewer sources behind the answer.',
  standard: 'Standard: 8 searches and up to 500 steps. The usual depth; a run ends when it has its answer.',
  thorough: 'Thorough: 12 searches and up to 1,000 steps. More sources and slower; it may stop early if it has too much to read.',
};
const REASON: Record<string, { title: string; text: string }> = {
  interrupted: { title: 'Interrupted', text: 'This investigation stopped before it finished, so there is no result to show. Everything it did up to then was saved.' },
  failed: { title: 'Could not finish', text: 'Something went wrong while this investigation ran.' },
  stopped: { title: 'Stopped by you', text: 'You stopped this investigation before it finished.' },
  unavailable: { title: 'Could not open the result', text: 'This investigation finished, but its result could not be loaded just now.' },
  unreachable: { title: 'Lost the connection', text: 'The page could not reach aemon. It may be restarting; investigations resume after a restart.' },
};
// Technical reasons in plain words, keeping the original after a dash for whoever looks into it
const plainReason = (error: string): string => {
  const known: [RegExp, string][] = [
    [/restarted/i, 'aemon was restarted while this ran, and this run could not be resumed'],
    [/could not resume/i, 'aemon restarted and could not resume this run'],
    [/URLError|Connection refused|timed out|RemoteDisconnected/i, 'the assistant (the model server) stopped responding'],
    [/HTTPError|server refused/i, 'the assistant (the model server) refused a request'],
    [/Request failed: 5\d\d/, 'aemon hit an error loading it'],
  ];
  const hit = known.find(([re]) => re.test(error));
  return hit ? `${hit[1]} — ${error}` : error;
};

function statusOf(e: HistoryEntry): { kind: 'good' | 'bad' | 'warn'; label: string } {
  if (e.status === 'running') return { kind: 'warn', label: 'Running…' };
  if (e.status === 'interrupted') return { kind: 'bad', label: 'Interrupted' };
  if (e.status === 'failed') return { kind: 'bad', label: 'Could not finish' };
  if (e.status === 'stopped') return { kind: 'bad', label: 'Stopped by you' };
  return e.summary?.finished ? { kind: 'good', label: 'Finished' } : e.summary?.draft ? { kind: 'warn', label: 'Draft answer' } : { kind: 'bad', label: 'Stopped early' };
}

export function TryPage({ workspace: w, onError, onMemory, running = [] }: { workspace: Workspace; onError: (error: unknown) => void; onMemory: (project: string | null, name?: string) => void; running?: Running[] }) {
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
  const location = useLocation();
  const [options, setOptions] = useState(false);  // the run settings, folded away until asked for
  const [scenario, setScenario] = useState<Workspace['scenarios'][number] | null>(null);  // a simulated what-if, chosen explicitly
  useEffect(() => { const p = (location.state as { project?: unknown } | null)?.project; if (typeof p === 'string') setProjectView(p); }, [location.state]);  // a project opened from the library
  const [input, setInput] = useState<string>(() => { const q = (location.state as { question?: unknown } | null)?.question; return typeof q === 'string' ? q : ''; });  // an example chosen on Home
  const [starting, setStarting] = useState(false);
  const [live, setLive] = useState(false);
  const [guard, setGuard] = useState(false);  // experimental step-budget guard (docs/RECOVERY_EXPERIMENT.md), off by default
  const [depth, setDepth] = useState<string>(() => { try { return localStorage.getItem('lexsi.depth') || 'standard'; } catch { return 'standard'; } });
  const [loaded, setLoaded] = useState(false);
  const [attached, setAttached] = useState<Attached[]>([]);
  const watching = useRef<string | null>(null);

  const refresh = useCallback(async () => { const d = await api<TryStatus>('/api/try'); setData(d); return d; }, []);
  useEffect(() => { refresh().catch(onError); }, [refresh, onError]);

  const loadHistory = useCallback(async () => {
    const d = await api<{ entries: HistoryEntry[]; projects?: Project[] }>(`/api/workspaces/${w.id}/history`);
    setEntries([...d.entries].sort((a, b) => (b.started ?? 0) - (a.started ?? 0)));
    setProjects(d.projects ?? []);
    setLoaded(true);
  }, [w.id]);
  useEffect(() => { loadHistory().catch(onError); }, [loadHistory, onError]);
  useEffect(() => {
    const ended = (): void => { loadHistory().catch(() => {}); refresh().catch(() => {}); };
    window.addEventListener('investigation-ended', ended);
    return () => window.removeEventListener('investigation-ended', ended);
  }, [loadHistory, refresh]);

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
    if (e.status !== 'running') loadDetail(e.id).catch((error: unknown) => setOpened((o) => (o && o.id === e.id ? { ...o, status: e.status === 'finished' ? 'unavailable' : e.status, error: e.status === 'finished' ? errorText(error) : e.error } : o)));
  }, [routeId, entries, opened?.id, loadDetail, loaded, navigate]);

  // While it runs: poll, then load the full result.
  const runningId = opened && opened.status === 'running' ? opened.id : null;
  useEffect(() => {
    if (!runningId) return undefined;
    watching.current = runningId;
    const id = runningId;
    let timer: number | undefined;
    let misses = 0;
    const tick = async (): Promise<void> => {
      try {
        const d = await api<TryRun>(`/api/try/${id}`);
        misses = 0;
        if (watching.current !== id) return;
        setOpened((o) => (o && o.id === id ? { ...o, record: d.record ?? o.record, status: d.status, error: d.error, wrapping: Boolean(d.wrapping) } : o));
        if (d.status === 'running') timer = window.setTimeout(() => { void tick(); }, 2000);
        else {
          await loadHistory(); await refresh();
          if (d.record) await loadDetail(id).catch(() => {});
          if (d.status === 'finished' && !document.hasFocus()) document.title = '✓ Done · aemon';
        }
      } catch {
        // The server may be restarting: keep trying, then ask the history what really happened (a restart resumes runs).
        misses += 1;
        if (misses < 30) { timer = window.setTimeout(() => { void tick(); }, Math.min(2000 * misses, 10000)); return; }
        try {
          const h = await api<{ entries: HistoryEntry[] }>(`/api/workspaces/${w.id}/history`);
          const e = h.entries.find((x) => x.id === id);
          await loadHistory();
          if (e?.status === 'finished') { await loadDetail(id); setOpened((o) => (o && o.id === id ? { ...o, status: 'finished' } : o)); }
          else setOpened((o) => (o && o.id === id ? { ...o, status: e?.status ?? 'interrupted', error: e?.error ?? 'aemon stopped while this ran.' } : o));
        } catch (error: unknown) { setOpened((o) => (o && o.id === id ? { ...o, status: 'unreachable', error: errorText(error) } : o)); }
      }
    };
    void tick();
    return () => { watching.current = null; if (timer) window.clearTimeout(timer); };
  }, [runningId, loadHistory, refresh, loadDetail, w.id]);

  const elsewhere = Boolean(data?.busy) && !runningId;
  useEffect(() => {
    if (!elsewhere) return undefined;
    const timer = window.setTimeout(() => { refresh().catch(onError); }, 5000);
    return () => window.clearTimeout(timer);
  }, [elsewhere, refresh, onError, data]);
  useEffect(() => { const reset = (): void => { document.title = 'aemon'; }; window.addEventListener('focus', reset); return () => window.removeEventListener('focus', reset); }, []);

  const start = async (ask: Ask, fresh = false, options?: { depth?: string; live?: boolean; project?: string | null; context?: string; attachments?: string[] }): Promise<void> => {
    const question = text(ask.question).trim();
    if (!question || starting) return;
    setStarting(true);
    try {
      const project = options && 'project' in options ? options.project ?? null : projectView ?? (target || null);
      const body: Record<string, unknown> = { workspace: w.id, case: ask.caseId };
      if (ask.asCase) body.shown = question; else body.question = question;
      if (fresh) body.fresh = true;
      if (options?.live ?? live) body.live_research = true;
      if (guard) body.budget_guard = true;
      if (project) body.project = project;
      body.depth = options?.depth ?? depth;
      const files = options?.attachments ?? (options ? [] : attached.map((a) => a.id));
      if (files.length) body.attachments = files;
      if (options?.context) body.context = options.context;
      const { id } = await postJSON<{ id: string }>('/api/try', body);
      setDetail(null);
      setProjectView(null);
      setOpened({ id, question, record: null, status: 'running', error: null, started: Date.now(), ask });
      setInput('');
      if (!options) setAttached([]);
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
  const rerun = (e: HistoryEntry, edit?: { question: string; depth: string; live: boolean; project: string | null; attachments?: string[] }): void => {
    const original = e.question.replace(/ \(live web\)$/, '');
    const question = edit ? edit.question.trim() : original;
    // the same words keep the case's own question (a what-if keeps its scenario); new words ask that question instead
    void start({ question, caseId: e.case, asCase: e.case !== w.base_case && question === original }, true, edit ? { depth: edit.depth, live: edit.live || asksOnline(edit.question), project: edit.project, attachments: edit.attachments ?? [] } : { project: e.project ?? null });
  };

  // The question typed or picked: an example keeps the company's own case for its first question, as before
  const ask = (): Ask => (scenario ? { question: scenario.label, caseId: scenario.case, asCase: true }
    : { question: input, caseId: w.base_case, asCase: w.examples[0] !== undefined && input.trim() === text(w.examples[0]).trim() });
  const depthInfo = (data?.depths ?? []).find((d) => d.id === depth);
  const settingsLine = [depthInfo ? `${depthInfo.label} depth` : null, live ? 'live web search (experimental)' : `${shortCompany(w.company)}'s source library`, memoryOn ? (memoryCount ? `${memoryCount} memory note${memoryCount === 1 ? '' : 's'}` : 'no memory notes') : 'memory off', guard ? 'finish-on-time guard' : null].filter(Boolean).join(' · ');
  const composer = (
    <div className="ask">
      <div className="ask-ctx"><span className="kicker accent"><Icon name="building" size={12} /> {text(w.company)}</span>{viewProject ? <span className="chip"><Icon name="folder" size={11} /> {viewProject.name}</span> : null}</div>
      {scenario ? (
        <div className="ask-scenario">
          <span className="chip sim">Simulated scenario</span>
          <p>{text(scenario.label)}</p>
          <p className="muted small">The agent investigates {shortCompany(w.company)}'s base question; halfway through it receives this made-up result, to show how it updates. It is never counted as real evidence.</p>
          <button type="button" className="button ghost small" onClick={() => setScenario(null)}><Icon name="cross" size={13} /> Back to my own question</button>
        </div>
      ) : (
        <textarea rows={3} maxLength={400} aria-label="Your strategic question" placeholder={`Describe the decision. For example: Should ${shortCompany(w.company)} sell to a new kind of customer?`} value={input} disabled={blocked}
          onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void start(ask()); } }} />
      )}
      <div className="ask-bar">
        <AttachmentPicker workspace={w.id} items={attached} onChange={setAttached} onError={onError} disabled={blocked} />
        <span className="grow" />
        <button type="button" className={`button ghost small ask-opt${options ? ' on' : ''}`} aria-expanded={options} onClick={() => setOptions(!options)}><Icon name="more" size={14} /> Options</button>
        <button type="button" className="button primary big" disabled={blocked || (!scenario && !input.trim())} onClick={() => { void start(ask()); }}>Start investigation <Icon name="arrow" size={15} /></button>
      </div>
      <p className="ask-line small muted">{settingsLine}{!live && asksOnline(input) ? ' · your question asks to search online, so this run will search the live web' : ''}</p>
      {options ? (
        <div className="ask-options">
          <div className="opt">
            <span className="opt-label">Depth</span>
            <div className="seg" role="radiogroup" aria-label="How deep to investigate">
              {(data.depths ?? []).map((d) => (
                <button key={d.id} type="button" role="radio" aria-checked={depth === d.id} title={`${d.searches} searches, up to ${d.turns} steps`}
                  onClick={() => { setDepth(d.id); try { localStorage.setItem('lexsi.depth', d.id); } catch { /* not remembered */ } }}>{d.label}</button>
              ))}
            </div>
            <span className="opt-help">{DEPTH_HINT[depth] ?? ''}</span>
          </div>
          <div className="opt">
            <span className="opt-label">Sources</span>
            <div className="seg" role="radiogroup" aria-label="Where to search">
              <button type="button" role="radio" aria-checked={!live} disabled={blocked} onClick={() => setLive(false)}>Source library</button>
              <button type="button" role="radio" aria-checked={live} disabled={blocked} onClick={() => setLive(true)}>Live web <span className="chip warn tiny">Experimental</span></button>
            </div>
            <span className="opt-help">{live ? 'Searches the live web instead of the company\'s library. Every page is saved and labelled unchecked. Not part of the frozen V1 evaluation.' : `The company's curated library of ${shortCompany(w.company)} sources, as in the evaluation.`}</span>
          </div>
          <div className="opt">
            <span className="opt-label">Finish-on-time guard</span>
            <div className="seg" role="radiogroup" aria-label="Finish-on-time guard">
              <button type="button" role="radio" aria-checked={!guard} disabled={blocked} onClick={() => setGuard(false)}>Off</button>
              <button type="button" role="radio" aria-checked={guard} disabled={blocked} onClick={() => setGuard(true)}>On <span className="chip warn tiny">Experimental</span></button>
            </div>
            <span className="opt-help">When the steps left barely cover what the investigation still needs, the agent is told and stops exploring. Always on in the default aemon system, together with the loop guards (no repeated assessments, quotes picked from the source, repeats redrawn): on development cases they finished 45 of 45 runs against 28, and both blind judges scored them higher. This switch adds the budget guard to the other models.</span>
          </div>
          <div className="opt">
            <span className="opt-label">Memory and project</span>
            <div className="row">
              <button type="button" className="button small" onClick={() => onMemory(scope, viewProject?.name ?? projects.find((p) => p.id === target)?.name)}>
                <Icon name="bulb" size={13} /> {memoryOn ? (memoryCount ? `Using ${memoryCount} memory note${memoryCount === 1 ? '' : 's'}` : 'Memory: none yet') : 'Memory off'}
              </button>
              {!viewProject && projects.length ? (
                <select className="button small" aria-label="Save in project" value={target} onChange={(e) => setTarget(e.target.value)}>
                  <option value="">No project</option>
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              ) : null}
            </div>
            <span className="opt-help">Memory notes are facts you saved earlier; the agent reads them as context, not as evidence.</span>
          </div>
        </div>
      ) : null}
      {!ready ? <p className="notice warn">The agent is not running yet. Start it with <code>./app/run_model.sh</code>, then reload.</p> : null}
      {elsewhere && !running.length ? <p className="notice" role="status">Another investigation is running. You can start yours as soon as it finishes.</p> : null}
      {running.length ? <p className="notice" role="status">One investigation runs at a time. It keeps going if you leave this page; you will see a notice when it finishes.</p> : null}
    </div>
  );

  let main;
  if (opened) {
    if (opened.status === 'running') {
      main = <Progress question={opened.question} record={opened.record} started={opened.started} stopping={Boolean(opened.stopping)} wrapping={Boolean(opened.wrapping)}
        onStop={() => { setOpened((o) => (o ? { ...o, stopping: true } : o)); postJSON(`/api/try/${opened.id}/stop`, {}).catch(onError); }} />;
    } else if (detail && detail.record) {
      main = <ResultView key={opened.id} workspace={w.id} company={w.company} id={opened.id} question={opened.question} started={current?.started ?? null}
        pinned={Boolean(current?.pinned)} project={current?.project ?? null} projects={projects} detail={detail} onError={onError}
        onPin={() => { void change(() => sendJSON(`/api/workspaces/${w.id}/history/${opened.id}`, 'PATCH', { pinned: !current?.pinned })); }}
        onMove={(p) => { void change(() => sendJSON(`/api/workspaces/${w.id}/history/${opened.id}`, 'PATCH', p ? { project: p } : { clear_project: true })); }}
        onDelete={() => { void change(async () => { await sendJSON(`/api/workspaces/${w.id}/history/${opened.id}`, 'DELETE'); navigate('/investigate'); }); }}
        onRerun={current ? (edit) => rerun(current, edit) : null}
        depths={data.depths ?? []}
        onReinvestigate={current ? (context, files) => {
          const original = current.question.replace(/ \(live web\)$/, '');
          void start({ question: original, caseId: current.case, asCase: current.case !== w.base_case }, true,
            { context, attachments: files, depth: detail.settings?.depth ?? 'standard', live: Boolean(detail.settings?.live) || asksOnline(context), project: current.project ?? null });
        } : null}
        onContinue={(!detail.record.final || detail.record.final.draft) && !/live web/.test(opened.question) ? () => {
          postJSON(`/api/workspaces/${w.id}/history/${opened.id}/continue`, {})
            .then(() => { setDetail(null); setOpened((o) => (o ? { ...o, status: 'running', record: detail.record, started: Date.now() } : o)); return loadHistory(); })
            .catch((error: unknown) => onError(new Error(`Could not continue: ${errorText(error)}`)));
        } : null}
        busy={blocked}
        runs={current ? entries.filter((e) => runKey(e) === runKey(current)).map((e) => ({ id: e.id, started: e.started, status: e.status, finished: Boolean(e.summary?.finished), recommendation: e.summary?.recommendation ?? null, stop: e.summary?.stop_reason ?? e.status })) : []}
        onOpenRun={(rid) => navigate(`/investigate/${rid}`)} />;
    } else if (['unavailable', 'unreachable', 'interrupted', 'failed', 'stopped'].includes(opened.status)) {
      const reason = REASON[opened.status] ?? { title: 'Interrupted', text: 'This investigation stopped before it finished.' };
      main = (
        <div className="empty problem">
          <p className="eyebrow">{reason.title}</p>
          <h1>{text(opened.question)}</h1>
          <p>{reason.text}</p>
          {opened.error ? <p className="reason"><b>Reason:</b> {plainReason(opened.error)}</p> : null}
          <div className="row">
            {opened.status === 'unavailable' || opened.status === 'unreachable'
              ? <button type="button" className="button primary" onClick={() => { setOpened((o) => (o ? { ...o, status: 'loading' } : o)); loadDetail(opened.id).then(() => setOpened((o) => (o ? { ...o, status: 'finished' } : o))).catch((error: unknown) => setOpened((o) => (o ? { ...o, status: 'unavailable', error: errorText(error) } : o))); }}>Try again</button>
              : current ? <button type="button" className="button primary" onClick={() => rerun(current)}>Run it again</button> : null}
          </div>
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
      <div className="setup">
        {running.length ? (
          <div className="running-strip panel pad" role="status">
            <span className="pulse" aria-hidden="true" />
            <div><b>{running[0]?.resuming ? 'Resuming after a restart' : 'Still running'}</b><span className="clip">{text(running[0]?.question)}</span></div>
            <button type="button" className="button small" onClick={() => navigate(`/investigate/${running[0]?.id}`)}>View progress</button>
          </div>
        ) : null}
        <header className="setup-head">
          <h1 className="display setup-title">What strategic decision are you facing?</h1>
          <p className="pg-sub">aemon reads {shortCompany(w.company)}'s sources, sets out competing explanations, weighs the evidence for and against each, and recommends what to do, with a small test when one is worth running. It takes a few minutes.</p>
        </header>
        {composer}
        <section className="sec">
          <div className="sec-head"><h2>Start with a question</h2><span className="muted small">Fills in the question; nothing starts until you press Start.</span></div>
          <ul className="tpl-grid">
            {w.examples.map((q, i) => (
              <li key={i}><button type="button" className={`tpl${!scenario && input.trim() === text(q).trim() ? ' on' : ''}`} onClick={() => { setScenario(null); setInput(text(q)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
                <Icon name={i === 0 ? 'target' : i === 1 ? 'eye' : 'flask'} size={16} /><span>{text(q)}</span>
              </button></li>
            ))}
          </ul>
        </section>
        {w.scenarios.length ? (
          <details className="scen">
            <summary><span><b>Explore a simulated scenario</b><span className="muted small">See how the agent updates its view when a made-up result appears mid-investigation. For understanding the method, not for decisions.</span></span><span className="chip sim">Simulated</span></summary>
            <ul className="tpl-grid">
              {w.scenarios.map((sc) => (
                <li key={sc.case}><button type="button" className={`tpl sim${scenario?.case === sc.case ? ' on' : ''}`} onClick={() => { setScenario(sc); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
                  <Icon name="refresh" size={16} /><span>{text(sc.label)}</span>
                </button></li>
              ))}
            </ul>
          </details>
        ) : null}
        {!entries.length ? (
          <ol className="how-strip">
            <li><b>Ask</b><span>a decision question, or pick one above.</span></li>
            <li><b>Watch</b><span>the agent gather sources and weigh the evidence.</span></li>
            <li><b>Read</b><span>the recommendation, its uncertainties, and the test it proposes.</span></li>
          </ol>
        ) : null}
      </div>
    );
  }

  return <div className={`inv-page${routeId ? ' open' : ''}`}>{main}</div>;
}
