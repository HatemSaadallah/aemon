import { useCallback, useEffect, useRef, useState } from 'react';
import { STEPS, cut, stepOf, text } from '../labels.ts';
import type { RunRecord } from '../types.ts';
import { activity } from './calls.tsx';
import { Icon } from './Icon.tsx';
import { StepsList } from './StepsList.tsx';
import { StepDetail, WorkflowCanvas } from './Workflow.tsx';
import { MapLayer } from './reasoning/MapLayer.tsx';
import { ReasoningMap } from './reasoning/ReasoningMap.tsx';

// An investigation while the agent works: what it is doing right now, the seven steps, live counts against its budget,
// the explanations as they form with the evidence weighed for and against each, and the live flow of every action,
// as a branching diagram or as a list. A Stop button ends it; leaving the page does not.

const VERB: Record<string, string> = {
  read_brief: 'Reading the question and the budget', frame_problem: 'Defining the decision and its alternatives', search_evidence: 'Searching the sources',
  read_source: 'Reading a source', add_theory: 'Writing down a possible explanation', assess_evidence: 'Weighing a source against an explanation',
  challenge_theory: 'Looking for evidence against its favourite', propose_test: 'Designing a market test', decline_test: 'Deciding whether a test is worth it',
  state_position: 'Forming a view', revise_theory: 'Updating its view after new evidence', finish: 'Writing the recommendation',
};
const NEXT: Record<number, string> = {
  0: 'Next it will define the decision and its alternatives.', 1: 'It searches and reads sources before explaining anything.',
  2: 'It writes rival explanations of why customers would buy.', 3: 'It weighs each source for or against each explanation.',
  4: 'It looks hardest for evidence against its favourite.', 5: 'It designs a small test, or says why one is not worth it.', 6: 'It forms a view and writes the recommendation.',
};

export function Progress({ question, record, started, onStop, stopping, searchBudget, wrapping = false }: { question: string; record: RunRecord | null; started: number; onStop: () => void; stopping: boolean; searchBudget?: number; wrapping?: boolean }) {
  const [now, setNow] = useState(Date.now());
  const [view, setView] = useState<'flow' | 'steps' | 'map'>('map');
  const [picked, setPicked] = useState<number | null>(null);
  const [full, setFull] = useState(false);
  const closeFull = useCallback((): void => setFull(false), []);
  const canvas = useRef<HTMLDivElement>(null);
  useEffect(() => { const t = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(t); }, []);
  const calls = record?.calls ?? [];
  const last = calls[calls.length - 1];
  const current = last ? stepOf(last.stage) : 0;
  useEffect(() => {  // follow the newest action in the diagram, unless a step is open
    if (view === 'flow' && picked === null && canvas.current) canvas.current.scrollTo({ top: canvas.current.scrollHeight, behavior: 'smooth' });
  }, [calls.length, view, picked]);
  const seconds = Math.max(0, Math.round((now - started) / 1000));
  const elapsed = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  const ok = calls.filter((c) => c.accepted);
  const searches = ok.filter((c) => c.name === 'search_evidence').length;
  const reads = new Set(ok.filter((c) => c.name === 'read_source').map((c) => text((c.arguments as Record<string, unknown>)?.id))).size;
  const theories = Object.entries(record?.theories ?? {});
  const weighed = ok.filter((c) => c.name === 'assess_evidence');
  const tally = (tid: string, dir: string): number => weighed.filter((c) => { const a = c.arguments as Record<string, unknown>; return a?.theory_id === tid && a?.direction === dir; }).length;
  const corrected = calls.length - ok.length;
  const told = Number((calls[0]?.result as Record<string, unknown> | undefined)?.search_budget);  // the budget the agent was given, from its brief
  const budget = told || searchBudget || 8;
  const doing = wrapping ? 'It stopped early: writing a draft recommendation from what it found' : last ? (last.accepted ? VERB[last.name] ?? 'Working' : 'Correcting a step the checker did not accept') : 'Starting up';

  return (
    <article className="result running">
      <header className="result-head">
        <p className="eyebrow">Investigating</p>
        <h1>{text(question)}</h1>
      </header>
      <section className="agent-card" aria-live="polite">
        <div className="agent-top">
          <span className="agent-orb" aria-hidden="true"><span /><span /><span /></span>
          <div className="agent-now">
            <p className="agent-label">The agent is working · step {current + 1} of {STEPS.length}</p>
            <p className="agent-doing">{doing}…</p>
            {last && last.accepted ? <p className="agent-detail">{cut(activity(last, record as RunRecord))}</p> : null}
          </div>
          <div className="agent-side">
            <p className="agent-time">{elapsed}</p>
            <button type="button" className="button small" disabled={stopping} onClick={onStop}><Icon name="cross" size={13} /> {stopping ? 'Stopping…' : 'Stop'}</button>
          </div>
        </div>
        <ol className="stepper">
          {STEPS.map((s, i) => <li key={s.label} className={i < current ? 'done' : i === current ? 'now' : ''}><span className="dot" aria-hidden="true">{i < current ? <Icon name="check" size={11} /> : i + 1}</span><span className="lbl">{s.label}</span></li>)}
        </ol>
        <p className="agent-next muted small">{NEXT[current]} It keeps running if you leave this page; a notice appears when it finishes.</p>
      </section>

      <section className="live-stats" aria-label="So far">
        <div className="stat"><span>Searches</span><b>{searches}<i>/ {budget}</i></b><div className="meter"><span style={{ width: `${Math.min(searches / budget, 1) * 100}%` }} /></div></div>
        <div className="stat"><span>Sources read</span><b>{reads}</b></div>
        <div className="stat"><span>Explanations</span><b>{theories.length}</b></div>
        <div className="stat"><span>Evidence weighed</span><b>{weighed.length}</b></div>
        <div className="stat"><span>Steps</span><b>{calls.length}</b>{corrected ? <em>{corrected} corrected by the checker</em> : null}</div>
      </section>

      {theories.length ? (
        <section className="block">
          <h2>Explanations taking shape</h2>
          <div className="explanations">{theories.map(([tid, t], i) => {
            const plus = tally(tid, 'supports'), minus = tally(tid, 'contradicts'), none = tally(tid, 'neutral');
            return (
              <div key={tid} className="explanation live">
                <div className="exp-head static">
                  <span className="exp-name">Explanation {i + 1}{record?.position?.favoured_theory === tid ? <span className="lead-chip">★ Leading</span> : null}</span>
                  <span className="exp-claim">{cut(t.claim)}</span>
                  <span className="tally"><span className={plus ? 't-for' : 'muted'}>{plus ? `+${plus}` : '0'} for</span><span className={minus ? 't-against' : 'muted'}>{minus ? `−${minus}` : '0'} against</span><span className="muted">{none} no bearing</span></span>
                </div>
              </div>
            );
          })}</div>
        </section>
      ) : null}

      {record && calls.length ? (
        <section className="block live-flow">
          <div className="row spread">
            <h2>The agent's flow, live</h2>
            <div className="depth" role="tablist" aria-label="View">
              <button type="button" role="tab" aria-checked={view === 'map'} onClick={() => setView('map')}>Reasoning map</button>
              <button type="button" role="tab" aria-checked={view === 'flow'} onClick={() => setView('flow')}>Action flow</button>
              <button type="button" role="tab" aria-checked={view === 'steps'} onClick={() => setView('steps')}>Step list</button>
            </div>
            {view === 'map' ? <button type="button" className="button small" onClick={() => setFull(true)}>Full page</button> : null}
          </div>
          {view === 'flow' ? (
            <>
              <p className="muted small">Each card is one action. Weighing evidence branches into one lane per explanation. Click a card to see what it did.</p>
              <div className="how-canvas live-canvas" ref={canvas}><WorkflowCanvas record={record} question={question} selected={picked} onSelect={setPicked} /></div>
              {picked ? <div className="step-detail"><div className="row spread"><b>Action {picked}</b><button type="button" className="button ghost small" onClick={() => setPicked(null)}>Close</button></div><StepDetail record={record} n={picked} /></div> : null}
            </>
          ) : view === 'map' ? (full ? <MapLayer title={text(question)} back="Back to progress" onClose={closeFull}><ReasoningMap record={record} live /></MapLayer> : <ReasoningMap record={record} live />) : <StepsList record={record} live />}
        </section>
      ) : null}
    </article>
  );
}
