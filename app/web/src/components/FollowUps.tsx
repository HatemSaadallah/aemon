import { useEffect, useState } from 'react';
import { api, postJSON } from '../api.ts';
import { asksOnline, cut, text } from '../labels.ts';
import type { FollowUpItem, Source } from '../types.ts';
import { type Attached, AttachmentPicker } from './Attachments.tsx';
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
  onReinvestigate: ((context: string, attachments: string[]) => void) | null;
  busy: boolean;
}

const REMEMBER = /^\s*remember(?:\s+that)?\s*[:,-]?\s+/i;

export function FollowUps({ workspace, id, project, initial, suggestions, sources, number, onError, onReinvestigate, busy }: Props) {
  const [files, setFiles] = useState<Attached[]>([]);
  const [items, setItems] = useState<FollowUpItem[]>(initial);
  const [input, setInput] = useState('');
  const [note, setNote] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const answering = items.some((f) => f.status === 'answering');

  useEffect(() => { setItems(initial); }, [initial]);
  useEffect(() => {  // poll while an answer is being written
    if (!answering) return undefined;
    const timer = window.setTimeout(() => {
      api<{ followups: FollowUpItem[] }>(`/api/workspaces/${workspace}/history/${id}/followups`).then((d) => setItems(d.followups)).catch(onError);
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [answering, items, workspace, id, onError]);

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

  const newest = [...items].reverse();  // the latest answer sits right under the box
  const shown = showAll ? newest : newest.slice(0, 2);
  const unasked = suggestions.filter((q) => !items.some((f) => f.question === q));
  return (
    <section className="followups-top" id="followups" aria-label="Follow-up questions">
      <form className="ask-box top" id="ask" onSubmit={(e) => { e.preventDefault(); void ask(input); }}>
        <Icon name="spark" size={18} />
        <textarea id="ask-input" rows={1} maxLength={500} value={input} placeholder="Ask a follow-up about this investigation, or start with “Remember:” to save a note" aria-label="Ask a follow-up"
          onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void ask(input); } }} />
        <button type="submit" className="button primary" disabled={answering || !input.trim()} title="Answer from this investigation's sources">Ask</button>
        {onReinvestigate ? (
          <button type="button" className="button" disabled={busy || (!input.trim() && !files.length)} title="Run the investigation again with this information, your files and links, or a web search"
            onClick={() => { onReinvestigate(input.trim(), files.map((f) => f.id)); setInput(''); setFiles([]); }}>Re-investigate with this</button>
        ) : null}
      </form>
      {onReinvestigate ? <AttachmentPicker workspace={workspace} items={files} onChange={setFiles} onError={onError} disabled={busy} /> : null}
      {asksOnline(input) ? <p className="small online-hint"><Icon name="search" size={12} /> To search online, use Re-investigate with this: answers only use this investigation's sources.</p> : null}
      {unasked.length && items.length < 3 ? (
        <div className="suggestions">{unasked.map((q) => <button key={q} type="button" className="chip-button" disabled={answering} onClick={() => { void ask(q); }}>{q}</button>)}</div>
      ) : null}
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
      {shown.length ? (
        <div className="thread">
          {shown.map((f, i) => (
            <div key={f.id} className={`turn${i === 0 ? ' latest' : ''}`}>
              <p className="q">{text(f.question)}</p>
              {f.status === 'answering' ? <p className="a thinking"><span className="dots" aria-hidden="true"><i /><i /><i /></span> Reading this investigation's sources…</p> : (
                <div className={`a${f.status === 'not_in_record' ? ' not-covered' : ''}${f.status === 'failed' ? ' failed' : ''}`}>
                  <p>{cut(f.answer)}</p>
                  {f.sources.length ? <p className="based">Based on: {f.sources.map((src) => <a key={src} href={`#src-${src}`} className="cite" title={text(sources[src]?.title)}>[{number[src] ?? '?'}] {text(sources[src]?.title).slice(0, 48)}</a>)}</p> : null}
                  {f.status === 'not_in_record' ? <p className="muted small">This investigation's sources do not cover that. A new investigation on it would.</p> : null}
                </div>
              )}
            </div>
          ))}
          {newest.length > 2 ? <button type="button" className="link small" onClick={() => setShowAll(!showAll)}>{showAll ? 'Show fewer' : `Show ${newest.length - 2} earlier question${newest.length - 2 === 1 ? '' : 's'}`}</button> : null}
        </div>
      ) : null}
      <p className="muted small">Answers use only this investigation's sources. Check the quotes before acting.</p>
    </section>
  );
}
