import { useEffect, useRef, useState } from 'react';
import { postJSON, sendJSON } from '../api.ts';
import type { HistoryEntry, Project } from '../types.ts';
import { Icon } from './Icon.tsx';

// The Try it history: pinned investigations first, then projects (folders), then the rest. Each item has a menu to pin,
// move to a project, or delete; deleting asks inline, never through a browser dialog.

interface Props {
  workspace: string;
  company: string;
  entries: HistoryEntry[];
  projects: Project[];
  openedId: string | null;
  onOpen: (entry: HistoryEntry) => void;
  onChanged: () => Promise<void>;
  onDeleted: (id: string) => void;
  onError: (error: unknown) => void;
  onOpenProject?: (id: string) => void;
  status: (entry: HistoryEntry) => { kind: string; label: string };
  meta: (entry: HistoryEntry) => string;
}

function Item({ entry, props, menuFor, setMenuFor }: { entry: HistoryEntry; props: Props; menuFor: string | null; setMenuFor: (id: string | null) => void }) {
  const { workspace, projects, openedId, onOpen, onChanged, onDeleted, onError, status, meta } = props;
  const [confirm, setConfirm] = useState(false);
  const s = status(entry);
  const base = `/api/workspaces/${workspace}/history/${entry.id}`;
  const act = async (fn: () => Promise<unknown>): Promise<void> => {
    try { await fn(); setMenuFor(null); setConfirm(false); await onChanged(); } catch (error: unknown) { onError(error); }
  };
  const open = menuFor === entry.id;
  return (
    <li className={`history-row${open ? ' menu-open' : ''}`}>
      <button type="button" className="history-item" aria-pressed={openedId === entry.id} onClick={() => onOpen(entry)}>
        <span className={`history-dot ${s.kind}`} aria-hidden="true" />
        <span className="history-text">
          <span className="history-q">{entry.pinned ? <span className="pin-mark" title="Pinned"><Icon name="pin" size={11} /></span> : null}{entry.question}</span>
          <span className="history-meta">{s.label}{meta(entry)}</span>
        </span>
      </button>
      <button type="button" className="history-more" aria-label={`Actions for “${entry.question}”`} aria-expanded={open} onClick={() => { setMenuFor(open ? null : entry.id); setConfirm(false); }}>
        <Icon name="more" size={16} />
      </button>
      {open ? (
        <div className="history-menu" role="menu">
          <button type="button" role="menuitem" onClick={() => { void act(() => sendJSON(base, 'PATCH', { pinned: !entry.pinned })); }}>
            <Icon name="pin" size={14} /> {entry.pinned ? 'Unpin' : 'Pin'}
          </button>
          {projects.length || entry.project ? <p className="menu-label">Move to project</p> : null}
          {projects.filter((p) => p.id !== entry.project).map((p) => (
            <button key={p.id} type="button" role="menuitem" onClick={() => { void act(() => sendJSON(base, 'PATCH', { project: p.id })); }}>
              <Icon name="folder" size={14} /> {p.name}
            </button>
          ))}
          {entry.project ? (
            <button type="button" role="menuitem" onClick={() => { void act(() => sendJSON(base, 'PATCH', { clear_project: true })); }}>
              <Icon name="folder" size={14} /> Remove from project
            </button>
          ) : null}
          {confirm ? (
            <div className="menu-confirm">
              <p className="small">Delete this investigation from your history? This cannot be undone.</p>
              <button type="button" className="danger" onClick={() => { void act(async () => { await sendJSON(base, 'DELETE'); onDeleted(entry.id); }); }}>Delete</button>
              <button type="button" onClick={() => setConfirm(false)}>Cancel</button>
            </div>
          ) : (
            <button type="button" role="menuitem" className="danger-text" disabled={entry.status === 'running'} onClick={() => setConfirm(true)}>
              <Icon name="trash" size={14} /> Delete
            </button>
          )}
        </div>
      ) : null}
    </li>
  );
}

export function HistoryPanel(props: Props) {
  const { workspace, company, entries, projects, onChanged, onError } = props;
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [naming, setNaming] = useState<string | null>(null);  // '' for a new project, an id to rename one
  const [name, setName] = useState('');
  const [closed, setClosed] = useState<Record<string, boolean>>({});
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {  // a click outside closes the open menu
    const close = (e: MouseEvent): void => { if (panel.current && !panel.current.contains(e.target as Node)) setMenuFor(null); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);
  const saveName = async (): Promise<void> => {
    const title = name.trim();
    if (!title) { setNaming(null); return; }
    try {
      if (naming === '') await postJSON(`/api/workspaces/${workspace}/projects`, { name: title });
      else await sendJSON(`/api/workspaces/${workspace}/projects/${naming}`, 'PATCH', { name: title });
      setNaming(null); setName(''); await onChanged();
    } catch (error: unknown) { onError(error); }
  };
  const removeProject = async (id: string): Promise<void> => {
    try { await sendJSON(`/api/workspaces/${workspace}/projects/${id}`, 'DELETE'); await onChanged(); } catch (error: unknown) { onError(error); }
  };
  const pinned = entries.filter((e) => e.pinned);
  const loose = entries.filter((e) => !e.pinned && !e.project);
  const list = (items: HistoryEntry[]) => items.map((e) => <Item key={e.id} entry={e} props={props} menuFor={menuFor} setMenuFor={setMenuFor} />);
  const nameBox = (
    <form className="project-name" onSubmit={(e) => { e.preventDefault(); void saveName(); }}>
      <input autoFocus maxLength={80} value={name} placeholder="Project name" aria-label="Project name" onChange={(e) => setName(e.target.value)} onBlur={() => { void saveName(); }} />
    </form>
  );
  return (
    <div ref={panel} className="history-panel">
      {pinned.length ? (<><p className="side-label">Pinned</p><ol className="history">{list(pinned)}</ol></>) : null}
      <div className="side-label-row">
        <p className="side-label">Projects</p>
        <button type="button" className="link small" onClick={() => { setNaming(''); setName(''); }}><Icon name="plus" size={12} /> New project</button>
      </div>
      {naming === '' ? nameBox : null}
      {projects.map((p) => {
        const items = entries.filter((e) => e.project === p.id && !e.pinned);
        const isClosed = closed[p.id];
        return (
          <div key={p.id} className="project">
            {naming === p.id ? nameBox : (
              <div className="project-head">
                <button type="button" className="project-fold" aria-label={isClosed ? `Show ${p.name}` : `Hide ${p.name}`} aria-expanded={!isClosed} onClick={() => setClosed((c) => ({ ...c, [p.id]: !isClosed }))}>{isClosed ? '▸' : '▾'}</button>
                <button type="button" className="project-toggle" onClick={() => props.onOpenProject?.(p.id)}>
                  <Icon name="folder" size={14} /> <span>{p.name}</span> <span className="small muted">{entries.filter((e) => e.project === p.id).length}</span>
                </button>
                <button type="button" className="link small" onClick={() => { setNaming(p.id); setName(p.name); }}>Rename</button>
                <button type="button" className="link small danger-text" title="Delete the project; its investigations go back to the history" onClick={() => { void removeProject(p.id); }}>Delete</button>
              </div>
            )}
            {!isClosed ? <ol className="history in-project">{items.length ? list(items) : <li className="small muted history-empty">Empty: move an investigation here from its menu.</li>}</ol> : null}
          </div>
        );
      })}
      {!projects.length && naming !== '' ? <p className="small muted history-empty">Group related investigations, each with its own memory.</p> : null}
      <p className="side-label">Recent</p>
      <ol className="history" aria-label={`Investigations of ${company}`}>
        {loose.length ? list(loose) : <li className="small muted history-empty">{entries.length ? 'Everything is pinned or in a project.' : 'Your investigations will appear here.'}</li>}
      </ol>
    </div>
  );
}
