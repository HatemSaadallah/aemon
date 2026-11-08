import { useEffect, useState } from 'react';
import { STEPS, cut, stepOf, text } from '../labels.ts';
import type { RunRecord } from '../types.ts';
import { activity } from './calls.tsx';
import { Icon } from './Icon.tsx';

// An investigation while it runs: which of the seven steps it is on, how long it has taken, the last few things it
// did in plain words, the explanations so far, and a Stop button (docs/DESIGN_RESEARCH.md, section 4b).

export function Progress({ question, record, started, onStop, stopping }: { question: string; record: RunRecord | null; started: number; onStop: () => void; stopping: boolean }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(t); }, []);
  const calls = record?.calls ?? [];
  const last = calls[calls.length - 1];
  const current = last ? stepOf(last.stage) : 0;
  const seconds = Math.max(0, Math.round((now - started) / 1000));
  const elapsed = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  const recent = calls.slice(-5).reverse();
  const theories = Object.entries(record?.theories ?? {});
  return (
    <article className="result running">
      <header className="result-head">
        <p className="eyebrow">Investigating</p>
        <h1>{text(question)}</h1>
        <div className="result-actions"><span className="grow" /><button type="button" className="button" disabled={stopping} onClick={onStop}><Icon name="cross" size={14} /> {stopping ? 'Stopping…' : 'Stop'}</button></div>
      </header>
      <section className="progress-card" aria-live="polite">
        <div className="progress-top">
          <p className="progress-title">Step {current + 1} of {STEPS.length} · {STEPS[current]?.label}</p>
          <p className="muted small">{elapsed} elapsed · usually 2 to 4 minutes</p>
        </div>
        <ol className="stepper">
          {STEPS.map((s, i) => <li key={s.label} className={i < current ? 'done' : i === current ? 'now' : ''}><span className="dot" aria-hidden="true">{i < current ? <Icon name="check" size={11} /> : i + 1}</span><span className="lbl">{s.label}</span></li>)}
        </ol>
      </section>
      <section className="block">
        <h2>What it is doing</h2>
        {recent.length ? <ul className="feed">{recent.map((c, i) => <li key={calls.length - i} className={c.accepted ? '' : 'muted'}>{cut(activity(c, record as RunRecord))}</li>)}</ul> : <p className="muted">Starting up…</p>}
      </section>
      {theories.length ? (
        <section className="block">
          <h2>Explanations so far</h2>
          <div className="explanations">{theories.map(([tid, t], i) => <div key={tid} className="explanation"><div className="exp-head static"><span className="exp-name">Explanation {i + 1}</span><span className="exp-claim">{cut(t.claim)}</span></div></div>)}</div>
        </section>
      ) : null}
    </article>
  );
}
