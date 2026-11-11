import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api.ts';
import type { Running } from '../App.tsx';
import { Icon } from '../components/Icon.tsx';
import { cut, day, shortCompany, text } from '../labels.ts';
import type { CompanyProfile, HistoryEntry, TryStatus, Workspace } from '../types.ts';
import { CompanyHero } from '../components/company.tsx';

// Home: the company's research at a glance, from its saved investigations only. Every number is counted from the
// history the server returns; nothing here is estimated or illustrative.

export function outcomeOf(e: HistoryEntry): { kind: 'good' | 'warn' | 'bad' | 'run'; label: string } {
  if (e.status === 'running') return { kind: 'run', label: 'Running' };
  if (e.status === 'interrupted') return { kind: 'bad', label: 'Interrupted' };
  if (e.status === 'failed') return { kind: 'bad', label: 'Could not finish' };
  if (e.status === 'stopped') return { kind: 'bad', label: 'Stopped by you' };
  if (e.summary?.finished) return { kind: 'good', label: 'Finished' };  // finished, not verified: the report carries its own checks
  if (e.summary?.draft) return { kind: 'warn', label: 'Draft answer' };
  return { kind: 'warn', label: 'Stopped early' };
}

export function HomePage({ workspace: w, running, onError }: { workspace: Workspace; running: Running[]; onError: (e: unknown) => void }) {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<HistoryEntry[] | null>(null);
  const [status, setStatus] = useState<TryStatus | null>(null);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  useEffect(() => {
    let alive = true;
    api<{ entries: HistoryEntry[] }>(`/api/workspaces/${w.id}/history`).then((d) => { if (alive) setEntries(d.entries); }).catch((e) => { if (alive) { setEntries([]); onError(e); } });
    api<TryStatus>('/api/try').then((d) => { if (alive) setStatus(d); }).catch(() => {});
    api<CompanyProfile>(`/api/companies/${w.id}`).then((d) => { if (alive) setProfile(d); }).catch(() => {});
    return () => { alive = false; };
  }, [w.id, running.length, onError]);

  const list = [...(entries ?? [])].sort((a, b) => (b.started ?? 0) - (a.started ?? 0));
  const count = (k: string) => list.filter((e) => outcomeOf(e).kind === k).length;
  const company = shortCompany(w.company);
  const model = (
    <span className={`model-pill ${status?.model_ready ? 'ok' : 'off'}`} title={status?.model ? text(status.model.label) : undefined}>
      <span className="dot" aria-hidden="true" />{status ? (status.model_ready ? 'Agent ready · Strategy Agent V1 (frozen)' : 'Model server offline: investigations cannot start') : 'Checking the agent…'}
    </span>
  );
  return (
    <div className="pg home2">
      {profile ? (
        <CompanyHero p={profile} onInvestigate={() => navigate('/investigate')}
          actions={<><Link to={`/companies/${w.id}`} className="button ghost">Company profile</Link><Link to={`/companies/${w.id}`} state={{ tab: 'evidence' }} className="button ghost">Sources</Link></>}>
          {model}
        </CompanyHero>
      ) : (
        <header className="pg-head">
          <div>
            <span className="kicker accent">{text(w.company)}</span>
            <h1 className="pg-title">Strategic research for {company}</h1>
            <p className="pg-sub">Ask a strategic question. The agent reads {company}'s source library, compares rival explanations against quoted evidence and proposes a test before a big commitment.</p>
          </div>
          <div className="row"><button type="button" className="button primary big" onClick={() => navigate('/investigate')}><Icon name="plus" size={16} /> New investigation</button>{model}</div>
        </header>
      )}

      {running.length ? (
        <section className="panel pad running-strip" aria-label="Running now">
          <span className="pulse" aria-hidden="true" />
          <div><b>Running now</b>{running.map((r) => <Link key={r.id} to={`/investigate/${r.id}`} className="clip">{text(r.question)}</Link>)}</div>
          <span className="muted small">{running[0]?.resuming ? 'Resuming after a restart' : 'The agent is working; you can leave this page.'}</span>
        </section>
      ) : null}

      <section className="kstats" aria-label="This company's research, counted from saved records">
        <div className="kstat"><b>{entries ? list.length : '–'}</b><span>investigations</span></div>
        <div className="kstat"><b>{entries ? count('good') : '–'}</b><span>finished</span></div>
        <div className="kstat"><b>{entries ? count('warn') + count('bad') : '–'}</b><span>stopped early or interrupted</span></div>
        <div className="kstat"><b>{profile ? profile.sources : '–'}</b><span>source records{profile ? ` · ${profile.independent_sources} independent` : ''}</span></div>
        <div className="kstat"><b className="kstat-date">{list[0] ? day(list[0].started) : '–'}</b><span>last investigation</span></div>
      </section>

      <div className="home2-grid">
        <section className="sec" aria-label="Recent investigations">
          <div className="sec-head"><h2 className="display">Recent investigations</h2>{list.length ? <Link to="/history">All {list.length} investigations →</Link> : null}</div>
          {entries === null ? <div className="inv-rows">{[0, 1, 2].map((i) => <div key={i} className="skel" style={{ height: 84 }} />)}</div> : !list.length ? (
            <div className="empty-box"><b>Nothing investigated yet</b><span>Start with one of the suggested questions, or ask your own.</span><button type="button" className="button primary" onClick={() => navigate('/investigate')}>Start an investigation</button></div>
          ) : (
            <ul className="inv-rows">{list.slice(0, 5).map((e) => <InvestigationRow key={e.id} e={e} scenario={w.scenarios.some((c) => c.case === e.case)} />)}</ul>
          )}
        </section>

        <aside className="home2-side">
          <section className="sec">
            <div className="sec-head"><h2 className="display">Explore a question</h2></div>
            <p className="muted small">Possible questions to investigate, written for this company. They are starting points, not findings.</p>
            <ul className="q-cards">{w.examples.slice(0, 4).map((q) => (
              <li key={q}><button type="button" className="q-card" onClick={() => navigate('/investigate', { state: { question: q } })}>
                <span>{text(q)}</span><Icon name="arrow" size={15} />
              </button></li>
            ))}</ul>
          </section>
          <section className="panel pad trust" aria-label="How to read results">
            <h2 className="kicker"><Icon name="flag" size={13} /> How to read results</h2>
            <ul>
              <li><b>A hypothesis to test, not advice.</b> Recommendations come from a small fine-tuned research model (Tiny Aya, 3B).</li>
              <li><b>Traceable is not the same as true.</b> Quotes are checked word for word against their source; the agent's reading of them is not.</li>
              <li><b>Numbers need checking.</b> On our frozen tests, 21% and 31% of finished answers used a number found in no source read. Every report flags its own.</li>
              <li><b>Unfinished stays unfinished.</b> Runs that stop early are shown as stopped, never as finished.</li>
            </ul>
            <Link to="/how" className="small">How the agent works and how it was evaluated →</Link>
          </section>
        </aside>
      </div>
    </div>
  );
}

// One investigation as a scannable row: status and date, the question, a short preview of where it ended, quick links
export function InvestigationRow({ e, company, scenario }: { e: HistoryEntry; company?: string; scenario?: boolean }) {
  const o = outcomeOf(e);
  const preview = e.summary?.recommendation ? cut(e.summary.recommendation) : e.summary?.position ? `Interim view: ${cut(e.summary.position)}` : null;
  return (
    <li className="inv-row2">
      <Link to={`/investigate/${e.id}`} className="inv-hit" aria-label={`Open: ${text(e.question)}`} />
      <div className="inv-top">
        <span className={`chip ${o.kind === 'good' ? 'good' : o.kind === 'run' ? 'accent' : o.kind === 'warn' ? 'warn' : 'bad'}`}>{o.label}</span>
        {scenario ? <span className="chip sim">Simulated scenario</span> : null}
        <span className="muted small">{company ? `${company} · ` : ''}{day(e.started)}</span>
        <span className="grow" />
        <span className="inv-links">
          <Link to={`/investigate/${e.id}`} className="button ghost small">Report</Link>
          {o.kind !== 'run' ? <Link to={`/map/${e.id}`} className="button ghost small"><Icon name="map" size={13} /> Map</Link> : null}
        </span>
      </div>
      <p className="inv-q2">{text(e.question)}</p>
      {preview ? <p className="inv-prev"><span className="muted">{e.summary?.recommendation ? 'Recommends: ' : ''}</span>{preview}</p> : null}
    </li>
  );
}
