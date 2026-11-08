import { useEffect, useRef, useState } from 'react';
import { api, postJSON } from '../api.ts';
import { cut, text } from '../labels.ts';
import type { FollowUpItem, Source } from '../types.ts';
import { Icon } from './Icon.tsx';

// Follow-up questions on a finished investigation. Answers come from that investigation's sources only and say which
// ones; "Remember: …" saves a memory note instead, after the person chooses where it applies.

interface Props {
  workspace: string;
  id: string;
  project: string | null;
  initial: FollowUpItem[];
  suggestions: string[];
  sources: Record<string, Source>;
  number: Record<string, number>;
  onError: (error: unknown) => void;
}

const REMEMBER = /^\s*remember(?:\s+that)?\s*[:,-]?\s+/i;

export function FollowUps({ workspace, id, project, initial, suggestions, sources, number, onError }: Props) {
  const [items, setItems] = useState<FollowUpItem[]>(initial);
  const [input, setInput] = useState('');
  const [note, setNote] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const answering = items.some((f) => f.status === 'answering');

  useEffect(() => { setItems(initial); }, [initial]);
  useEffect(() => {  // poll while an answer is being written
    if (!answering) return undefined;
    const timer = window.setTimeout(() => {
      api<{ followups: FollowUpItem[] }>(`/api/workspaces/${workspace}/history/${id}/followups`).then((d) => setItems(d.followups)).catch(onError);
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [answering, items, workspace, id, onError]);
  const seen = useRef(initial.length);
  useEffect(() => {  // follow a new question or answer, but never jump to the bottom when the page opens
    if (items.length > seen.current) end.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    seen.current = items.length;
  }, [items.length]);

  const ask = async (question: string): Promise<void> => {
    const q = question.trim();
    if (!q || answering) return;
    if (REMEMBER.test(q)) { setNote(q.replace(REMEMBER, '')); setInput(''); return; }
    try {
      const item = await postJSON<FollowUpItem>(`/api/workspaces/${workspace}/history/${id}/followups`, { question: q });
      setItems((all) => [...all, item]);
      setInput('');
    } catch (error: unknown) { onError(error); }
  };
  const remember = async (scope: 'global' | 'company' | 'project'): Promise<void> => {
    if (!note) return;
    try {
      await postJSON('/api/memory', { text: note, ...(scope === 'company' ? { workspace } : scope === 'project' && project ? { workspace, project } : {}) });
      setSaved(scope === 'global' ? 'everywhere' : scope === 'company' ? 'for this company' : 'for this project');
      setNote(null);
      window.dispatchEvent(new Event('memory-changed'));
    } catch (error: unknown) { onError(error); }
  };

  return (
    <section className="block followups" aria-label="Follow-up questions">
      <h2>Ask a follow-up</h2>
      <div className="thread">
        {items.map((f) => (
          <div key={f.id} className="turn">
            <p className="q">{text(f.question)}</p>
            {f.status === 'answering' ? <p className="a thinking"><span className="dots" aria-hidden="true"><i /><i /><i /></span> Reading this investigation's sources…</p> : (
              <div className={`a${f.status === 'not_in_record' ? ' not-covered' : ''}${f.status === 'failed' ? ' failed' : ''}`}>
                <p>{cut(f.answer)}</p>
                {f.sources.length ? <p className="based">Based on: {f.sources.map((s) => <a key={s} href={`#src-${s}`} className="cite" title={text(sources[s]?.title)}>[{number[s] ?? '?'}] {text(sources[s]?.title).slice(0, 48)}</a>)}</p> : null}
                {f.status === 'not_in_record' ? <p className="muted small">This investigation's sources do not cover that. A new investigation on it would.</p> : null}
              </div>
            )}
          </div>
        ))}
        <div ref={end} />
      </div>
      {note !== null ? (
        <div className="remember-card" role="status">
          <p><Icon name="bulb" size={15} /> Remember this for future investigations? <b>“{note}”</b></p>
          <div className="row">
            <button type="button" className="button primary" onClick={() => { void remember('company'); }}>For this company</button>
            <button type="button" className="button" onClick={() => { void remember('global'); }}>Everywhere</button>
            {project ? <button type="button" className="button" onClick={() => { void remember('project'); }}>For this project</button> : null}
            <button type="button" className="button ghost" onClick={() => setNote(null)}>No</button>
          </div>
        </div>
      ) : null}
      {saved ? <p className="saved-note" role="status"><Icon name="check" size={14} /> Saved to memory {saved}. It will be used in new investigations.</p> : null}
      {!items.length && suggestions.length ? (
        <div className="suggestions">{suggestions.map((s) => <button key={s} type="button" className="chip-button" disabled={answering} onClick={() => { void ask(s); }}>{s}</button>)}</div>
      ) : null}
      <form className="ask-box" onSubmit={(e) => { e.preventDefault(); void ask(input); }}>
        <textarea rows={1} maxLength={500} value={input} placeholder="Ask about this investigation, or start with “Remember:” to save a note" aria-label="Ask a follow-up"
          onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void ask(input); } }} />
        <button type="submit" className="button primary" disabled={answering || !input.trim()}>Ask</button>
      </form>
      <p className="muted small">Answers use only this investigation's sources. Check the quotes before acting.</p>
    </section>
  );
}
