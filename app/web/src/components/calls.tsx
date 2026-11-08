import type { ReactNode } from 'react';
import { text } from '../labels.ts';
import type { Call, RunRecord } from '../types.ts';

// What each call did, in words, shared by the tree and the visual trace. Model text is untrusted: React text only.

type Args = Record<string, unknown>;
const obj = (value: unknown): Args => (value && typeof value === 'object' ? (value as Args) : {});
const str = (value: unknown): string => text(value);

function SourceTitle({ record, id }: { record: RunRecord; id: unknown }) {
  const source = record.sources?.[str(id)];
  if (!source) return <>{text(id)}</>;
  return source.url ? <a href={source.url} target="_blank" rel="noreferrer noopener">{text(source.title)}</a> : <>{text(source.title)}</>;
}

function Quote({ body, record, id }: { body: unknown; record: RunRecord; id: unknown }) {
  return (
    <figure className="quote">
      <blockquote>{text(body)}</blockquote>
      <figcaption><SourceTitle record={record} id={id} /></figcaption>
    </figure>
  );
}

// What the model did, in words. Arguments come from the model, so every field is read defensively.
export function describe(call: Call, record: RunRecord): ReactNode[] {
  const a = obj(call.arguments), r = obj(call.result);
  switch (call.name) {
    case 'read_brief': return ['Read the question and the budget'];
    case 'frame_problem': return ['Defined the decision', <p key="o">{text(a.objective)}</p>];
    case 'search_evidence': return [`Searched for “${text(a.query)}”`, Array.isArray(r.results) ? <p key="r" className="muted">{r.results.length ? `Found ${(r.results as { title?: unknown }[]).map((x) => text(x.title)).join('; ')}` : 'Found nothing'}</p> : null];
    case 'challenge_theory': return [`Stress-tested ${text(a.theory_id)}: searched for evidence against it, “${text(a.query)}”`];
    case 'read_source': return [<span key="s">Read <SourceTitle record={record} id={a.id} /></span>];
    case 'add_theory': return [`Proposed explanation ${text(r.theory_id || '')}`.trim(), <p key="c">{text(a.claim)}</p>, a.why_behaviour_changes ? <p key="w" className="muted">Why: {text(a.why_behaviour_changes)}</p> : null];
    case 'assess_evidence': return [`Weighed a source for ${text(a.theory_id)}: ${a.direction === 'supports' ? 'for' : a.direction === 'contradicts' ? 'against' : 'no bearing'}`, a.quote ? <Quote key="q" body={a.quote} record={record} id={a.evidence_id} /> : null, a.does_not_show ? <p key="d" className="muted">Does not show: {text(a.does_not_show)}</p> : null];
    case 'propose_test': return [`Proposed a test: ${text(a.name)}`, <p key="m">{text(a.method)}</p>, a.decision_rule ? <p key="r" className="muted">How it would decide: {text(a.decision_rule)}</p> : null];
    case 'decline_test': return ['Decided a test is not worth the cost', <p key="r">{text(a.reason)}</p>];
    case 'state_position': return [`Formed a view: ${text(a.favoured_theory)} leads`, <p key="r">{text(a.recommendation)}</p>];
    case 'revise_theory': return [`Marked ${text(a.theory_id)} as ${text(a.status)}`, <p key="r">{text(a.reason)}</p>];
    case 'finish': return ['Wrote the recommendation', <p key="r">{text(a.recommendation)}</p>];
    default: return [text(call.name) || 'Unreadable call'];
  }
}

// One line saying what a call was about.
export function gist(call: Call, record: RunRecord): string {
  const a = obj(call.arguments), r = obj(call.result);
  const found = Array.isArray(r.results) ? `, ${r.results.length} found` : '';
  switch (call.name) {
    case 'read_brief': return 'the company, the question and the budgets';
    case 'frame_problem': return text(a.objective);
    case 'search_evidence': return `“${text(a.query)}”${found}`;
    case 'challenge_theory': return `against ${text(a.theory_id)}: “${text(a.query)}”${found}`;
    case 'read_source': { const source = record.sources?.[str(a.id)]; return source ? text(source.title) : text(a.id); }
    case 'add_theory': return `${r.theory_id ? `${text(r.theory_id)}: ` : ''}${text(a.claim)}`;
    case 'assess_evidence': return `${text(a.theory_id)} ${text(a.direction)}: “${text(a.quote)}”`;
    case 'propose_test': return text(a.name);
    case 'decline_test': return text(a.reason);
    case 'state_position': return `favours ${text(a.favoured_theory)}: ${text(a.recommendation)}`;
    case 'revise_theory': return `${text(a.theory_id)} ${text(a.status)}: ${text(a.reason)}`;
    case 'finish': return text(a.recommendation);
    default: return '';
  }
}

// Consecutive calls in one stage form a visit; a stage visited twice appears where it recurred.
export interface Visit { stage: string | undefined; calls: [Call, number][] }

export function visits(record: RunRecord): Visit[] {
  const out: Visit[] = [];
  (record.calls || []).forEach((call, index) => {
    const last = out[out.length - 1];
    if (last && last.stage === call.stage) last.calls.push([call, index + 1]);
    else out.push({ stage: call.stage, calls: [[call, index + 1]] });
  });
  return out;
}

export const refusedIn = (calls: [Call, number][]): number => calls.filter(([c]) => !c.accepted).length;
export const plural = (n: number, word: string): string => `${n} ${n === 1 ? word : `${word}s`}`;

// One plain line for the live activity feed while an investigation runs.
export function activity(call: Call, record: RunRecord): string {
  if (!call.accepted) return 'Not accepted by the checker; it changed nothing and is trying again';
  const a = obj(call.arguments);
  const kind: Record<string, string> = { verified_observation: 'independent', company_claim: "company's own claim", synthetic: 'simulated what-if', web_page: 'web page' };
  switch (call.name) {
    case 'read_brief': return 'Read the question and the budget';
    case 'frame_problem': return 'Defined the decision and its alternatives';
    case 'search_evidence': return `Searched for “${text(a.query)}”`;
    case 'challenge_theory': return `Looked for evidence against ${text(a.theory_id)}`;
    case 'read_source': { const s = record.sources?.[str(a.id)]; return s ? `Read “${text(s.title)}” (${kind[s.class] ?? s.class})` : 'Read a source'; }
    case 'add_theory': return `Proposed an explanation: ${text(a.claim)}`;
    case 'assess_evidence': return `Noted a source ${a.direction === 'supports' ? 'for' : a.direction === 'contradicts' ? 'against' : 'with no bearing on'} ${text(a.theory_id)}`;
    case 'propose_test': return `Designed a test: ${text(a.name)}`;
    case 'decline_test': return 'Decided a test is not worth the cost';
    case 'state_position': return `Formed a view: ${text(a.favoured_theory)} leads`;
    case 'revise_theory': return `Updated ${text(a.theory_id)} after new evidence`;
    case 'finish': return 'Wrote the recommendation';
    default: return text(call.name);
  }
}
