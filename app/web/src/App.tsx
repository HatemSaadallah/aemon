import { useCallback, useEffect, useRef, useState } from 'react';
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { api, errorText } from './api.ts';
import { Icon } from './components/Icon.tsx';
import { Logo } from './components/Logo.tsx';
import { MemoryDrawer } from './components/MemoryDrawer.tsx';
import { AboutPage } from './pages/AboutPage.tsx';
import { CompaniesPage } from './pages/CompaniesPage.tsx';
import { ComparePage } from './pages/ComparePage.tsx';
import { CompanyPage } from './pages/CompanyPage.tsx';
import { HistoryPage } from './pages/HistoryPage.tsx';
import { HomePage } from './pages/HomePage.tsx';
import { MapPage } from './pages/MapPage.tsx';
import { HowPage } from './pages/HowPage.tsx';
import { ReviewPage } from './pages/ReviewPage.tsx';
import { TeamPage } from './pages/TeamPage.tsx';
import { TryPage } from './pages/TryPage.tsx';
import { WorkspaceSwitcher } from './WorkspaceSwitcher.tsx';
import { day, text } from './labels.ts';
import type { HistoryEntry, Workspace } from './types.ts';
import { loadWorkflow } from './workflow.ts';

// The workspace: one sidebar for the whole app. The company switcher sets the context; the reasoning map is a view of
// one investigation, so it lives with each investigation rather than here.
const NAV = [['home', 'Home', 'home'], ['history', 'Investigations', 'library'], ['companies', 'Companies', 'building']] as const;
const RESEARCH = [['how', 'Methodology', 'compass'], ['about', 'About', 'eye'], ['team', 'Who we are', 'spark']] as const;

export type OnError = (error: unknown) => void;
export interface Running { id: string; workspace: string; question: string; resuming: boolean }

async function signOut(): Promise<void> {
  try { await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' }); } finally { window.location.replace('/login'); }
}

const WS_KEY = 'lexsi.workspace';
const storedWorkspace = (): string | null => { try { return localStorage.getItem(WS_KEY); } catch { return null; } };
const storeWorkspace = (id: string): void => { try { localStorage.setItem(WS_KEY, id); } catch { /* private window: not remembered */ } };
// Dark by default; light when this viewer chooses it (a per-browser convenience)
const THEME_KEY = 'lexsi.theme';
const storedTheme = (): 'light' | 'dark' => { try { return localStorage.getItem(THEME_KEY) === 'light' ? 'light' : 'dark'; } catch { return 'dark'; } };

export function App() {
  const [user, setUser] = useState('');
  const [spaces, setSpaces] = useState<Workspace[] | null>(null);
  const [ws, setWs] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [memory, setMemory] = useState<{ project: string | null; name?: string } | null>(null);
  const [running, setRunning] = useState<Running[]>([]);
  const [reviewer, setReviewer] = useState(false);
  const [done, setDone] = useState<Running | null>(null);
  const before = useRef<Running[]>([]);
  const navigate = useNavigate();
  const [theme, setTheme] = useState<'light' | 'dark'>(storedTheme);
  const [recent, setRecent] = useState<HistoryEntry[]>([]);
  const [menu, setMenu] = useState(false);  // the sidebar on phones
  const location = useLocation();
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem(THEME_KEY, theme); } catch { /* not remembered */ } }, [theme]);

  // Investigations run on the server whatever page is open. Every page knows which of yours are running, and says when
  // one finishes; the result is saved in the history either way.
  useEffect(() => {
    let alive = true;
    const poll = async (): Promise<void> => {
      try {
        const { running: now } = await api<{ running: Running[] }>('/api/try/running');
        if (!alive) return;
        const ended = before.current.filter((r) => !now.some((n) => n.id === r.id));
        if (ended.length) {
          const last = ended[ended.length - 1];
          if (last && !window.location.hash.includes(last.id)) setDone(last);  // already watching it: no notice needed
          if (!document.hasFocus()) document.title = '✓ Done · Aemon';
          window.dispatchEvent(new Event('investigation-ended'));
        }
        before.current = now;
        setRunning(now);
      } catch { /* signed out or offline: try again next time */ }
    };
    void poll();
    // With nothing running, a hidden tab or one nobody has touched for two minutes stops asking, so a hosted copy that
    // sleeps when idle is not kept awake by a forgotten tab. A running investigation is always followed.
    let touched = Date.now();
    const touch = (): void => { const away = Date.now() - touched > 120000; touched = Date.now(); if (away) void poll(); };
    const events = ['pointerdown', 'pointermove', 'keydown', 'visibilitychange'] as const;
    events.forEach((e) => document.addEventListener(e, touch, { passive: true }));
    const timer = window.setInterval(() => {
      if (before.current.length || (!document.hidden && Date.now() - touched <= 120000)) void poll();
    }, 4000);
    return () => { alive = false; window.clearInterval(timer); events.forEach((e) => document.removeEventListener(e, touch)); };
  }, []);
  const timer = useRef<number | null>(null);
  const enterWorkspace = useCallback((id: string) => { setWs(id); storeWorkspace(id); }, []);
  // Citation links (#src-<id>) would be read as routes by the hash router: open the source in place instead
  useEffect(() => {
    const onClick = (e: MouseEvent): void => {
      const a = (e.target as HTMLElement | null)?.closest?.('a[href^="#src-"]');
      if (!a) return;
      e.preventDefault();
      const id = (a.getAttribute('href') ?? '').slice(5);
      const handled = !window.dispatchEvent(new CustomEvent('open-source', { detail: id, cancelable: true }));  // the report's inspector takes it
      if (!handled) window.setTimeout(() => document.getElementById(`src-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 60);
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, []);

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
    api('/api/review').then(() => setReviewer(true)).catch(() => setReviewer(false));  // the Review page is the reviewer's only
    loadWorkflow().catch(() => {});  // the tree colours stages by group; every page still works without it
    return () => { if (timer.current !== null) window.clearTimeout(timer.current); };
  }, []);

  const workspace = spaces?.find((w) => w.id === ws) ?? null;
  const runningKey = running.map((r) => r.id).join();
  useEffect(() => {
    if (!ws) return undefined;
    let alive = true;
    const load = (): void => { api<{ entries: HistoryEntry[] }>(`/api/workspaces/${ws}/history`).then((d) => { if (alive) setRecent([...d.entries].sort((a, b) => (b.started ?? 0) - (a.started ?? 0)).slice(0, 6)); }).catch(() => {}); };
    load();
    window.addEventListener('investigation-ended', load);
    return () => { alive = false; window.removeEventListener('investigation-ended', load); };
  }, [ws, location.pathname, runningKey]);
  useEffect(() => { setMenu(false); }, [location.pathname]);
  const openId = /^\/(?:investigate|map)\/([^/]+)/.exec(location.pathname)?.[1];
  const noCompany = <div className="page-pad"><p className="muted">{spaces && !spaces.length ? 'This account is not a member of any company yet: add one with python app/users.py join.' : 'Loading…'}</p></div>;
  const investigate = workspace ? <TryPage key={workspace.id} workspace={workspace} onError={onError} running={running.filter((r) => r.workspace === workspace.id)} onMemory={(project, name) => setMemory({ project, name })} /> : noCompany;
  return (
    <>
      <div className={`shell${menu ? ' menu-open' : ''}`}>
      <header className="mbar">
        <button type="button" className="button ghost icon-only" aria-label="Menu" aria-expanded={menu} onClick={() => setMenu(!menu)}><Icon name="menu" size={18} /></button>
        <span className="brandline"><Logo size={24} /><b>Aemon</b></span>
        <NavLink to="/investigate" className="button primary small"><Icon name="plus" size={14} /> New</NavLink>
      </header>
      <aside className="side" aria-label="Workspace">
        <div className="side-brand">
          <Logo size={30} />
          <div className="wordmark"><span className="wm-name">Aemon</span><span className="tagline">weigh what is known. test what is not.</span></div>
        </div>
        {spaces && spaces.length ? <WorkspaceSwitcher spaces={spaces} current={ws} onChoose={(id) => { setWs(id); storeWorkspace(id); }} /> : null}
        <NavLink to="/investigate" end className="side-new"><Icon name="plus" size={15} /> New investigation</NavLink>
        <nav className="snav" aria-label="Sections">
          {NAV.map(([path, label, icon]) => <NavLink key={path} to={`/${path}`}><Icon name={icon} size={16} />{label}</NavLink>)}
        </nav>
        {running.length ? (
          <button type="button" className="side-running" title={running[0]?.question} onClick={() => { const r = running[0]; if (!r) return; if (r.workspace !== ws) { setWs(r.workspace); storeWorkspace(r.workspace); } navigate(`/investigate/${r.id}`); }}>
            <span className="pulse" aria-hidden="true" /><span><b>Agent working{running.length > 1 ? ` (${running.length})` : ''}</b><span className="clip">{text(running[0]?.question)}</span></span>
          </button>
        ) : null}
        {recent.length ? (
          <div className="side-group">
            <p className="side-label">Recent</p>
            <ul className="side-recent">
              {recent.map((e) => (
                <li key={e.id}><NavLink to={`/investigate/${e.id}`} className={e.id === openId ? 'active' : undefined} title={`${text(e.question)} · ${day(e.started)}`}>
                  <span className={`dot s-${e.status === 'running' ? 'running' : e.summary?.finished ? 'done' : 'partial'}`} aria-hidden="true" /><span className="clip">{text(e.question)}</span>
                </NavLink></li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="side-group">
          <p className="side-label">Research</p>
          <nav className="snav" aria-label="Research">
            {RESEARCH.map(([path, label, icon]) => <NavLink key={path} to={`/${path}`}><Icon name={icon} size={16} />{label}</NavLink>)}
          </nav>
        </div>
        <span className="grow" />
        <div className="side-foot">
          {workspace ? <button type="button" className="sbtn" onClick={() => setMemory({ project: null })}><Icon name="bulb" size={15} />Memory</button> : null}
          {reviewer ? <NavLink to="/review" className="sbtn"><Icon name="check" size={15} />Review</NavLink> : null}
          <div className="side-foot-row">
            <button type="button" className="sbtn" title={user ? `Signed in as ${user}` : undefined} onClick={() => { void signOut(); }}><Icon name="logout" size={15} />Sign out</button>
            <button type="button" className="sbtn icon-only" aria-label={theme === 'dark' ? 'Use the light theme' : 'Use the dark theme'} title={theme === 'dark' ? 'Light theme' : 'Dark theme'} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}><Icon name={theme === 'dark' ? 'sun' : 'moon'} size={15} /></button>
          </div>
        </div>
      </aside>
      {menu ? <button type="button" className="side-scrim" aria-label="Close the menu" onClick={() => setMenu(false)} /> : null}
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<section id="home">{workspace ? <HomePage key={workspace.id} workspace={workspace} running={running.filter((r) => r.workspace === workspace.id)} onError={onError} /> : noCompany}</section>} />
          <Route path="/companies" element={<section id="companies"><CompaniesPage onError={onError} /></section>} />
          <Route path="/companies/:id" element={<section id="company"><CompanyPage onWorkspace={enterWorkspace} onError={onError} /></section>} />
          <Route path="/map" element={<section id="map">{workspace ? <MapPage key={workspace.id} workspace={workspace} onError={onError} /> : noCompany}</section>} />
          <Route path="/map/:id" element={<section id="map">{workspace ? <MapPage key={workspace.id} workspace={workspace} onError={onError} /> : noCompany}</section>} />
          <Route path="/history" element={<section id="history">{workspace ? <HistoryPage key={workspace.id} workspace={workspace} onError={onError} /> : noCompany}</section>} />
          <Route path="/compare/:a/:b" element={<section id="compare">{workspace ? <ComparePage key={workspace.id} workspace={workspace} onError={onError} /> : noCompany}</section>} />
          <Route path="/investigate" element={<section id="try">{investigate}</section>} />
          <Route path="/investigate/:id" element={<section id="try">{investigate}</section>} />
          <Route path="/how" element={<section id="how"><HowPage workspace={workspace} /></section>} />
          <Route path="/about" element={<section id="about"><AboutPage /></section>} />
          <Route path="/team" element={<section id="team"><TeamPage /></section>} />
          <Route path="/review" element={<section id="review"><ReviewPage onError={onError} /></section>} />
          <Route path="*" element={<Navigate to="/home" replace />} />
        </Routes>
      </main>
      </div>
      {workspace ? <MemoryDrawer open={memory !== null} onClose={() => setMemory(null)} workspace={workspace.id} company={workspace.company} project={memory?.project ?? null} projects={memory?.project ? [{ id: memory.project, name: memory.name ?? 'this project', created: 0 }] : []} onError={onError} /> : null}
      {done ? (
        <div className="toast" role="status">
          <Icon name="check" size={16} /><span><b>Investigation finished.</b> {done.question.slice(0, 90)}</span>
          <button type="button" className="button primary small" onClick={() => { if (done.workspace !== ws) { setWs(done.workspace); storeWorkspace(done.workspace); } navigate(`/investigate/${done.id}`); setDone(null); }}>View result</button>
          <button type="button" className="button ghost small" aria-label="Dismiss" onClick={() => setDone(null)}><Icon name="cross" size={14} /></button>
        </div>
      ) : null}
      {error ? <div id="error" role="alert">{error}</div> : null}
    </>
  );
}
