import { useRef, useState } from 'react';
import { errorText, postJSON } from '../api.ts';
import { text } from '../labels.ts';
import { Icon } from './Icon.tsx';

// Files and links the person adds to an investigation. Each is read once on the server and split into passages the
// agent can search and quote, labelled "Your document": the person's material, not checked by an analyst.

export interface Attached { id: string; name: string; kind: 'file' | 'link'; url?: string; passages: number; words: number }

const ACCEPT = '.pdf,.docx,.txt,.md,.csv,.html,.htm,.json';

const toBase64 = (file: File): Promise<string> => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(String(reader.result).split(',', 2)[1] ?? '');
  reader.onerror = () => reject(reader.error ?? new Error('could not read the file'));
  reader.readAsDataURL(file);
});

export function AttachmentPicker({ workspace, items, onChange, onError, disabled = false }: { workspace: string; items: Attached[]; onChange: (items: Attached[]) => void; onError: (e: unknown) => void; disabled?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [linking, setLinking] = useState(false);
  const [url, setUrl] = useState('');

  const upload = async (files: FileList | null): Promise<void> => {
    if (!files?.length) return;
    let next = items;
    for (const file of Array.from(files)) {
      setBusy(`Reading ${file.name}…`);
      try {
        if (file.size > 15_000_000) throw new Error(`${file.name} is larger than 15 MB`);
        const added = await postJSON<Attached>(`/api/workspaces/${workspace}/attachments`, { name: file.name, data_base64: await toBase64(file) });
        next = [...next, added];
        onChange(next);
      } catch (error: unknown) { onError(new Error(`${file.name}: ${errorText(error)}`)); }
    }
    setBusy(null);
    if (input.current) input.current.value = '';
  };
  const addLink = async (): Promise<void> => {
    const link = url.trim();
    if (!link) return;
    setBusy('Reading the page…');
    try {
      const added = await postJSON<Attached>(`/api/workspaces/${workspace}/attachments`, { url: /^https?:\/\//.test(link) ? link : `https://${link}` });
      onChange([...items, added]);
      setUrl(''); setLinking(false);
    } catch (error: unknown) { onError(error); } finally { setBusy(null); }
  };
  const remove = (a: Attached): void => {
    onChange(items.filter((x) => x.id !== a.id));  // detached only: a run that used it can still continue
  };

  return (
    <div className="attach">
      <div className="attach-row">
        <button type="button" className="chip-button" disabled={disabled || Boolean(busy)} onClick={() => input.current?.click()}
          title="PDF, Word, text, Markdown, CSV or HTML, up to 15 MB. The agent can search and quote it."><Icon name="doc" size={13} /> Attach file</button>
        <input ref={input} type="file" multiple accept={ACCEPT} hidden onChange={(e) => { void upload(e.target.files); }} />
        <button type="button" className="chip-button" disabled={disabled || Boolean(busy)} aria-expanded={linking} onClick={() => setLinking(!linking)}><Icon name="plus" size={13} /> Add link</button>
        {busy ? <span className="small muted">{busy}</span> : null}
      </div>
      {linking ? (
        <form className="link-form" onSubmit={(e) => { e.preventDefault(); void addLink(); }}>
          <input autoFocus value={url} placeholder="https://… a page the agent should read" aria-label="Link to add" onChange={(e) => setUrl(e.target.value)} />
          <button type="submit" className="button small primary" disabled={!url.trim() || Boolean(busy)}>Add</button>
          <button type="button" className="button small ghost" onClick={() => { setLinking(false); setUrl(''); }}>Cancel</button>
        </form>
      ) : null}
      {items.length ? (
        <ul className="attached">
          {items.map((a) => (
            <li key={a.id} title={`${a.words.toLocaleString()} words in ${a.passages} passages${a.url ? ` · ${a.url}` : ''}`}>
              <Icon name={a.kind === 'link' ? 'search' : 'doc'} size={12} /><span>{text(a.name)}</span>
              <button type="button" aria-label={`Remove ${a.name}`} onClick={() => remove(a)}>×</button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
