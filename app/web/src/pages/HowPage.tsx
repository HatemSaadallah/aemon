import { useEffect, useState } from 'react';
import type { OnError } from '../App.tsx';
import { Chip } from '../Chip.tsx';
import { sentence, shortName, stageName } from '../labels.ts';
import type { Workflow } from '../types.ts';
import { loadWorkflow } from '../workflow.ts';

type Stage = Workflow['stages'][number];

const GROUPS: Record<string, [label: string, note: string]> = {
  problem: ['Problem', 'Understand the question before looking for answers.'],
  theory: ['Theories and evidence', 'Rival causal explanations, each weighed against quoted evidence and challenged.'],
  experiment: ['Test and position', 'Design a test where the theories predict different results, or say why one is not worth it, then commit to a view.'],
  revision: ['New evidence, a what-if', 'Only in cases with a simulated result. It arrives after the position is stated, and the update loops into concluding. Without one, the agent goes from its position straight to concluding.'],
  conclusion: ['Conclusion', 'Recommend, with uncertainty and what would change the view.'],
};
const OPTIONAL: Record<string, string> = { challenge_reading: 'Only when the challenge found something not yet read.', new_evidence: 'Only in a what-if case.', update: 'Only in a what-if case.' };
const isLater = (s: Stage): boolean => s.group === 'experiment' || s.group === 'conclusion';

// Tools that every later stage keeps open, so the agent can always look further before moving on.
function lookFurther(stages: Stage[]): string[] {
  const later = stages.filter((s) => isLater(s) && !s.optional);
  const first = later[0];
  return first ? first.tools.filter((t) => later.every((s) => s.tools.includes(t))) : [];
}

function StageBox({ stage, number, further, tools }: { stage: Stage; number: number; further: string[]; tools: Record<string, string> }) {
  const [shown, setShown] = useState<string | null>(null);
  const own = stage.tools.filter((t) => !further.includes(t) || !isLater(stage));
  const kept = stage.tools.filter((t) => !own.includes(t));
  const chip = (name: string, kind = '') => (
    <button key={name} type="button" className={`tool${kind ? ` ${kind}` : ''}`} title={sentence(tools[name])} aria-expanded={shown === name}
      onClick={() => setShown((current) => (current === name ? null : name))}>{name}</button>
  );
  return (
    <li className={`stage-box${stage.optional ? ' optional' : ''}`}>
      <div className="stage-head">
        <span className="stage-n">{number}</span><strong>{stageName(stage.stage)}</strong><code className="muted small">{stage.stage}</code>
        {stage.optional ? <Chip kind="quiet">sometimes</Chip> : null}
      </div>
      {stage.optional && OPTIONAL[stage.stage] ? <p className="muted small">{OPTIONAL[stage.stage]}</p> : null}
      <div className="tools">{own.map((t) => chip(t))}</div>
      {kept.length ? <div className="tools kept"><span className="muted small">↺ still open:</span>{kept.map((t) => chip(t, 'further'))}</div> : null}
      <p className="tool-desc" aria-live="polite" hidden={!shown}>
        {shown ? <><code>{shown}</code> {sentence(tools[shown]) || 'No description.'}</> : null}
      </p>
    </li>
  );
}

export function HowPage({ onError }: { onError: OnError }) {
  const [w, setW] = useState<Workflow | null>(null);
  useEffect(() => { loadWorkflow().then(setW).catch(onError); }, [onError]);
  if (!w) return <div className="card"><p className="muted">Loading the controller…</p></div>;

  const further = lookFurther(w.stages);
  const opens: Record<string, string[]> = {};
  w.stages.forEach((s) => s.tools.forEach((t) => { (opens[t] ??= []).push(s.stage); }));
  const groups: { group: string; stages: [Stage, number][] }[] = [];
  w.stages.forEach((s, i) => {
    const last = groups[groups.length - 1];
    if (last && last.group === s.group) last.stages.push([s, i]); else groups.push({ group: s.group, stages: [[s, i]] });
  });

  return (
    <>
      <div className="card">
        <h2>How the agent works</h2>
        <p className="lead">A stage controller decides which tools are open at each step and what must happen before the investigation moves on. The model decides everything else: what to search, which theories to hold, what to test and what the evidence means. Every arm, trained or not, runs under this same controller.</p>
        <p className="muted small">Drawn from the controller’s own table, which a test checks against the code. Select a tool to see what it does. Dashed stages happen only in some cases.</p>
      </div>
      <div className="card">
        <div className="flow">
          {groups.map((g, gi) => {
            const [label, note] = GROUPS[g.group] ?? [g.group, ''];
            const optional = g.stages.every(([s]) => s.optional);
            return (
              <section key={gi} className={`group g-${g.group}${optional ? ' optional' : ''}`}>
                <header className="group-head"><h3>{label}</h3><p className="muted small">{note}</p></header>
                <ol className="flow-stages">
                  {g.stages.flatMap(([s, i]) => {
                    const box = <StageBox key={s.stage} stage={s} number={i + 1} further={further} tools={w.tools} />;
                    return s.stage === 'conclude' ? [box] : [box,
                      <li key={`${s.stage}-arrow`} className="arrow"><span className="arrow-line" aria-hidden="true" /><span className="arrow-text">moves on {s.moves_on}</span></li>];
                  })}
                </ol>
              </section>
            );
          })}
          <div className="flow-end">✓ Done: the investigation is finished</div>
        </div>
      </div>
      <div className="card">
        <h3>Every tool</h3>
        {further.length ? <p className="muted small">From the test onward, {further.join(', ')} stay open in every stage, so the agent can keep investigating before it moves on.</p> : null}
        <dl className="glossary">
          {Object.entries(w.tools).map(([name, description]) => [
            <dt key={`${name}-t`}><code>{name}</code></dt>,
            <dd key={`${name}-d`}>{sentence(description)}<span className="muted small"> Open in: {(opens[name] ?? []).map(shortName).join(', ') || 'none'}.</span></dd>,
          ])}
        </dl>
      </div>
    </>
  );
}
