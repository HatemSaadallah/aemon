import { type FormEvent, useRef, useState } from 'react';
import { errorText } from '../api.ts';
import { Logo } from '../components/Logo.tsx';

// Sign in by name alone, then go to aemon. A new name opens a new account; the same name opens it again later.
// The session cookie is HttpOnly, so this page never sees it.
export function Login() {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const nameRef = useRef<HTMLInputElement>(null);

  const submit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const response = await fetch('/api/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin',
        body: JSON.stringify({ name: name.trim().toLowerCase() }),
      });
      const data: unknown = await response.json().catch(() => ({}));
      const detail = data && typeof data === 'object' && 'detail' in data ? (data as { detail: unknown }).detail : undefined;
      if (!response.ok) throw new Error(typeof detail === 'string' ? detail : 'Sign-in failed');
      window.location.replace('/');
    } catch (failure: unknown) {
      setError(errorText(failure));
      nameRef.current?.focus();
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login-main">
      <form className="card login-card" noValidate onSubmit={(e) => { void submit(e); }}>
        <Logo size={44} className="logo-mark big" />
        <h1>aemon</h1>
        <p className="tagline">weigh what is known. test what is not.</p>
        <p className="muted">Pick a username to investigate a company with the agent.</p>
        <label htmlFor="name">Username</label>
        <input id="name" name="name" autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={32} autoFocus
          ref={nameRef} placeholder="e.g. ada" value={name} onChange={(e) => setName(e.target.value)} />
        {error ? <p className="small bad-text" role="alert">{error}</p> : null}
        <button type="submit" className="primary" disabled={busy || !name.trim()}>Continue</button>
        <p className="muted small">A new username opens a new account; use the same one to come back to your investigations.
          There is no password, so anyone who types your username can open your account.</p>
      </form>
    </main>
  );
}
