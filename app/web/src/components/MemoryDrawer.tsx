import { useCallback, useEffect, useState } from 'react';
import { api, postJSON, sendJSON } from '../api.ts';
import { day, text } from '../labels.ts';
import type { MemoryNote, MemoryState, Project } from '../types.ts';
import { Icon } from './Icon.tsx';

// Memory, as in ChatGPT: notes the assistant is given at the start of each new investigation and follow-up. Notes about
// you apply everywhere, a company's notes in that company, a project's notes in that project. Nothing is saved without
// the person asking, and "saved" is shown only after the server confirms.

type Scope = 'global' | 'company' | 'project';

function Note({ note, onSave, onDelete }: { note: MemoryNote; onSave: (text: string) => Promise<void>; onDelete: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(note.text);
  const [confirm, setConfirm] = useState(false);
  return (
    <li className="note">
      {editing ? (
        <form onSubmit={(e) => { e.preventDefault(); void onSave(value).then(() => setEditing(false)); }}>
          <textarea rows={2} maxLength={400} value={value} onChange={(e) => setValue(e.target.value)} aria-label="Edit note" autoFocus />
          <div className="row"><button type="submit" className="button primary small">Save</button><button type="button" className="button ghost small" onClick={() => { setValue(note.text); setEditing(false); }}>Cancel</button></div>
        </form>
      ) : (
        <>
          <p>{text(note.text)}</p>
          <p className="note-meta">Added {day(note.created)}
            <button type="button" className="link" onClick={() => setEditing(true)}>Edit</button>
            {confirm ? <><span>Delete?</span><button type="button" className="link danger-text" onClick={() => { void onDelete(); }}>Yes</button><button type="button" className="link" onClick={() => setConfirm(false)}>No</button></> : <button type="button" className="link" onClick={() => setConfirm(true)}>Delete</button>}
          </p>
        </>
      )}
    </li>
  );
}

function Section({ title, hint, notes, onAdd, onSave, onDelete, full }: { title: string; hint: string; notes: MemoryNote[]; onAdd: (t: string) => Promise<void>; onSave: (n: MemoryNote, t: string) => Promise<void>; onDelete: (n: MemoryNote) => Promise<void>; full: boolean }) {
  const [value, setValue] = useState('');
  return (
    <section className="mem-section">
      <h3>{title}</h3>
      {notes.length ? <ul className="notes">{notes.map((n) => <Note key={n.id} note={n} onSave={(t) => onSave(n, t)} onDelete={() => onDelete(n)} />)}</ul> : <p className="muted small">{hint}</p>}
      <form className="add-note" onSubmit={(e) => { e.preventDefault(); if (value.trim()) void onAdd(value.trim()).then(() => setValue('')); }}>
        <input value={value} maxLength={400} disabled={full} placeholder={full ? 'Memory is full: remove a note first' : 'Add a note'} aria-label={`Add a note: ${title}`} onChange={(e) => setValue(e.target.value)} />
        <button type="submit" className="button small" disabled={full || !value.trim()}><Icon name="plus" size={13} /> Add</button>
      </form>
    </section>
  );
}

export function MemoryDrawer({ open, onClose, workspace, company, project, projects, onError }: { open: boolean; onClose: () => void; workspace: string; company: string; project: string | null; projects: Project[]; onError: (e: unknown) => void }) {
  const [state, setState] = useState<MemoryState | null>(null);
  const load = useCallback(async () => {
    const q = new URLSearchParams({ workspace, ...(project ? { project } : {}) });
    setState(await api<MemoryState>(`/api/memory?${q.toString()}`));
  }, [workspace, project]);
  useEffect(() => { if (open) load().catch(onError); }, [open, load, onError]);
  useEffect(() => {
    const refresh = (): void => { if (open) load().catch(onError); };
    const esc = (e: KeyboardEvent): void => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('memory-changed', refresh);
    document.addEventListener('keydown', esc);
    return () => { window.removeEventListener('memory-changed', refresh); document.removeEventListener('keydown', esc); };
  }, [open, load, onError, onClose]);
  if (!open) return null;
  const act = async (fn: () => Promise<unknown>): Promise<void> => { try { await fn(); await load(); window.dispatchEvent(new Event('memory-counted')); } catch (e: unknown) { onError(e); } };
  const add = (scope: Scope) => (t: string): Promise<void> => act(() => postJSON('/api/memory', { text: t, ...(scope === 'company' ? { workspace } : scope === 'project' ? { workspace, project } : {}) }));
  const save = (n: MemoryNote, t: string): Promise<void> => act(() => sendJSON(`/api/memory/${n.id}`, 'PATCH', { text: t }));
  const remove = (n: MemoryNote): Promise<void> => act(() => sendJSON(`/api/memory/${n.id}`, 'DELETE'));
  const count = state ? state.global.length + state.company.length + state.project.length : 0;
  const full = state ? count >= state.limit : false;
  const projectName = projects.find((p) => p.id === project)?.name;
  return (
    <div className="drawer-wrap" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Memory">
        <header className="drawer-head">
          <h2><Icon name="bulb" size={18} /> Memory</h2>
          <button type="button" className="button ghost" onClick={onClose} aria-label="Close memory"><Icon name="cross" size={16} /></button>
        </header>
        {state ? (
          <>
            <label className="switch">
              <input type="checkbox" checked={state.enabled} onChange={(e) => { void act(() => sendJSON('/api/memory/settings', 'PATCH', { enabled: e.target.checked })); }} />
              <span className="track" aria-hidden="true" />
              <span><b>Use memory</b><br /><span className="muted small">When on, these notes are given to the assistant at the start of each new investigation and follow-up. They are your context, never evidence.</span></span>
            </label>
            <p className="muted small">{count} of {state.limit} notes used.</p>
            <Section title="About you" hint="Nothing yet. Add what applies to every question, e.g. “I lead product strategy and decide on budgets under €50k.”" notes={state.global} onAdd={add('global')} onSave={save} onDelete={remove} full={full} />
            <Section title={`About ${company}`} hint="Nothing yet, e.g. “We sell only through distributors in the EU” or “Test budgets rarely exceed €20k.”" notes={state.company} onAdd={add('company')} onSave={save} onDelete={remove} full={full} />
            {project ? <Section title={`Project: ${projectName ?? ''}`} hint="Nothing yet. Notes here apply only to investigations in this project." notes={state.project} onAdd={add('project')} onSave={save} onDelete={remove} full={full} /> : <p className="muted small">Open a project to see and add its own notes.</p>}
            <p className="muted small">Tip: in a follow-up, start with “Remember:” to save a note.</p>
          </>
        ) : <p className="muted">Loading…</p>}
      </aside>
    </div>
  );
}
