import { createElement, type ReactNode, useEffect, useState } from 'react';
import { api } from '../api.ts';
import type { OnError } from '../App.tsx';
import { Chip } from '../Chip.tsx';
import { sentence, stageName, variant } from '../labels.ts';
import type { BeliefsResponse, Workflow } from '../types.ts';
import { loadWorkflow } from '../workflow.ts';

// MathML through createElement: React puts these in the MathML namespace under <math>, and every symbol is text.
type Node = ReactNode;
const m = (tag: string, props: Record<string, string> | null, ...children: Node[]): Node => createElement(tag, props, ...children);
const mi = (x: string): Node => m('mi', null, x);
const mo = (x: string): Node => m('mo', null, x);
const mn = (x: string): Node => m('mn', null, x);
const row = (...xs: Node[]): Node => m('mrow', null, ...xs);
const sub = (base: Node, s: Node): Node => m('msub', null, typeof base === 'string' ? mi(base) : base, typeof s === 'string' ? m('mtext', null, s) : s);
const th = (s: string): Node => sub('θ', s);
const P = (...xs: Node[]): Node => row(mi('P'), mo('('), ...xs, mo(')'));
const tilde = (x: string): Node => m('mover', { accent: 'true' }, mi(x), mo('~'));
const prime = (x: string): Node => m('msup', null, mi(x), mo('′'));
const space = (): Node => m('mspace', { width: '0.6em' });
const paren = (...xs: Node[]): Node => row(mo('('), ...xs, mo(')'));
const pair = (a: string, c: string): Node => paren(mi(a), mo(','), mi(c));

function Equation({ n, children }: { n?: number; children: Node[] }) {
  return (
    <div className="eq">
      <div className="eq-body" tabIndex={0}>{m('math', { display: 'block' }, row(...children))}</div>
      {n ? <span className="eq-n muted">({n})</span> : null}
    </div>
  );
}

function Network() {
  const box = (x: number, label: string, detail: string) => (
    <g key={label}>
      <rect x={x} y={8} width={150} height={54} rx={10} className="net-node" />
      <text x={x + 75} y={32} textAnchor="middle" className="net-label">{label}</text>
      <text x={x + 75} y={50} textAnchor="middle" className="net-sub">{detail}</text>
    </g>
  );
  return (
    <svg viewBox="0 0 400 70" className="net" role="img" aria-label="Bayesian network: fashion design Xf causes demand Xd">
      <defs><marker id="net-arrow" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={7} markerHeight={7} orient="auto"><path d="M0,0 L10,5 L0,10 z" className="net-head" /></marker></defs>
      {box(10, 'Xf: fashion design', 'Y (yes) or N (no)')}{box(240, 'Xd: demand', 'H (high) or L (low)')}
      <line x1={160} y1={35} x2={236} y2={35} className="net-edge" markerEnd="url(#net-arrow)" />
    </svg>
  );
}

interface Inputs { omega: number; thetaY: number; thetaHN: number; n: number; k: number }

// Numerical posterior for θHY under the theory: θHY ~ Uniform(θHN, 1), k of n buy. Log scale so large n cannot underflow.
function updateNumbers({ omega, thetaY, thetaHN, n, k }: Inputs) {
  const loglik = (t: number): number => (k ? k * Math.log(t) : 0) + (n - k ? (n - k) * Math.log(1 - t) : 0);
  const steps = 2000, a = thetaHN, b = 1 - 1e-9, h = (b - a) / steps;
  const xs = Array.from({ length: steps + 1 }, (_, i) => a + i * h);
  const ls = xs.map(loglik);
  const top = Math.max(...ls);
  const weight = (i: number): number => (i === 0 || i === steps ? 1 : i % 2 ? 4 : 2);
  let mass = 0, first = 0;
  xs.forEach((x, i) => { const f = Math.exp((ls[i] ?? top) - top) * weight(i); mass += f; first += x * f; });
  mass *= h / 3; first *= h / 3;
  const meanHY = first / mass;
  // Marginal likelihood: the prior density is 1 / (1 − θHN) on (θHN, 1); under the null θHY equals θHN exactly.
  const bf = Math.exp(top + Math.log(mass) - Math.log(1 - thetaHN) - loglik(thetaHN));
  const omega2 = Number.isFinite(bf) ? (omega * bf) / (omega * bf + 1 - omega) : 1;
  const vTheory = thetaHN + thetaY * ((thetaHN + 1) / 2 - thetaHN);
  const vTheory2 = thetaHN + thetaY * (meanHY - thetaHN);
  const vNull = thetaHN;
  return { meanHY, bf, omega2, vTheory, vTheory2, vNull, v: omega * vTheory + (1 - omega) * vNull, v2: omega2 * vTheory2 + (1 - omega2) * vNull };
}

const SLIDERS: [key: keyof Inputs, label: string, min: number, max: number, step: number][] = [
  ['omega', 'ω, belief that the theory is right', 0.05, 0.95, 0.05],
  ['thetaY', 'θY, chance the fashion design works', 0, 1, 0.05],
  ['thetaHN', 'θHN, demand without fashion design', 0.05, 0.9, 0.05],
  ['n', 'n, customers shown the fashion design', 0, 60, 1],
  ['k', 'k, of them who buy', 0, 60, 1],
];
const fmt = (x: number, d = 3): string => (Number.isFinite(x) ? x.toFixed(d) : '∞');

function Calculator() {
  const [s, setS] = useState<Inputs>({ omega: 0.5, thetaY: 0.8, thetaHN: 0.5, n: 0, k: 0 });
  const r = updateNumbers(s);
  const set = (key: keyof Inputs, value: number): void => setS((old) => {
    const next = { ...old, [key]: value };
    if (next.k > next.n) next.k = next.n;
    return next;
  });
  const line = (label: string, before: string, after: string) => <tr key={label}><th scope="row">{label}</th><td className="num">{before}</td><td className="num">{after}</td></tr>;
  return (
    <div className="calc">
      <div className="calc-in">
        {SLIDERS.map(([key, label, min, max, step]) => (
          <label key={key} className="calc-row">
            <span>{label}</span>
            <input type="range" min={min} max={key === 'k' ? s.n : max} step={step} value={s[key]} aria-label={label} onChange={(e) => set(key, Number(e.target.value))} />
            <output className="num">{String(s[key])}</output>
          </label>
        ))}
      </div>
      <div className="calc-out" aria-live="polite">
        <table className="totals">
          <thead><tr><th /><th className="num" scope="col">Before</th><th className="num" scope="col">After the experiment</th></tr></thead>
          <tbody>
            {line('Expected θHY under the theory', fmt((s.thetaHN + 1) / 2), fmt(r.meanHY))}
            {line('VΘ, the theory’s P(H)', fmt(r.vTheory), fmt(r.vTheory2))}
            {line('VΘ̃, the null’s P(H)', fmt(r.vNull), fmt(r.vNull))}
            {line('ω, belief in the theory', fmt(s.omega, 2), fmt(r.omega2))}
            {line('V = ωVΘ + (1 − ω)VΘ̃', fmt(r.v), fmt(r.v2))}
          </tbody>
        </table>
        <p className="muted small">{s.n
          ? `Bayes factor, theory against null: ${fmt(r.bf, 2)}. Above 1 the observations favour the theory, below 1 the null.`
          : 'With no customers observed nothing updates. With the defaults this reproduces the paper: VΘ = 0.7, VΘ̃ = 0.5, V = ω·0.7 + (1 − ω)·0.5.'}</p>
      </div>
    </div>
  );
}

const MAPPING: [concept: string, stage: string, tool: string, does: string][] = [
  ['Attributes and state space X (eq. 1)', 'frame', 'frame_problem', 'States the objective, the constraints and the alternatives, which fixes what the investigation is about.'],
  ['A causal link and its restriction, θHY > θHN', 'theories', 'add_theory', 'Each theory names a cause, why behaviour changes, how value is captured, its assumptions and its predictions.'],
  ['Null hypothesis and an alternative theory Q', 'theories', 'add_theory', 'At least two rival theories with different causes.'],
  ['Questioning the theory, ω < 1', 'challenge', 'challenge_theory', 'Searches for what could prove the favoured theory wrong, then reads what it found.'],
  ['Pseudo-observations behind μ(θ)', 'assessment', 'assess_evidence', 'Says how a source bears on a theory, quoting its exact words, and what it cannot establish.'],
  ['An experiment that discriminates', 'test', 'propose_test', 'A test where the theories predict different results, with a decision rule that has a threshold.'],
  ['Committing without experimenting', 'test', 'decline_test', 'Says why more information is not worth its cost, as when V or Q already dominates.'],
  ['ω and V before an experiment', 'position', 'state_position', 'Names the favoured theory and rates each theory on a five-point scale.'],
  ['V to V′ (eq. 7)', 'update', 'revise_theory', 'After a simulated what-if: keeps, revises or rejects the theory it bears on, citing it.'],
  ['Commit', 'conclude', 'finish', 'Recommends, with the favoured theory, the uncertainty, what would change it and the final beliefs.'],
];

const Verdict = ({ v }: { v: string }) =>
  (v === 'consistent' ? <Chip kind="good">✓ consistent</Chip> : v === 'inconsistent' ? <Chip kind="bad">✕ inconsistent</Chip> : <Chip kind="quiet">{v}</Chip>);

function Paper() {
  return (
    <div className="card">
      <h2>The math in the paper</h2>
      <p className="lead">Camuffo, Gambardella and Pignataro (2024), “Theory-driven strategic management decisions”, Strategy Science 9(4): 382–396, sections 3 and 4. Their example is Luxottica deciding whether eyeglasses could be a fashion product.</p>
      <h3>1. Attributes define a state space</h3>
      <p>An attribute is a question whose answer is uncertain: can Luxottica design fashion eyewear (Y or N), and will demand be high or low (H or L)? Together they make four states.</p>
      <Equation n={1}>{[mi('X'), mo('='), sub('X', 'f'), mo('×'), sub('X', 'd'), mo('='), mo('{'), pair('H', 'Y'), mo(','), pair('H', 'N'), mo(','), pair('L', 'Y'), mo(','), pair('L', 'N'), mo('}')]}</Equation>
      <p>The decision maker cares about high demand, so the target is the probability of H:</p>
      <Equation n={2}>{[P(mi('H')), mo('='), P(mi('H'), mo(','), mi('Y')), mo('+'), P(mi('H'), mo(','), mi('N'))]}</Equation>
      <h3>2. A theory is a Bayesian network with a restriction</h3>
      <p>The theory says fashion design causes demand. As a Bayesian network that is one arrow, and the claim is an inequality on its conditional probabilities.</p>
      <Network />
      <Equation>{[P(mi('H'), mo('|'), mi('Y')), mo('>'), P(mi('H'), mo('|'), mi('N')), space(), mo('⇔'), space(), th('HY'), mo('>'), th('HN')]}</Equation>
      <Equation>{[mi('Θ'), mo('='), mo('{'), mi('θ'), mo(':'), th('HY'), mo('>'), th('HN'), mo('}')]}</Equation>
      <p>Writing θY for P(Y), the probability of high demand for one set of parameters is:</p>
      <Equation n={3}>{[mi('E'), mi('P'), paren(mi('H')), mo('≡'), mi('v'), paren(mi('θ')), mo('='), th('HY'), th('Y'), mo('+'), th('HN'), paren(mn('1'), mo('−'), th('Y')), mo('='), th('HN'), mo('+'), th('Y'), paren(th('HY'), mo('−'), th('HN'))]}</Equation>
      <h3>3. Beliefs about the parameters, under the theory and under the null</h3>
      <p>The parameters are not known, so the decision maker holds a distribution μ over them. The theory allows only parameters in Θ; the null hypothesis, here θHY = θHN, allows only Θ̃.</p>
      <Equation n={4}>{[sub('V', 'Θ'), mo('≡'), sub(mi('E'), row(mi('θ'), mo('∈'), mi('Θ'))), mi('v'), paren(mi('θ')), mo('='), m('msub', null, mo('∫'), row(mi('θ'), mo('∈'), mi('Θ'))), mi('v'), paren(mi('θ')), sub('μ', 'Θ'), paren(mi('θ')), mi('d'), mi('θ')]}</Equation>
      <Equation n={5}>{[sub('V', tilde('Θ')), mo('≡'), m('msub', null, mo('∫'), row(mi('θ'), mo('∈'), tilde('Θ'))), mi('v'), paren(mi('θ')), sub('μ', tilde('Θ')), paren(mi('θ')), mi('d'), mi('θ')]}</Equation>
      <p>The decision maker is not sure the theory is right, and ω is the prior that it is. The expected value of the theory weighs the two:</p>
      <Equation n={6}>{[mi('V'), mo('='), mi('ω'), sub('V', 'Θ'), mo('+'), paren(mn('1'), mo('−'), mi('ω')), sub('V', tilde('Θ'))]}</Equation>
      <div className="worked">
        <strong>The paper’s numbers</strong>
        <p>θHN = 0.5 and θY = 0.8, each with probability 1, and θHY uniform. Under the theory θHY is uniform on (0.5, 1), so its expected value is 0.75:</p>
        <Equation>{[sub('V', 'Θ'), mo('='), mn('0.5'), mo('+'), paren(mn('0.75'), mo('−'), mn('0.5')), mo('·'), mn('0.8'), mo('='), mn('0.7')]}</Equation>
        <Equation>{[sub('V', tilde('Θ')), mo('='), mn('0.5'), space(), mo(','), space(), mi('V'), mo('='), mi('ω'), mo('·'), mn('0.7'), mo('+'), paren(mn('1'), mo('−'), mi('ω')), mo('·'), mn('0.5')]}</Equation>
        <p className="muted small">Without the restriction θHY would average 0.5 and V would be 0.5. The theory raises belief in high demand by ruling parameter values out.</p>
      </div>
      <h3>4. Experiments update the theory</h3>
      <p>An experiment updates μ, and so VΘ and VΘ̃. The prior ω on the theory changes only when the evidence moves μ past a threshold, ‖μ′ − μ‖ &gt; μ*: a small surprise adjusts the parameters, a large one shakes belief in the theory itself.</p>
      <Equation n={7}>{[prime('V'), mo('='), prime('ω'), m('msubsup', null, mi('V'), mi('Θ'), mo('′')), mo('+'), paren(mn('1'), mo('−'), prime('ω')), m('msubsup', null, mi('V'), tilde('Θ'), mo('′'))]}</Equation>
      <p>An alternative theory, with its own attributes and causal links, has its own value Q, built the same way. The decision maker can commit to either theory or experiment on either. With costly experiments, committing is right once V is far enough above or below Q; in between it pays to experiment (their Appendix A, extending Moscarini and Smith 2001). Experiments are assumed Bayes plausible: before running one there is no reason to expect it to move the value either way.</p>
      <Equation>{[mi('E'), prime('V'), mo('='), mi('V'), space(), mo(','), space(), mi('E'), prime('ω'), mo('='), mi('ω')]}</Equation>
    </div>
  );
}

export function MathPage({ onError }: { onError: OnError }) {
  const [w, setW] = useState<Workflow | null>(null);
  const [b, setB] = useState<BeliefsResponse | null>(null);
  useEffect(() => {
    loadWorkflow().then(setW).catch(onError);
    api<BeliefsResponse>('/api/beliefs').then(setB).catch(onError);
  }, [onError]);
  const known = new Set(w ? w.stages.flatMap((s) => s.tools) : []);
  const reached = (b?.arms ?? []).map((a) => ({ ...a, reached: a.cases.filter((c) => c.moves.length && c.moves.some((mv) => mv.before)) }));

  return (
    <>
      <Paper />
      <div className="card">
        <h2>Try the update</h2>
        <p className="note">An illustration of the paper’s framework with standard Bayesian updating, not something the agent computes.</p>
        <p className="muted small">Observe n customers shown the fashion design; k buy. Under the theory θHY is uniform on (θHN, 1); under the null θHY = θHN. The calculator updates μ and ω fully by Bayes’ rule. The paper changes ω only past a threshold, so this overstates how often ω moves.</p>
        <Calculator />
      </div>
      <div className="card">
        <h2>How the agent carries this out</h2>
        <p className="lead">The agent follows the paper’s steps in words, with tools and evidence, but it does not compute probabilities.</p>
        <table className="totals mapping">
          <thead><tr><th scope="col">In the paper</th><th scope="col">Stage and tool</th><th scope="col">What the agent does</th></tr></thead>
          <tbody>
            {MAPPING.filter(([, , tool]) => known.has(tool)).map(([concept, stage, tool, does]) => (
              <tr key={concept}><th scope="row">{concept}</th><td><span className="muted small">{stageName(stage)} · </span><code className="tool-name">{tool}</code></td><td>{does}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h2>How we assess the model</h2>
        <p>The agent does not compute a Bayesian update, and nor does the harness. Decided on November 2, 2026 with Codex: a computed update would need an invented network and invented numbers, and assumed ratios could create the very revision we want to measure.</p>
        <p>Instead, in cases with a simulated what-if, the model rates each theory on a five-point scale (very unlikely, unlikely, uncertain, likely, very likely) when it states its position, and again after the what-if. The evaluation protocol scores whether its response targets the affected theory, cites the what-if, explains its limits, and moves in the direction the packet was written to push. A weak result may rationally change nothing, scripted policies that always keep or always change must not be rewarded, and blind judges score the full rubric. The scale is a within-run signal, not a calibrated probability.</p>
        <h3>What the pilots show so far</h3>
        <p className="muted small">Undermining evidence should not raise the affected theory’s belief, supporting evidence should not lower it, irrelevant evidence should leave it unchanged. A direction check only.</p>
        {!b ? <p className="muted">Loading…</p> : reached.map((a) => (
          <div key={`${a.pilot}-${a.arm}`} className="belief-arm">
            <h4>{a.pilot_label}, {a.arm_label}: <span className="muted">{a.reached.length} of {a.cases.length} what-if cases reached a stated position with the what-if delivered</span></h4>
            {a.reached.length ? (
              <table className="totals">
                <thead><tr>{['Case', 'What-if', 'Theory', 'Before', 'After', 'Direction'].map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
                <tbody>
                  {a.reached.flatMap((c) => c.moves.map((mv) => (
                    <tr key={`${c.case}-${c.index}-${mv.theory}`}>
                      <td>{sentence(c.case.split('-')[0])} · {variant(c.case).replace('Simulated evidence: ', '')}</td>
                      <td>{c.direction}</td><td>{mv.theory}</td><td>{mv.before || '—'}</td><td>{mv.after || '—'}</td><td><Verdict v={mv.verdict} /></td>
                    </tr>
                  )))}
                </tbody>
              </table>
            ) : null}
          </div>
        ))}
        <p className="note">Very few pilot runs reach the what-if, so these rows say almost nothing yet. The measure becomes informative once runs routinely reach that stage.</p>
      </div>
    </>
  );
}
