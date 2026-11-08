import { useCallback, useEffect, useRef, useState } from 'react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { api, errorText } from './api.ts';
import { Icon } from './components/Icon.tsx';
import { MemoryDrawer } from './components/MemoryDrawer.tsx';
import { AboutPage } from './pages/AboutPage.tsx';
import { HowPage } from './pages/HowPage.tsx';
import { MindMapPage } from './pages/MindMapPage.tsx';
import { TryPage } from './pages/TryPage.tsx';
import { WorkspaceSwitcher } from './WorkspaceSwitcher.tsx';
import type { Workspace } from './types.ts';
import { loadWorkflow } from './workflow.ts';

const SECTIONS = [['investigate', 'Investigate'], ['map', 'Mind map'], ['how', 'How it works'], ['about', 'Who we are']] as const;

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
  const [memory, setMemory] = useState<{ project: string | null; name?: string } | null>(null);
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
  const noCompany = <div className="page-pad"><p className="muted">{spaces && !spaces.length ? 'This account is not a member of any company yet: add one with python app/users.py join.' : 'Loading…'}</p></div>;
  const investigate = workspace ? <TryPage key={workspace.id} workspace={workspace} onError={onError} onMemory={(project, name) => setMemory({ project, name })} /> : noCompany;
  return (
    <>
      <header className="top">
        <div className="brand">
          <span className="logo" aria-hidden="true">S</span>
          <h1>Strategy Lab</h1>
          {spaces && spaces.length ? <WorkspaceSwitcher spaces={spaces} current={ws} onChoose={(id) => { setWs(id); storeWorkspace(id); }} /> : null}
        </div>
        <nav className="tabs" aria-label="Sections">
          {SECTIONS.map(([path, label]) => <NavLink key={path} to={`/${path}`}>{label}</NavLink>)}
        </nav>
        <div className="account">
          {workspace ? <button type="button" className="button ghost" onClick={() => setMemory({ project: null })}><Icon name="bulb" size={15} /> Memory</button> : null}
          <span className="user">{user}</span>
          <button type="button" className="button ghost" onClick={() => { void signOut(); }}>Sign out</button>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/investigate" replace />} />
          <Route path="/investigate" element={<section id="try">{investigate}</section>} />
          <Route path="/investigate/:id" element={<section id="try">{investigate}</section>} />
          <Route path="/map" element={<section id="map">{workspace ? <MindMapPage key={workspace.id} workspace={workspace} onError={onError} /> : noCompany}</section>} />
          <Route path="/how" element={<section id="how"><HowPage /></section>} />
          <Route path="/about" element={<section id="about"><AboutPage /></section>} />
          <Route path="*" element={<Navigate to="/investigate" replace />} />
        </Routes>
      </main>
      {workspace ? <MemoryDrawer open={memory !== null} onClose={() => setMemory(null)} workspace={workspace.id} company={workspace.company} project={memory?.project ?? null} projects={memory?.project ? [{ id: memory.project, name: memory.name ?? 'this project', created: 0 }] : []} onError={onError} /> : null}
      {error ? <div id="error" role="alert">{error}</div> : null}
    </>
  );
}
