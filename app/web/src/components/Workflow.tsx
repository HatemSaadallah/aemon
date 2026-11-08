import { type CSSProperties, Fragment, type ReactNode } from 'react';
import { stageName, stopName, text } from '../labels.ts';
import type { Call, RunRecord } from '../types.ts';
import { groupsOf, useWorkflow } from '../workflow.ts';
import { describe, gist } from './calls.tsx';
import { Icon, toolOf } from './Icon.tsx';

// The investigation as a workflow canvas: the question is the trigger, each call a connected step card, stages label the
// connectors, and steps about specific theories branch into one lane per theory. Model text is React text only.

type Args = Record<string, unknown>;
const obj = (value: unknown): Args => (value && typeof value === 'object' ? (value as Args) : {});

// A node is one call, or a run of identical calls in a row (a loop), shown once with a count.
export interface Node { first: [Call, number]; calls: [Call, number][] }
const sameCall = (a: Call, b: Call): boolean => a.name === b.name && JSON.stringify(a.arguments) === JSON.stringify(b.arguments) && a.accepted === b.accepted;

function nodesOf(calls: [Call, number][]): Node[] {
  const out: Node[] = [];
  for (const entry of calls) {
    const last = out[out.length - 1];
    if (last && sameCall(last.first[0], entry[0])) last.calls.push(entry);
    else out.push({ first: entry, calls: [entry] });
  }
  return out;
}

interface Block { stage: string | undefined; lanes: { theory: string; nodes: Node[] }[] | null; nodes: Node[] }

const theoryOf = (call: Call): string => text(obj(call.arguments).theory_id);
const BRANCHING = new Set(['assessment', 'challenge', 'challenge_reading', 'update']);

// Consecutive calls in one stage form a block; a branching stage whose calls name theories is split into lanes.
function blocksOf(record: RunRecord): Block[] {
  const blocks: { stage: string | undefined; calls: [Call, number][] }[] = [];
  (record.calls || []).forEach((call, i) => {
    const last = blocks[blocks.length - 1];
    if (last && last.stage === call.stage) last.calls.push([call, i + 1]);
    else blocks.push({ stage: call.stage, calls: [[call, i + 1]] });
  });
  return blocks.map((b) => {
    const named = b.calls.filter(([c]) => theoryOf(c));
    const ids = [...new Set(named.map(([c]) => theoryOf(c)))];
    if (!BRANCHING.has(b.stage ?? '') || ids.length < 2) return { stage: b.stage, lanes: null, nodes: nodesOf(b.calls) };
    return {
      stage: b.stage,
      nodes: nodesOf(b.calls.filter(([c]) => !theoryOf(c))),
      lanes: ids.map((theory) => ({ theory, nodes: nodesOf(b.calls.filter(([c]) => theoryOf(c) === theory)) })),
    };
  });
}

function title(call: Call): string {
  const a = obj(call.arguments), r = obj(call.result);
  switch (call.name) {
    case 'read_brief': return 'Read the brief';
    case 'frame_problem': return 'Frame the problem';
    case 'search_evidence': return 'Search evidence';
    case 'read_source': return 'Read a source';
    case 'challenge_theory': return `Challenge ${text(a.theory_id)}`;
    case 'add_theory': return `Add theory ${text(r.theory_id)}`.trim();
    case 'assess_evidence': return `Weigh evidence: ${text(a.direction) || '?'}`;
    case 'propose_test': return 'Propose a test';
    case 'decline_test': return 'Decline a test';
    case 'state_position': return 'State a position';
    case 'revise_theory': return `Revise ${text(a.theory_id)}: ${text(a.status)}`;
    case 'finish': return 'Finish';
    default: return text(call.name) || 'Unreadable call';
  }
}

function StepCard({ node, record, selected, onSelect, live }: { node: Node; record: RunRecord; selected: number | null; onSelect: (n: number) => void; live: boolean }) {
  const [call, n] = node.first;
  const tool = toolOf(call.name);
  const repeat = node.calls.length;
  const isSelected = node.calls.some(([, k]) => k === selected);
  const direction = call.name === 'assess_evidence' ? text(obj(call.arguments).direction) : '';
  return (
    <button type="button" className={`wf-card f-${tool.family}${call.accepted ? '' : ' refused'}${isSelected ? ' selected' : ''}${live ? ' latest' : ''}${call.prefix ? ' replayed' : ''}`}
      onClick={() => onSelect(n)} aria-pressed={isSelected}>
      <span className="wf-icon"><Icon name={tool.icon} size={18} /></span>
      <span className="wf-text">
        <span className="wf-title">{title(call)}{direction ? <span className={`wf-dir ev-${direction}`} /> : null}</span>
        <span className="wf-sub">{gist(call, record) || text(call.name)}</span>
      </span>
      <span className="wf-side">
        <span className={`wf-status ${call.accepted ? 'ok' : 'no'}`} aria-label={call.accepted ? 'accepted' : 'refused'}><Icon name={call.accepted ? 'check' : 'cross'} size={14} /></span>
        <span className="wf-n">{repeat > 1 ? `×${repeat}` : `#${n}`}</span>
      </span>
    </button>
  );
}

const Link = ({ label, group }: { label?: string; group?: string }) => (
  <div className={`wf-link${label ? ' labelled' : ''}${group ? ` g-${group}` : ''}`}>{label ? <span className="wf-stage">{label}</span> : null}</div>
);

function Column({ nodes, record, selected, onSelect, lastN, running }: { nodes: Node[]; record: RunRecord; selected: number | null; onSelect: (n: number) => void; lastN: number; running: boolean }) {
  return (
    <>
      {nodes.map((node, i) => (
        <Fragment key={node.first[1]}>
          {i ? <Link /> : null}
          <StepCard node={node} record={record} selected={selected} onSelect={onSelect} live={running && node.calls.some(([, k]) => k === lastN)} />
        </Fragment>
      ))}
    </>
  );
}

export function WorkflowCanvas({ record, question, selected, onSelect, header }: { record: RunRecord | null; question: string; selected: number | null; onSelect: (n: number) => void; header?: ReactNode }) {
  const workflow = useWorkflow();
  const groups = groupsOf(workflow);
  const running = !record || !record.stop_reason;
  const blocks = record ? blocksOf(record) : [];
  const lastN = record ? (record.calls || []).length : 0;
  return (
    <div className="wf-canvas">
      {header}
      <div className="wf-flow">
        <div className="wf-card trigger">
          <span className="wf-icon"><Icon name="zap" size={18} /></span>
          <span className="wf-text">
            <span className="wf-kicker">Trigger · Question</span>
            <span className="wf-title">{question}</span>
            {record ? <span className="wf-sub">{text(record.company)}</span> : null}
          </span>
        </div>
        {record ? blocks.map((b, i) => (
          <Fragment key={i}>
            <Link label={stageName(b.stage)} group={groups[b.stage ?? '']} />
            {b.nodes.length ? <Column nodes={b.nodes} record={record} selected={selected} onSelect={onSelect} lastN={lastN} running={running} /> : null}
            {b.lanes ? (
              <>
                {b.nodes.length ? <Link /> : null}
                <div className="wf-branch" style={{ '--lanes': b.lanes.length } as CSSProperties}>
                  {b.lanes.map((lane) => (
                    <div className="wf-lane" key={lane.theory}>
                      <span className="wf-lane-label"><Icon name="bulb" size={12} />{lane.theory}</span>
                      <Column nodes={lane.nodes} record={record} selected={selected} onSelect={onSelect} lastN={lastN} running={running} />
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </Fragment>
        )) : null}
        <Link />
        {running ? (
          <div className="wf-card ghost"><span className="wf-icon"><span className="dots"><span /><span /><span /></span></span><span className="wf-text"><span className="wf-title">{record ? 'Thinking about the next step' : 'Starting the investigation'}</span><span className="wf-sub">Each call is checked by the harness before it runs</span></span></div>
        ) : record?.final ? (
          <div className="wf-card outcome good"><span className="wf-icon"><Icon name="spark" size={18} /></span><span className="wf-text"><span className="wf-kicker">Outcome · Recommendation</span><span className="wf-title">{text(record.final.recommendation)}</span>{record.final.next_action ? <span className="wf-sub">Next: {text(record.final.next_action)}</span> : null}</span></div>
        ) : (
          <div className="wf-card outcome bad"><span className="wf-icon"><Icon name="cross" size={18} /></span><span className="wf-text"><span className="wf-kicker">Outcome · Stopped</span><span className="wf-title">{stopName(record?.stop_reason)}</span><span className="wf-sub">{record?.position ? `Position so far: ${text(record.position.recommendation)}` : 'No recommendation was reached.'}</span></span></div>
        )}
      </div>
    </div>
  );
}

// What one step did, for the side panel.
export function StepDetail({ record, n }: { record: RunRecord; n: number }) {
  const call = record.calls?.[n - 1];
  if (!call) return null;
  const tool = toolOf(call.name);
  const [head, ...body] = describe(call, record);
  const reason = call.result && call.result.error;
  const args = Object.entries(obj(call.arguments));
  return (
    <div className={`inspector-step f-${tool.family}`}>
      <div className="inspector-head">
        <span className="wf-icon"><Icon name={tool.icon} size={18} /></span>
        <div>
          <p className="inspector-kicker">Step {n} · {stageName(call.stage)}</p>
          <h3>{head}</h3>
        </div>
      </div>
      <p className={`inspector-verdict ${call.accepted ? 'ok' : 'no'}`}><Icon name={call.accepted ? 'check' : 'cross'} size={14} />{call.accepted ? 'Accepted by the harness' : `Refused: ${text(reason)}`}</p>
      {body.length ? <div className="inspector-body">{body}</div> : null}
      {args.length ? (
        <details className="inspector-args">
          <summary>Arguments the model sent to <code className="tool-name">{text(call.name)}</code></summary>
          <dl>{args.map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{text(v)}</dd></Fragment>)}</dl>
        </details>
      ) : null}
    </div>
  );
}
