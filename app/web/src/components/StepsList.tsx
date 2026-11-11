import { useState } from 'react';
import { STEPS, cut, kindOf, stepOf, text } from '../labels.ts';
import type { Call, RunRecord } from '../types.ts';
import { activity, describe } from './calls.tsx';
import { Icon } from './Icon.tsx';

// What the assistant did, in the seven steps a manager would recognise. Each step opens to its actions in plain words,
// and each action opens to exactly what was read, quoted or decided. Actions the checker did not accept are marked and
// explained: they changed nothing, and the assistant tried again.

type Args = Record<string, unknown>;
const obj = (v: unknown): Args => (v && typeof v === 'object' ? (v as Args) : {});

function why(call: Call): string {
  const error = text(obj(call.result).error);
  return error ? error.replace(/\b(harness|tool|stage)\b/gi, (w) => ({ harness: 'checker', tool: 'action', stage: 'step' } as Record<string, string>)[w.toLowerCase()] ?? w) : 'It broke one of the investigation rules.';
}

function summary(calls: [Call, number][]): string {
  const count = (name: string): number => calls.filter(([c]) => c.name === name && c.accepted).length;
  const parts: string[] = [];
  const searches = count('search_evidence') + count('challenge_theory'), reads = count('read_source'), weighed = count('assess_evidence'), ideas = count('add_theory');
  if (searches) parts.push(`${searches} search${searches === 1 ? '' : 'es'}`);
  if (reads) parts.push(`${reads} source${reads === 1 ? '' : 's'} read`);
  if (ideas) parts.push(`${ideas} explanation${ideas === 1 ? '' : 's'}`);
  if (weighed) parts.push(`${weighed} source${weighed === 1 ? '' : 's'} weighed`);
  const refused = calls.filter(([c]) => !c.accepted).length;
  if (refused) parts.push(`${refused} not accepted`);
  return parts.join(' · ') || `${calls.length} action${calls.length === 1 ? '' : 's'}`;
}

function Action({ call, n, record }: { call: Call; n: number; record: RunRecord }) {
  const [open, setOpen] = useState(false);
  const a = obj(call.arguments);
  const source = call.name === 'read_source' ? record.sources?.[text(a.id)] : undefined;
  const parts = describe(call, record).slice(1).filter(Boolean);
  return (
    <li className={`action${call.accepted ? '' : ' refused'}`}>
      <button type="button" className="action-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="action-n">{n}</span>
        <span className="action-text">{cut(activity(call, record))}</span>
        <span className="action-chev" aria-hidden="true">{open ? '▾' : '▸'}</span>
      </button>
      {open ? (
        <div className="action-body">
          {!call.accepted ? <p className="refused-why"><Icon name="cross" size={13} /> Not accepted by the checker, so it changed nothing. Why: {cut(why(call))}</p> : null}
          {source ? (
            <>
              <p className="small"><span className={`kind k-${source.class}`}>{kindOf(source.class)}</span> {source.date ? <span className="muted">{text(source.date)}</span> : null}</p>
              {source.excerpt ? <p className="src-quote">“{text(source.excerpt)}”</p> : null}
              {source.url ? <p className="small"><a href={source.url} target="_blank" rel="noreferrer noopener">Open the source</a></p> : null}
            </>
          ) : null}
          {call.name === 'search_evidence' || call.name === 'challenge_theory' ? (
            Array.isArray(obj(call.result).results) && (obj(call.result).results as unknown[]).length
              ? <ul className="found">{(obj(call.result).results as { title?: unknown; id?: unknown }[]).map((r, i) => <li key={i}>{text(r.title || r.id)}</li>)}</ul>
              : call.accepted ? <p className="small muted">Nothing new found.</p> : null
          ) : null}
          {call.name !== 'read_source' && call.name !== 'search_evidence' && call.name !== 'challenge_theory' ? <div className="action-detail">{parts.length ? parts : <p className="small muted">No further detail.</p>}</div> : null}
        </div>
      ) : null}
    </li>
  );
}

export function StepsList({ record, live = false }: { record: RunRecord; live?: boolean }) {
  const calls = (record.calls || []).map((c, i) => [c, i + 1] as [Call, number]);
  const groups = STEPS.map((s, i) => ({ step: s, index: i, calls: calls.filter(([c]) => stepOf(c.stage) === i) }));
  const last = calls[calls.length - 1];
  const current = last ? stepOf(last[0].stage) : 0;
  const [open, setOpen] = useState<Set<number>>(() => new Set(live ? [current] : []));
  const toggle = (i: number): void => setOpen((o) => { const n = new Set(o); if (n.has(i)) n.delete(i); else n.add(i); return n; });
  const isOpen = (i: number): boolean => open.has(i) || (live && i === current);
  return (
    <ol className="steps-list">
      {groups.map(({ step, index, calls: inStep }) => {
        const state = inStep.length ? (live && index === current ? 'now' : 'done') : 'todo';
        return (
          <li key={step.label} className={`step-group ${state}`}>
            <button type="button" className="step-head" aria-expanded={isOpen(index)} disabled={!inStep.length} onClick={() => toggle(index)}>
              <span className="step-dot" aria-hidden="true">{state === 'done' ? <Icon name="check" size={12} /> : index + 1}</span>
              <span className="step-title"><b>{step.label}</b><span className="muted small">{inStep.length ? summary(inStep) : live ? 'Not started yet' : 'Not reached'}</span></span>
              {inStep.length ? <span className="action-chev" aria-hidden="true">{isOpen(index) ? '▾' : '▸'}</span> : null}
            </button>
            {isOpen(index) && inStep.length ? <ol className="actions">{inStep.map(([c, n]) => <Action key={n} call={c} n={n} record={record} />)}</ol> : null}
          </li>
        );
      })}
    </ol>
  );
}
