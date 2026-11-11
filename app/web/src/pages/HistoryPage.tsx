import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, postJSON, sendJSON } from '../api.ts';
import { Icon } from '../components/Icon.tsx';
import { cut, day, runKey, text } from '../labels.ts';
import type { HistoryEntry, Project, Workspace } from '../types.ts';
import { outcomeOf } from './HomePage.tsx';

// The research library: every investigation of this company, from the saved history only. Collections on the left
// (all, pinned, each project), search, outcome filters and sorting above, rows or cards below. Repeated runs of the
// same question are kept apart and numbered, never merged. Pick two to compare them side by side.

const FILTERS = [['all', 'All'], ['good', 'Finished'], ['warn', 'Stopped early or draft'], ['bad', 'Interrupted'], ['run', 'Running']] as const;
const VIEW_KEY = 'lexsi.library.view';

function RowMenu({ e, w, projects, onChanged, onError }: { e: HistoryEntry; w: string; projects: Project[]; onChanged: () => void; onError: (x: unknown) => void }) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return undefined;
    const close = (x: MouseEvent | KeyboardEvent): void => { if (x instanceof KeyboardEvent ? x.key === 'Escape' : !box.current?.contains(x.target as Node)) { setOpen(false); setConfirm(false); } };
    document.addEventListener('mousedown', close); document.addEventListener('keydown', close);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', close); };
  }, [open]);
  const base = `/api/workspaces/${w}/history/${e.id}`;
  const act = (fn: () => Promise<unknown>): void => { fn().then(() => { setOpen(false); setConfirm(false); onChanged(); }).catch(onError); };
  return (
    <div className="rmenu" ref={box}>
      <button type="button" className="button ghost small icon-only" aria-label="Actions" aria-expanded={open} onClick={() => setOpen(!open)}><Icon name="more" size={15} /></button>
      {open ? (
        <div className="rmenu-pop" role="menu">
          <button type="button" role="menuitem" onClick={() => act(() => sendJSON(base, 'PATCH', { pinned: !e.pinned }))}><Icon name="pin" size={14} /> {e.pinned ? 'Unpin' : 'Pin'}</button>
          {projects.filter((p) => p.id !== e.project).map((p) => (
            <button key={p.id} type="button" role="menuitem" onClick={() => act(() => sendJSON(base, 'PATCH', { project: p.id }))}><Icon name="folder" size={14} /> Move to {p.name}</button>
          ))}
          {e.project ? <button type="button" role="menuitem" onClick={() => act(() => sendJSON(base, 'PATCH', { clear_project: true }))}><Icon name="folder" size={14} /> Remove from project</button> : null}
          {confirm
            ? <button type="button" role="menuitem" className="danger" onClick={() => act(() => sendJSON(base, 'DELETE'))}><Icon name="trash" size={14} /> Delete for good</button>
            : <button type="button" role="menuitem" className="danger" onClick={() => setConfirm(true)}><Icon name="trash" size={14} /> Delete…</button>}
        </div>
      ) : null}
    </div>
  );
}

export function HistoryPage({ workspace: w, onError }: { workspace: Workspace; onError: (e: unknown) => void }) {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<HistoryEntry[] | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<string>('all');
  const [where, setWhere] = useState<string>('all');  // all, pinned, or a project id
  const [sort, setSort] = useState<'new' | 'old'>('new');
  const [view, setView] = useState<'list' | 'cards'>(() => { try { return localStorage.getItem(VIEW_KEY) === 'cards' ? 'cards' : 'list'; } catch { return 'list'; } });
  const [picked, setPicked] = useState<string[]>([]);
  const [naming, setNaming] = useState<string | null>(null);  // '' for a new project, an id to rename one
  const [name, setName] = useState('');
  const load = useCallback(() => {
    api<{ entries: HistoryEntry[]; projects?: Project[] }>(`/api/workspaces/${w.id}/history`)
      .then((d) => { setEntries(d.entries); setProjects(d.projects ?? []); })
      .catch((e) => { setEntries([]); onError(e); });
  }, [w.id, onError]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { try { localStorage.setItem(VIEW_KEY, view); } catch { /* not remembered */ } }, [view]);

  // Runs of the same question are numbered in the order they started, so repeats stay distinguishable
  const runNo = useMemo(() => {
    const m = new Map<string, { n: number; of: number }>();
    const groups = new Map<string, HistoryEntry[]>();
    for (const e of entries ?? []) groups.set(runKey(e), [...(groups.get(runKey(e)) ?? []), e]);
    for (const g of groups.values()) [...g].sort((a, b) => (a.started ?? 0) - (b.started ?? 0)).forEach((e, i) => m.set(e.id, { n: i + 1, of: g.length }));
    return m;
  }, [entries]);
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return [...(entries ?? [])]
      .sort((a, b) => (sort === 'new' ? -1 : 1) * ((a.started ?? 0) - (b.started ?? 0)))
      .filter((e) => filter === 'all' || outcomeOf(e).kind === filter)
      .filter((e) => where === 'all' || (where === 'pinned' ? e.pinned : e.project === where))
      .filter((e) => !q || `${e.question} ${e.summary?.recommendation ?? ''}`.toLowerCase().includes(q));
  }, [entries, query, filter, where, sort]);
  const counts = (k: string): number => (entries ?? []).filter((e) => k === 'all' || (k === 'pinned' ? e.pinned : e.project === k)).length;
  const toggle = (id: string): void => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p.slice(-1), id]));

  const saveName = (): void => {
    const title = name.trim();
    if (!title) { setNaming(null); return; }
    (naming === '' ? postJSON(`/api/workspaces/${w.id}/projects`, { name: title }) : sendJSON(`/api/workspaces/${w.id}/projects/${naming}`, 'PATCH', { name: title }))
      .then(() => { setNaming(null); setName(''); load(); }).catch(onError);
  };
  const removeProject = (id: string): void => { sendJSON(`/api/workspaces/${w.id}/projects/${id}`, 'DELETE').then(() => { if (where === id) setWhere('all'); load(); }).catch(onError); };
  const nameBox = (
    <form className="ilib-name" onSubmit={(e) => { e.preventDefault(); saveName(); }}>
      <input autoFocus maxLength={80} value={name} placeholder="Project name" aria-label="Project name" onChange={(e) => setName(e.target.value)} onBlur={saveName} />
    </form>
  );
  const current = projects.find((p) => p.id === where);

  return (
    <div className="pg ilib">
      <header className="pg-head">
        <div>
          <span className="kicker accent">{text(w.company)}</span>
          <h1 className="pg-title">Investigations</h1>
          <p className="pg-sub">Every investigation of {text(w.company)}, with its report and reasoning map. Repeated runs of a question are kept separate and numbered.</p>
        </div>
        <button type="button" className="button primary big" onClick={() => navigate('/investigate')}><Icon name="plus" size={15} /> New investigation</button>
      </header>

      <div className="ilib-body">
        <nav className="ilib-cols" aria-label="Collections">
          <button type="button" aria-current={where === 'all'} onClick={() => setWhere('all')}><Icon name="library" size={15} /><span>All investigations</span><b>{counts('all')}</b></button>
          <button type="button" aria-current={where === 'pinned'} onClick={() => setWhere('pinned')}><Icon name="pin" size={15} /><span>Pinned</span><b>{counts('pinned')}</b></button>
          <p className="side-label ilib-label">Projects <button type="button" className="button ghost small icon-only" aria-label="New project" onClick={() => { setNaming(''); setName(''); }}><Icon name="plus" size={13} /></button></p>
          {naming === '' ? nameBox : null}
          {projects.map((p) => naming === p.id ? <div key={p.id}>{nameBox}</div> : (
            <button key={p.id} type="button" aria-current={where === p.id} onClick={() => setWhere(p.id)}><Icon name="folder" size={15} /><span>{p.name}</span><b>{counts(p.id)}</b></button>
          ))}
          {!projects.length && naming !== '' ? <p className="muted small ilib-hint">Group related investigations into a project, each with its own memory.</p> : null}
        </nav>

        <div className="ilib-main">
          {current ? (
            <div className="ilib-project panel pad">
              <div><span className="kicker"><Icon name="folder" size={12} /> Project</span><h2 className="display">{current.name}</h2></div>
              <div className="row">
                <button type="button" className="button small primary" onClick={() => navigate('/investigate', { state: { project: current.id } })}><Icon name="plus" size={13} /> New in this project</button>
                <button type="button" className="button small" onClick={() => { setNaming(current.id); setName(current.name); }}>Rename</button>
                <button type="button" className="button small ghost" title="Its investigations go back to the main list" onClick={() => removeProject(current.id)}>Delete project</button>
              </div>
            </div>
          ) : null}
          <div className="ilib-tools">
            <label className="field ilib-search"><Icon name="search" size={15} /><input type="search" placeholder="Search questions and recommendations" value={query} onChange={(e) => setQuery(e.target.value)} /></label>
            <div className="seg" role="radiogroup" aria-label="Outcome">
              {FILTERS.map(([id, label]) => <button key={id} type="button" role="radio" aria-checked={filter === id} onClick={() => setFilter(id)}>{label}</button>)}
            </div>
            <span className="grow" />
            <div className="seg" role="radiogroup" aria-label="Order">
              <button type="button" role="radio" aria-checked={sort === 'new'} onClick={() => setSort('new')}>Newest</button>
              <button type="button" role="radio" aria-checked={sort === 'old'} onClick={() => setSort('old')}>Oldest</button>
            </div>
            <div className="seg" role="radiogroup" aria-label="Layout">
              <button type="button" role="radio" aria-checked={view === 'list'} aria-label="List" title="List" onClick={() => setView('list')}><Icon name="list" size={14} /></button>
              <button type="button" role="radio" aria-checked={view === 'cards'} aria-label="Cards" title="Cards" onClick={() => setView('cards')}><Icon name="library" size={14} /></button>
            </div>
          </div>

          {entries === null ? <div className="ilib-list">{[0, 1, 2, 3].map((i) => <div key={i} className="skel" style={{ height: 64 }} />)}</div> : !rows.length ? (
            <div className="empty-box">
              <b>{entries.length ? 'Nothing matches' : 'No investigations yet'}</b>
              <span>{entries.length ? 'Try another search, outcome or collection.' : 'Start one and it is saved here, with its report and reasoning map.'}</span>
              {entries.length ? <button type="button" className="button small" onClick={() => { setQuery(''); setFilter('all'); setWhere('all'); }}>Clear filters</button> : <button type="button" className="button primary" onClick={() => navigate('/investigate')}>Start an investigation</button>}
            </div>
          ) : (
            <ul className={view === 'cards' ? 'ilib-cards' : 'ilib-list'}>{rows.map((e) => {
              const o = outcomeOf(e); const r = runNo.get(e.id); const sel = picked.includes(e.id);
              const preview = e.summary?.recommendation ? cut(e.summary.recommendation) : e.summary?.position ? `Interim view: ${cut(e.summary.position)}` : null;
              return (
                <li key={e.id} className={`ilib-item${sel ? ' sel' : ''}`}>
                  <Link to={`/investigate/${e.id}`} className="inv-hit" aria-label={`Open: ${text(e.question)}`} />
                  <label className="ilib-pick" title="Select to compare"><input type="checkbox" checked={sel} onChange={() => toggle(e.id)} aria-label="Select to compare" /></label>
                  <div className="ilib-text">
                    <p className="ilib-q">{e.pinned ? <Icon name="pin" size={12} /> : null}{text(e.question)}</p>
                    {preview ? <p className="ilib-prev">{e.summary?.recommendation ? <span className="muted">Recommends: </span> : null}{preview}</p> : null}
                  </div>
                  <div className="ilib-meta">
                    <span className={`chip ${o.kind === 'good' ? 'good' : o.kind === 'run' ? 'accent' : o.kind === 'warn' ? 'warn' : 'bad'}`}>{o.label}</span>
                    {w.scenarios.some((c) => c.case === e.case) ? <span className="chip sim">Simulated</span> : null}
                    <span className="muted small nowrap">{day(e.started)}</span>
                    {r && r.of > 1 ? <span className="chip" title={`Run id ${e.id.slice(0, 8)}`}>Run {r.n} of {r.of}</span> : null}
                  </div>
                  <div className="ilib-acts">
                    {o.kind !== 'run' ? <Link to={`/map/${e.id}`} className="button ghost small"><Icon name="map" size={13} /> Map</Link> : null}
                    <RowMenu e={e} w={w.id} projects={projects} onChanged={load} onError={onError} />
                  </div>
                </li>
              );
            })}</ul>
          )}
          <p className="muted small">{rows.length} of {entries?.length ?? 0} shown. Investigations are kept per person and per company.</p>
        </div>
      </div>

      {picked.length ? (
        <div className="compare-bar" role="status">
          <span>{picked.length === 1 ? 'Pick one more investigation to compare.' : 'Two investigations selected.'}</span>
          <button type="button" className="button primary small" disabled={picked.length < 2} onClick={() => navigate(`/compare/${picked[0]}/${picked[1]}`)}>Compare side by side</button>
          <button type="button" className="button ghost small" onClick={() => setPicked([])}>Clear</button>
        </div>
      ) : null}
    </div>
  );
}
