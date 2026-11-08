import { type CSSProperties, useState } from 'react';
import { shortName, stageName, stopName, text } from '../labels.ts';
import type { RunRecord } from '../types.ts';
import { useWorkflow } from '../workflow.ts';
import { Icon, toolOf } from './Icon.tsx';
import { gist, plural } from './calls.tsx';
import { StepDetail, WorkflowCanvas } from './Workflow.tsx';

// The investigation drawn as a picture: where it went through the stages, every call in order, the theories with the
// evidence weighed for and against each, and the steps themselves. Model text is only ever rendered as React text.

type Args = Record<string, unknown>;
const obj = (value: unknown): Args => (value && typeof value === 'object' ? (value as Args) : {});

const BELIEFS = ['very unlikely', 'unlikely', 'uncertain', 'likely', 'very likely'];

// The stage the run is in now, or stopped in.
const currentStage = (record: RunRecord): string | undefined => record.stopping_point?.stage_at_stop ?? record.calls?.[record.calls.length - 1]?.stage;

export function JourneyMap({ record, onPick }: { record: RunRecord; onPick: (stage: string) => void }) {
  const workflow = useWorkflow();
  const stages = workflow ? workflow.stages : [];
  const calls = record.calls || [];
  const count = (stage: string): [number, number] => {
    const own = calls.filter((c) => c.stage === stage);
    return [own.length, own.filter((c) => !c.accepted).length];
  };
  const running = !record.stop_reason;
  const now = currentStage(record);
  const reached = stages.map((s) => count(s.stage)[0] > 0);
  const furthest = reached.lastIndexOf(true);
  const done = Boolean(record.final);
  const fill = stages.length > 1 ? (done ? 1 : Math.max(0, furthest) / (stages.length - 1)) : 0;
  if (!stages.length) return null;
  return (
    <div className="journey" style={{ '--fill': fill } as CSSProperties}>
      <div className="journey-track" aria-hidden="true"><div className="journey-fill" /></div>
      <ol className="journey-stages" aria-label="Stages of the investigation">
        {stages.map((s, i) => {
          const [n, refused] = count(s.stage);
          const isNow = s.stage === now && !done;
          const state = n ? (isNow && running ? 'now' : isNow ? 'stopped' : 'visited') : 'ahead';
          return (
            <li key={s.stage} className={`journey-stop g-${s.group} ${state}${s.optional ? ' optional' : ''}`}>
              <button type="button" disabled={!n} onClick={() => onPick(s.stage)}
                title={`${stageName(s.stage)}: ${n ? plural(n, 'call') : 'not reached'}${refused ? `, ${refused} refused` : ''}${s.optional ? ' (optional)' : ''}`}>
                <span className="journey-dot">
                  {state === 'visited' ? <Icon name="check" size={14} /> : state === 'stopped' ? <Icon name="cross" size={14} /> : <span className="journey-i">{i + 1}</span>}
                  {refused ? <span className="journey-alert" aria-label={`${refused} refused`}>{refused}</span> : null}
                </span>
                <span className="journey-name">{shortName(s.stage)}</span>
                <span className="journey-n">{n ? plural(n, 'call') : ' '}</span>
              </button>
            </li>
          );
        })}
        <li className={`journey-stop end ${done ? 'finished' : record.stop_reason ? 'halted' : 'pending'}`}>
          <span className="journey-dot"><Icon name={done ? 'spark' : record.stop_reason ? 'cross' : 'dot'} size={14} /></span>
          <span className="journey-name">{done ? 'Finished' : record.stop_reason ? stopName(record.stop_reason) : 'Finish'}</span>
          <span className="journey-n">&nbsp;</span>
        </li>
      </ol>
    </div>
  );
}

function CallStrip({ record, onPick }: { record: RunRecord; onPick: (n: number) => void }) {
  const calls = record.calls || [];
  const running = !record.stop_reason;
  if (!calls.length) return null;
  return (
    <div className="strip-wrap">
      <div className="strip" role="list" aria-label="Every call in order">
        {calls.map((call, i) => {
          const tool = toolOf(call.name);
          return (
            <button key={i} type="button" role="listitem" className={`cell f-${tool.family}${call.accepted ? '' : ' refused'}${call.prefix ? ' replayed' : ''}`}
              title={`${i + 1}. ${text(call.name)}${call.accepted ? '' : ' (refused)'}: ${gist(call, record)}`} onClick={() => onPick(i + 1)}>
              <Icon name={call.accepted ? tool.icon : 'cross'} size={12} />
            </button>
          );
        })}
        {running ? <span className="cell thinking" aria-label="Thinking"><span /><span /><span /></span> : null}
      </div>
      <div className="strip-key small muted">
        {[['problem', 'Framing'], ['evidence', 'Evidence'], ['challenge', 'Challenge'], ['theory', 'Theories'], ['assess', 'Weighing'], ['experiment', 'Test'], ['revision', 'Revision'], ['conclusion', 'Conclusion']].map(([f, label]) => (
          <span key={f} className="strip-key-item"><span className={`key-dot f-${f}`} />{label}</span>
        ))}
        <span className="strip-key-item"><span className="key-dot refused" />Refused</span>
      </div>
    </div>
  );
}

interface Weighed { direction: string; quote: string; source: string; n: number }

function theoriesOf(record: RunRecord): { id: string; claim: string; status: string; weighed: Weighed[]; belief: string | undefined; favoured: boolean }[] {
  const calls = record.calls || [];
  const ids = Object.keys(record.theories || {});
  for (const c of calls) {
    const id = text(obj(c.result).theory_id);
    if (c.accepted && c.name === 'add_theory' && id && !ids.includes(id)) ids.push(id);
  }
  const beliefs = (obj(record.final).beliefs ?? record.position?.beliefs ?? {}) as Record<string, unknown>;
  const favoured = text(record.final?.favoured_theory ?? record.position?.favoured_theory);
  return ids.map((id) => {
    const theory = record.theories?.[id] ?? {};
    const added = calls.find((c) => c.accepted && c.name === 'add_theory' && text(obj(c.result).theory_id) === id);
    const weighed = calls.flatMap((c, i): Weighed[] => {
      const a = obj(c.arguments);
      if (!c.accepted || c.name !== 'assess_evidence' || text(a.theory_id) !== id) return [];
      const source = record.sources?.[text(a.evidence_id)];
      return [{ direction: text(a.direction), quote: text(a.quote), source: source ? text(source.title) : text(a.evidence_id), n: i + 1 }];
    });
    const belief = beliefs[id];
    return { id, claim: text(theory.claim ?? obj(added?.arguments).claim), status: text(theory.status) || 'open', weighed, belief: typeof belief === 'string' ? belief : undefined, favoured: id === favoured };
  });
}

export function TheoryBoard({ record, onPick }: { record: RunRecord; onPick: (n: number) => void }) {
  const theories = theoriesOf(record);
  if (!theories.length) return null;
  return (
    <div className="board" aria-label="Theories and the evidence weighed for each">
      {theories.map((t) => {
        const tally = (d: string): number => t.weighed.filter((w) => w.direction === d).length;
        const [sup, con, neu] = [tally('supports'), tally('contradicts'), tally('neutral')];
        const level = t.belief ? BELIEFS.indexOf(t.belief) : -1;
        return (
          <article key={t.id} className={`theory s-${t.status}${t.favoured ? ' favoured' : ''}`}>
            <header className="theory-head">
              <span className="theory-id"><Icon name="bulb" size={14} />{t.id}</span>
              {t.favoured ? <span className="theory-fav"><Icon name="spark" size={12} /> favoured</span> : null}
              <span className={`theory-status s-${t.status}`}>{t.status}</span>
            </header>
            <p className="theory-claim">{t.claim}</p>
            <div className="evidence-bar" role="img" aria-label={`${sup} supporting, ${con} contradicting, ${neu} neutral`}>
              {t.weighed.length ? t.weighed.map((w) => (
                <button key={w.n} type="button" className={`ev ev-${w.direction}`} title={`${w.direction}: “${w.quote}” (${w.source})`} onClick={() => onPick(w.n)} />
              )) : <span className="ev-none small muted">No evidence weighed yet</span>}
            </div>
            <div className="theory-foot small">
              <span className="tally"><span className="key-dot ev-supports" />{sup} for</span>
              <span className="tally"><span className="key-dot ev-contradicts" />{con} against</span>
              <span className="tally"><span className="key-dot ev-neutral" />{neu} neutral</span>
            </div>
            {level >= 0 ? (
              <div className="belief" aria-label={`Belief: ${t.belief ?? ''}`}>
                <span className="small muted">Belief</span>
                <span className="belief-meter">{BELIEFS.map((b, i) => <span key={b} className={i <= level ? 'on' : ''} />)}</span>
                <span className="small">{t.belief}</span>
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

export function AgentTrace({ record, runKey }: { record: RunRecord; runKey: string; live?: boolean }) {
  const [step, setStep] = useState<number | null>(null);
  void runKey;
  const pickStage = (stage: string): void => {
    const first = (record.calls || []).findIndex((c) => c.stage === stage);
    if (first >= 0) setStep(first + 1);
  };
  return (
    <div className="trace">
      <JourneyMap record={record} onPick={pickStage} />
      <CallStrip record={record} onPick={setStep} />
      <div className="trace-grid">
        <WorkflowCanvas record={record} question={text(record.question)} selected={step} onSelect={setStep} />
        <div className="trace-side">
          {step ? <div className="panel-section"><div className="row spread"><p className="side-label">Selected step</p><button type="button" className="quiet-button" onClick={() => setStep(null)}>Close</button></div><StepDetail record={record} n={step} /></div> : <p className="small muted">Click a step on the canvas to see what the model sent and what the harness returned.</p>}
          <TheoryBoard record={record} onPick={setStep} />
        </div>
      </div>
    </div>
  );
}
