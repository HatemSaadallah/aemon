import { useCallback, useEffect, useRef, useState } from 'react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { api, errorText } from './api.ts';
import { HowPage } from './pages/HowPage.tsx';
import { MathPage } from './pages/MathPage.tsx';
import { ResultsPage } from './pages/ResultsPage.tsx';
import { TrainingPage } from './pages/TrainingPage.tsx';
import { TryPage } from './pages/TryPage.tsx';
import { WorkspaceSwitcher } from './WorkspaceSwitcher.tsx';
import type { Workspace } from './types.ts';
import { loadWorkflow } from './workflow.ts';

const SECTIONS = [
  ['try', 'Try it'], ['how', 'How it works'], ['math', 'The math'], ['results', 'Results'], ['training', 'Training'],
] as const;

export type OnError = (error: unknown) => void;

async function signOut(): Promise<void> {
  try { await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' }); } finally { window.location.replace('/login'); }
}

const WS_KEY = 'lexsi.workspace';
const storedWorkspace = (): string | null => { try { return localStorage.getItem(WS_KEY); } catch { return null; } };
const storeWorkspace = (id: string): void => { try { localStorage.setItem(WS_KEY, id); } catch { /* private window: not remembered */ } };

export function App() {
  const [user, setUser] = useState('');
  const [spaces, setSpaces] = useState<Workspace[] | null>(null);
  const [ws, setWs] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  const onError = useCallback<OnError>((failure) => {
    setError(errorText(failure));
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setError(null), 6000);
  }, []);

  useEffect(() => {
    api<{ user: string }>('/api/me').then((me) => setUser(me.user)).catch(() => {});
    // The companies this account is a member of; the whole app works inside one of them at a time.
    api<{ workspaces: Workspace[] }>('/api/workspaces').then(({ workspaces }) => {
      setSpaces(workspaces);
      const stored = storedWorkspace();
      setWs(workspaces.some((w) => w.id === stored) ? stored : workspaces[0]?.id ?? null);
    }).catch(() => setSpaces([]));
    loadWorkflow().catch(() => {});  // the tree colours stages by group; every page still works without it
    return () => { if (timer.current !== null) window.clearTimeout(timer.current); };
  }, []);

  const workspace = spaces?.find((w) => w.id === ws) ?? null;
  return (
    <>
      <header className="top">
        <div className="brand">
          <h1>Strategy Lab</h1>
          {spaces && spaces.length ? <WorkspaceSwitcher spaces={spaces} current={ws} onChoose={(id) => { setWs(id); storeWorkspace(id); }} /> : null}
          <span className="tag">Development pilots, not a final test</span>
        </div>
        <nav className="tabs" aria-label="Sections">
          {SECTIONS.map(([path, label]) => <NavLink key={path} to={`/${path}`}>{label}</NavLink>)}
        </nav>
        <div className="account"><span>{user}</span><button type="button" onClick={() => { void signOut(); }}>Sign out</button></div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/try" replace />} />
          <Route path="/try" element={<section id="try">{workspace ? <TryPage key={workspace.id} workspace={workspace} onError={onError} /> : <div className="card"><p className="muted">{spaces && !spaces.length ? 'This account is not a member of any company yet: add one with python app/users.py join.' : 'Loading…'}</p></div>}</section>} />
          <Route path="/how" element={<section id="how"><HowPage onError={onError} /></section>} />
          <Route path="/math" element={<section id="math"><MathPage onError={onError} /></section>} />
          <Route path="/results/:pilot?/:arm?/:index?" element={<section id="results"><ResultsPage onError={onError} /></section>} />
          <Route path="/training" element={<section id="training"><TrainingPage onError={onError} /></section>} />
          <Route path="*" element={<Navigate to="/try" replace />} />
        </Routes>
      </main>
      {error ? <div id="error" role="alert">{error}</div> : null}
    </>
  );
}
