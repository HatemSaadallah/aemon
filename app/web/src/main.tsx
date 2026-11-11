import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import { App } from './App.tsx';
import { Login } from './pages/Login.tsx';
import './style.css';
import './ui.css';

// Old links were #results/pilot1/trained/3; the router reads #/results/pilot1/trained/3.
// On load the address is rewritten before the router starts; later, location.replace fires the event the router follows.
const legacy = (): string | null => (window.location.hash && !window.location.hash.startsWith('#/') ? `#/${window.location.hash.slice(1)}` : null);
const first = legacy();
if (first) window.history.replaceState(null, '', first);
window.addEventListener('hashchange', () => { const next = legacy(); if (next) window.location.replace(next); });

const root = document.getElementById('root');
if (!root) throw new Error('The page has no #root element');
const signIn = window.location.pathname === '/login';
if (signIn) document.body.classList.add('login-page');
document.title = signIn ? 'Sign in · Aemon' : 'Aemon';

createRoot(root).render(
  <StrictMode>
    {signIn ? <Login /> : <HashRouter><App /></HashRouter>}
  </StrictMode>,
);
