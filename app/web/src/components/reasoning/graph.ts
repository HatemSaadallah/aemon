import { text } from '../../labels.ts';
import type { RunRecord } from '../../types.ts';

// The investigation's recorded reasoning as a graph. Pure: the same record and options give the same graph, so it is
// computed only when they change. Every node and edge comes from a field of the record; nothing is inferred.
//
// Stages (left to right): question -> hypotheses -> evidence and challenges -> sources -> experiments and simulated
// results -> revisions -> recommendation. Edges: considers, supports, contradicts, no_bearing, challenges, tests,
// observed (a simulated result read), revises, favours (the hypothesis the recommendation favours), cites (a source the
// recommendation cites).

export type NodeKind = 'question' | 'hypothesis' | 'group' | 'evidence' | 'challenge' | 'experiment' | 'declined' | 'simulated' | 'revision' | 'recommendation';
export type EdgeKind = 'considers' | 'supports' | 'contradicts' | 'no_bearing' | 'challenges' | 'tests' | 'observed' | 'revises' | 'favours' | 'cites';
export interface Detail { label?: string; text: string; tone?: 'for' | 'against' | 'none' | 'warn' | 'quote' }
export interface GNode { id: string; kind: NodeKind; col: number; title: string; sub?: string; theory?: string; direction?: string; count?: number; ref?: string; favoured?: boolean; status?: string; flags?: number;
  tally?: { for: number; against: number; none: number }; detail?: Detail[] }
export interface GEdge { id: string; from: string; to: string; kind: EdgeKind }
export interface Graph { nodes: GNode[]; edges: GEdge[]; names: Record<string, string> }
export interface Options { expanded: Set<string>; mode: 'overview' | 'evidence'; show: { supports: boolean; contradicts: boolean; no_bearing: boolean; challenges: boolean; experiments: boolean } }

const DIR: Record<string, EdgeKind> = { supports: 'supports', contradicts: 'contradicts', neutral: 'no_bearing' };
const COL = { question: 0, hypothesis: 1, group: 2, challenge: 2, evidence: 3, experiment: 4, declined: 4, simulated: 4, revision: 5, recommendation: 6 } as const;

export function structureKey(r: RunRecord | null): string {  // changes only when the reasoning structure does
  if (!r) return '';
  return [Object.keys(r.theories ?? {}).length, (r.assessments ?? []).length, (r.challenge_searches ?? []).length, Object.keys(r.tests ?? {}).length,
    r.test_declined ? 1 : 0, (r.revisions ?? []).length, r.final ? (r.final.draft ? 'd' : 'f') : r.position ? 'p' : '-', Object.keys(r.sources ?? {}).length].join(':');
}

export function buildGraph(r: RunRecord, o: Options): Graph {
  const nodes: GNode[] = [], edges: GEdge[] = [];
  const theories = Object.entries(r.theories ?? {});
  const names = Object.fromEntries(theories.map(([tid], i) => [tid, `Hypothesis ${i + 1}`]));
  const add = (n: GNode): void => { nodes.push(n); };
  const link = (from: string, to: string, kind: EdgeKind): void => { edges.push({ id: `${from}>${to}:${kind}`, from, to, kind }); };
  const favoured = r.final?.favoured_theory ?? r.position?.favoured_theory;

  add({ id: 'q', kind: 'question', col: COL.question, title: text(r.question) || 'The strategic question', sub: r.frame?.objective ? text(r.frame.objective) : undefined,
    detail: [...(r.frame?.objective ? [{ label: 'Objective', text: text(r.frame.objective) }] : []), ...(r.frame?.alternatives ?? []).map((x, i) => ({ label: i ? undefined : 'Alternatives', text: `• ${text(x)}` }))] });
  for (const [tid, t] of theories) {
    const mine = (r.assessments ?? []).filter((a) => a.theory_id === tid);
    const tt = t as Record<string, unknown>;
    add({ id: `h:${tid}`, kind: 'hypothesis', col: COL.hypothesis, title: text(t.claim), theory: tid, favoured: tid === favoured, status: text(t.status) || undefined,
      tally: { for: mine.filter((a) => a.direction === 'supports').length, against: mine.filter((a) => a.direction === 'contradicts').length, none: mine.filter((a) => a.direction === 'neutral').length },
      detail: [
        ...(tt.why_behaviour_changes ? [{ label: 'Why customers would change', text: text(tt.why_behaviour_changes) }] : []),
        ...(tt.who_benefits ? [{ label: 'Who it is for', text: text(tt.who_benefits) }] : []),
        ...(tt.how_value_is_captured ? [{ label: 'How the company earns', text: text(tt.how_value_is_captured) }] : []),
        ...mine.filter((a) => a.direction !== 'neutral').slice(0, 2).map((a) => ({ label: a.direction === 'supports' ? 'Quoted in support' : 'Quoted against', text: `“${text(a.quote)}”`, tone: (a.direction === 'supports' ? 'for' : 'against') as Detail['tone'] })),
        ...(mine.length && !mine.some((a) => a.direction === 'contradicts') ? [{ text: 'No evidence was weighed against it (not the same as none existing).', tone: 'warn' as const }] : []),
      ] });
    link('q', `h:${tid}`, 'considers');
  }
  // Evidence: one group per hypothesis and direction; expanded (or in evidence mode) into one node per source, shared
  // between hypotheses when the same source was weighed for several
  const assessments = r.assessments ?? [];
  const seen = new Set<string>();
  for (const [tid] of theories) {
    for (const dir of ['supports', 'contradicts', 'neutral'] as const) {
      const kind = DIR[dir] as 'supports' | 'contradicts' | 'no_bearing';
      if (!o.show[kind]) continue;
      const mine = assessments.filter((a) => a.theory_id === tid && a.direction === dir);
      if (!mine.length) continue;
      const gid = `g:${tid}:${dir}`;
      const open = o.mode === 'evidence' || o.expanded.has(gid) || o.expanded.has(`h:${tid}`);
      if (!open) {
        add({ id: gid, kind: 'group', col: COL.group, title: `${mine.length} ${dir === 'supports' ? 'supporting' : dir === 'contradicts' ? 'opposing' : 'no-bearing'} source${mine.length === 1 ? '' : 's'}`, theory: tid, direction: dir, count: mine.length,
          detail: mine.slice(0, 4).map((a) => ({ text: `• ${text(r.sources?.[a.evidence_id]?.title ?? a.evidence_id)}` })) });
        link(`h:${tid}`, gid, kind);
        continue;
      }
      for (const a of mine) {
        const eid = `e:${a.evidence_id}`;
        if (!seen.has(eid)) {
          seen.add(eid);
          const src = r.sources?.[a.evidence_id];
          add({ id: eid, kind: 'evidence', col: COL.group, title: src ? text(src.title) : a.evidence_id, sub: text(a.quote), ref: a.evidence_id, direction: dir, status: src?.class,
            detail: [{ label: 'Quoted', text: `“${text(a.quote)}”`, tone: 'quote' }, ...(a.does_not_show ? [{ label: "Agent's reading: does not show", text: text(a.does_not_show) }] : []),
              ...(src?.class === 'company_claim' ? [{ text: "The company's own words, not independent evidence.", tone: 'warn' as const }] : [])] });
        }
        link(`h:${tid}`, eid, kind);
      }
    }
  }
  if (o.show.challenges) {
    (r.challenge_searches ?? []).forEach((c, i) => {
      const id = `c:${i}`;
      const raw = c as unknown as { theory_id: string; query: string; found?: string[] };
      add({ id, kind: 'challenge', col: COL.challenge, title: `Challenge: ${text(raw.query)}`, theory: raw.theory_id, count: raw.found?.length ?? 0,
        detail: [{ label: 'Searched for evidence against it', text: `“${text(raw.query)}”: ${raw.found?.length ?? 0} source${raw.found?.length === 1 ? '' : 's'} found` }] });
      if (r.theories?.[raw.theory_id]) link(id, `h:${raw.theory_id}`, 'challenges');
    });
  }
  if (o.show.experiments) {
    for (const [key, test] of Object.entries(r.tests ?? {})) {
      const t = test as Record<string, unknown>;
      const id = `x:${key}`;
      add({ id, kind: 'experiment', col: COL.experiment, title: text(t.name) || key, sub: text(t.method), ref: key,
        detail: [{ text: 'Proposed by the agent, not run: no observed results.', tone: 'warn' },
          ...(t.method ? [{ label: 'Method', text: text(t.method) }] : []), ...(t.sample ? [{ label: 'Proposed sample', text: text(t.sample) }] : []),
          ...Object.entries((t.prediction_by_theory as Record<string, string>) ?? {}).map(([k, v]) => ({ label: `If ${names[k] ?? k} is right`, text: text(v) })),
          ...(t.decision_rule ? [{ label: 'Decision rule', text: text(t.decision_rule) }] : [])] });
      for (const tid of (t.theories as string[] | undefined) ?? []) if (r.theories?.[tid]) link(`h:${tid}`, id, 'tests');
    }
    if (r.test_declined) {
      add({ id: 'x:declined', kind: 'declined', col: COL.declined, title: 'Test declined', sub: text(r.test_declined.reason), detail: [{ label: "Agent's reason", text: text(r.test_declined.reason) }] });
      for (const [tid] of theories) link(`h:${tid}`, 'x:declined', 'tests');
    }
  }
  // Simulated what-if results the agent read, and the revisions that cite them
  const simulated = Object.values(r.sources ?? {}).filter((s) => s.class === 'synthetic' || s.simulated);
  for (const s of simulated) add({ id: `s:${s.id}`, kind: 'simulated', col: COL.simulated, title: text(s.title), sub: text(s.excerpt), ref: s.id,
    detail: [{ text: 'A what-if written for the case. Never evidence about real demand.', tone: 'warn' }, { label: 'What it says', text: text(s.excerpt) }] });
  (r.revisions ?? []).forEach((v, i) => {
    const raw = v as unknown as { theory_id: string; status: string; reason?: string; evidence_ids?: string[]; new_claim?: string };
    const id = `v:${i}`;
    add({ id, kind: 'revision', col: COL.revision, title: `${names[raw.theory_id] ?? raw.theory_id} ${raw.status === 'kept' ? 'kept' : raw.status === 'revised' ? 'revised' : text(raw.status)}`, sub: text(raw.reason), theory: raw.theory_id, status: raw.status,
      detail: [...(raw.reason ? [{ label: "Agent's reason", text: text(raw.reason) }] : []), ...(raw.new_claim ? [{ label: 'Revised claim', text: text(raw.new_claim) }] : [])] });
    if (r.theories?.[raw.theory_id]) link(id, `h:${raw.theory_id}`, 'revises');
    for (const e of raw.evidence_ids ?? []) {
      if (nodes.some((n) => n.id === `s:${e}`)) link(`s:${e}`, id, 'observed');
      else if (nodes.some((n) => n.id === `e:${e}`)) link(`e:${e}`, id, 'observed');
    }
  });
  // The recommendation, or what stands in for it
  const final = r.final;
  const recTitle = final ? text(final.recommendation) : r.position ? text(r.position.recommendation) : 'No recommendation: the investigation stopped first';
  add({ id: 'r', kind: 'recommendation', col: COL.recommendation, title: recTitle, status: final ? (final.draft ? 'draft' : 'final') : r.position ? 'interim' : 'none', flags: r.answer_flags?.length ?? 0,
    detail: [...(final?.next_action ? [{ label: 'Next step', text: text(final.next_action) }] : []), ...(final?.uncertainty ? [{ label: 'Still uncertain', text: text(final.uncertainty) }] : []),
      ...(r.answer_flags ?? []).map((f) => ({ text: `Check: ${text(f.label)}`, tone: 'warn' as const }))] });
  if (favoured && r.theories?.[favoured]) link(`h:${favoured}`, 'r', 'favours');
  for (const e of (final?.evidence_ids as string[] | undefined) ?? []) if (nodes.some((n) => n.id === `e:${e}`)) link(`e:${e}`, 'r', 'cites');
  return { nodes, edges, names };
}

// Layout: columns by stage; rows banded by hypothesis so a hypothesis's evidence and challenges sit beside it; nodes
// linked to several hypotheses sit at the mean of their rows; then each column is pushed apart so nothing overlaps.
// Three detail levels (semantic zoom): 0 bird's-eye, 1 overview, 2 detail. Width and height depend on the level and,
// at level 2, on the node's own text, so expanded cards never overlap: the layout is recomputed only when the level does.
export type Level = 0 | 1 | 2;
export const WIDTH: Record<Level, number> = { 0: 196, 1: 224, 2: 352 };  // overview cards narrow and tall: the map is wide, the screen has height to spare
export const NODE_W = WIDTH[1], COL_GAP = 52;
export const HEIGHT: Record<NodeKind, number> = { question: 150, hypothesis: 132, group: 60, evidence: 108, challenge: 104, experiment: 108, declined: 96, simulated: 100, revision: 96, recommendation: 152 };
const GAP_Y = 18;
const lines = (t: string, chars: number): number => Math.max(1, Math.ceil(t.length / chars));

export function sizeOf(n: GNode, level: Level): { w: number; h: number } {
  const w = WIDTH[level];
  if (level === 0) return { w, h: n.kind === 'group' ? 44 : 64 };
  if (level === 1) return { w, h: HEIGHT[n.kind] };
  // Level 2: title (up to 6 lines) plus every detail line (up to 9), erring tall: a card with spare room reads fine, a
  // card that cuts its last line does not
  const titleLines = Math.min(n.kind === 'question' || n.kind === 'recommendation' ? 8 : 6, lines(n.title, n.kind === 'question' || n.kind === 'recommendation' ? 34 : 38));
  const body = (n.detail ?? []).reduce((h, d) => h + (d.label ? 16 : 0) + Math.min(9, lines(d.text, 42)) * 19 + 8, 0);
  return { w, h: 52 + titleLines * 22 + body + (n.tally ? 24 : 0) };
}

export interface Placed extends GNode { x: number; y: number; w: number; h: number }

export function layout(g: Graph, level: Level = 1): { placed: Placed[]; width: number; height: number } {
  const by = new Map(g.nodes.map((n) => [n.id, n]));
  const H = (n: GNode): number => sizeOf(n, level).h, W = WIDTH[level], gap = level === 2 ? 110 : level === 0 ? 56 : COL_GAP;
  const y = new Map<string, number>();
  const cols = [...new Set(g.nodes.map((n) => n.col))].sort((a, b) => a - b);
  const x = (col: number): number => cols.indexOf(col) * (W + gap);
  // Hypotheses get bands sized by what hangs off them
  const hyps = g.nodes.filter((n) => n.kind === 'hypothesis');
  const kids = (hid: string): GNode[] => g.edges.filter((e) => e.from === hid || e.to === hid).map((e) => by.get(e.from === hid ? e.to : e.from)).filter((n): n is GNode => Boolean(n) && (n as GNode).col === 2);
  let cursor = 0;
  for (const h of hyps) {
    const k = kids(h.id);
    const need = Math.max(H(h), k.reduce((s, n) => s + H(n) + GAP_Y, 0) - GAP_Y);
    y.set(h.id, cursor + need / 2 - H(h) / 2);
    let ky = cursor;
    for (const n of k) if (!y.has(n.id)) { y.set(n.id, ky); ky += H(n) + GAP_Y; }
    cursor += need + GAP_Y * 3;
  }
  const centre = (id: string): number | undefined => { const v = y.get(id); const n = by.get(id); return v === undefined || !n ? undefined : v + H(n) / 2; };
  // Everything else at the mean of its placed neighbours, in column order
  for (const col of cols) {
    for (const n of g.nodes.filter((m) => m.col === col && !y.has(m.id))) {
      const near = g.edges.filter((e) => e.from === n.id || e.to === n.id).map((e) => centre(e.from === n.id ? e.to : e.from)).filter((v): v is number => v !== undefined);
      const c = near.length ? near.reduce((a, b) => a + b, 0) / near.length : cursor / 2;
      y.set(n.id, c - H(n) / 2);
    }
  }
  // No overlaps within a column
  for (const col of cols) {
    const inCol = g.nodes.filter((n) => n.col === col).sort((a, b) => (y.get(a.id) ?? 0) - (y.get(b.id) ?? 0));
    let floor = -Infinity;
    for (const n of inCol) { const v = Math.max(y.get(n.id) ?? 0, floor); y.set(n.id, v); floor = v + H(n) + GAP_Y; }
  }
  const top = Math.min(...g.nodes.map((n) => y.get(n.id) ?? 0));
  const placed = g.nodes.map((n) => ({ ...n, x: x(n.col), y: (y.get(n.id) ?? 0) - top, w: W, h: H(n) }));
  return { placed, width: (cols.length - 1) * (W + gap) + W, height: Math.max(...placed.map((p) => p.y + p.h)) };
}

// What to highlight around a node: itself, its neighbours, and for a hypothesis everything one step from those
export function related(g: Graph, id: string | null): Set<string> | null {
  if (!id) return null;
  const out = new Set([id]);
  const step = (ids: string[]): string[] => g.edges.filter((e) => ids.includes(e.from) || ids.includes(e.to)).flatMap((e) => [e.from, e.to]);
  const first = step([id]);
  first.forEach((n) => out.add(n));
  if (id.startsWith('h:')) step(first.filter((n) => !n.startsWith('h:') && n !== 'q' && n !== 'r')).forEach((n) => { if (!n.startsWith('h:') || n === id) out.add(n); });
  return out;
}
