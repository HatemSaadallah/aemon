import { type FormEvent, useRef, useState } from 'react';
import { errorText } from '../api.ts';
import { Logo } from '../components/Logo.tsx';

// Sign in, then go to aemon. The session cookie is HttpOnly, so this page never sees it.
export function Login() {
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const passwordRef = useRef<HTMLInputElement>(null);

  const submit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const response = await fetch('/api/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin',
        body: JSON.stringify({ name: name.trim(), password }),
      });
      const data: unknown = await response.json().catch(() => ({}));
      const detail = data && typeof data === 'object' && 'detail' in data ? (data as { detail: unknown }).detail : undefined;
      if (!response.ok) throw new Error(typeof detail === 'string' ? detail : 'Sign-in failed');
      window.location.replace('/');
    } catch (failure: unknown) {
      setError(errorText(failure));
      setPassword('');
      passwordRef.current?.focus();
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
        <p className="muted">Sign in to investigate a company with the agent.</p>
        <label htmlFor="name">Name</label>
        <input id="name" name="name" autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={64} autoFocus
          value={name} onChange={(e) => setName(e.target.value)} />
        <label htmlFor="password">Password</label>
        <input id="password" name="password" type="password" autoComplete="current-password" required maxLength={256} ref={passwordRef}
          value={password} onChange={(e) => setPassword(e.target.value)} />
        {error ? <p className="small bad-text" role="alert">{error}</p> : null}
        <button type="submit" className="primary" disabled={busy}>Sign in</button>
        <p className="muted small">Accounts are created on this computer with <code>python app/users.py add NAME</code>.</p>
      </form>
    </main>
  );
}
