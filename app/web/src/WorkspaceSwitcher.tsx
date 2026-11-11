import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from './components/Icon.tsx';
import { shortCompany } from './labels.ts';
import type { Workspace } from './types.ts';

// The company workspace the whole app is working in, like a team switcher. One company: just its name.
export function WorkspaceSwitcher({ spaces, current, onChoose }: { spaces: Workspace[]; current: string | null; onChoose: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const active = spaces.find((w) => w.id === current) ?? spaces[0];
  useEffect(() => {
    if (!open) return undefined;
    const close = (e: MouseEvent | KeyboardEvent): void => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', close); };
  }, [open]);
  if (!active) return null;
  const mark = (w: Workspace) => <span className="ws-mark" aria-hidden="true">{shortCompany(w.company).charAt(0)}</span>;
  if (spaces.length === 1) return <Link to="/companies" className="ws-current single">{mark(active)}{shortCompany(active.company)}</Link>;
  return (
    <div className="ws-switcher" ref={box}>
      <button type="button" className="ws-current" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(!open)}>
        {mark(active)}{shortCompany(active.company)}<span className="ws-chev" aria-hidden="true">▾</span>
      </button>
      {open ? (
        <ul className="ws-menu" role="listbox" aria-label="Switch company workspace">
          <li className="ws-menu-label">Your companies</li>
          {spaces.map((w) => (
            <li key={w.id} role="option" aria-selected={w.id === active.id}>
              <button type="button" onClick={() => { onChoose(w.id); setOpen(false); }}>
                {mark(w)}<span>{shortCompany(w.company)}</span>{w.id === active.id ? <Icon name="check" size={14} /> : null}
              </button>
            </li>
          ))}
          <li className="ws-menu-foot"><Link to="/companies" onClick={() => setOpen(false)}><Icon name="list" size={14} /> Browse all companies</Link></li>
        </ul>
      ) : null}
    </div>
  );
}
