import type { BeliefRow, EvidenceRow, Metrics } from '../types.ts';
import { euros, text } from '../labels.ts';

// Small SVG charts for one investigation. Every number is counted from its record (app/insights.py). Quantities are
// shown by length and position, never by area; colour always comes with a label or a sign (docs/DESIGN_RESEARCH.md).

const short = (s: string, n = 70): string => (s.length > n ? `${s.slice(0, n - 1).trimEnd()}…` : s);

export function BeliefChart({ rows, scale, names }: { rows: BeliefRow[]; scale: string[]; names: Record<string, string> }) {
  const W = 640, left = 0, top = 26, row = 54, pad = 36;
  const plotLeft = 200, step = (W - plotLeft - pad) / (scale.length - 1);
  const H = top + row * rows.length + 4;
  const x = (i: number): number => plotLeft + i * step;
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="How likely the assistant judged each explanation">
        <defs><marker id="arrowhead" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" className="c-accent-fill" /></marker></defs>
        {scale.map((label, i) => (
          <g key={label}>
            <line x1={x(i)} y1={top - 6} x2={x(i)} y2={H - 4} className="c-grid" />
            <text x={x(i)} y={12} textAnchor="middle" className="c-axis">{label}</text>
          </g>
        ))}
        {rows.map((b, r) => {
          const y = top + r * row + row / 2 - 4;
          const moved = b.after_step !== null && b.before_step !== null && b.after_step !== b.before_step;
          return (
            <g key={b.id}>
              <title>{`${names[b.id] ?? b.id}: ${b.before ?? 'not stated'}${moved ? ` → ${b.after}` : ''}`}</title>
              <text x={left} y={y - 4} className={`c-label${b.favoured ? ' strong' : ''}`}>{names[b.id] ?? b.id}{b.favoured ? '  ★ leading' : ''}</text>
              <text x={left} y={y + 12} className="c-sub">{short(b.claim, 34)}</text>
              {b.before_step === null ? <text x={plotLeft} y={y + 4} className="c-sub">not stated</text> : moved ? (
                <>
                  <line x1={x(b.before_step)} y1={y} x2={x(b.after_step as number) + (b.after_step! > b.before_step ? -9 : 9)} y2={y} className="c-arrow" markerEnd="url(#arrowhead)" />
                  <circle cx={x(b.before_step)} cy={y} r={6} className="c-dot-hollow" />
                  <circle cx={x(b.after_step as number)} cy={y} r={7} className="c-dot" />
                </>
              ) : <circle cx={x(b.before_step)} cy={y} r={7} className="c-dot" />}
            </g>
          );
        })}
      </svg>
      <figcaption>The assistant's own judgement on a five-step scale, not a measured probability.{rows.some((b) => b.after_step !== null && b.after_step !== b.before_step) ? ' The arrow shows how new evidence moved it.' : ''}</figcaption>
    </figure>
  );
}

export function EvidenceBars({ rows, names }: { rows: EvidenceRow[]; names: Record<string, string> }) {
  const most = Math.max(1, ...rows.map((r) => Math.max(r.supports, r.contradicts)));
  return (
    <figure className="chart">
      <div className="diverging" role="table" aria-label="Sources for and against each explanation">
        <div className="div-head" role="row"><span role="columnheader" /><span role="columnheader" className="against-text">− against</span><span role="columnheader" className="support-text">for +</span><span role="columnheader">no bearing</span></div>
        {rows.map((r) => (
          <div className="div-row" role="row" key={r.id}>
            <span role="rowheader" className="div-name">{names[r.id] ?? r.id}</span>
            <span role="cell" className="div-left">{r.contradicts ? <><b>{r.contradicts}</b><i className="bar against" style={{ width: `${(r.contradicts / most) * 100}%` }} /></> : <b className="zero">0</b>}</span>
            <span role="cell" className="div-right">{r.supports ? <><i className="bar support" style={{ width: `${(r.supports / most) * 100}%` }} /><b>{r.supports}</b></> : <b className="zero">0</b>}</span>
            <span role="cell" className="div-neutral">{r.neutral}</span>
          </div>
        ))}
      </div>
      <figcaption>How many of the sources it weighed support or contradict each explanation.</figcaption>
    </figure>
  );
}

export function SourceMix({ sources }: { sources: Metrics['sources'] }) {
  const total = sources.reduce((n, s) => n + s.count, 0);
  if (!total) return null;
  return (
    <figure className="chart">
      <div className="stack" role="img" aria-label={sources.map((s) => `${s.count} ${s.label}`).join(', ')}>
        {sources.map((s) => <span key={s.class} className={`seg k-${s.class}`} style={{ flexGrow: s.count }} title={`${s.count} ${s.label}`} />)}
      </div>
      <ul className="stack-legend">
        {sources.map((s) => <li key={s.class}><i className={`k-${s.class}`} />{s.count} {s.label.toLowerCase()}</li>)}
      </ul>
    </figure>
  );
}

export function Bullet({ value, limit, label, format }: { value?: number; limit?: number; label: string; format: (n: number) => string }) {
  if (typeof value !== 'number' || !limit) return null;
  const share = Math.max(0, Math.min(value / limit, 1));
  return (
    <div className="bullet">
      <div className="bullet-head"><span>{label}</span><b>{format(value)} <span className="muted">of {format(limit)}</span></b></div>
      <div className="bullet-track" role="img" aria-label={`${format(value)} of ${format(limit)}`}><span style={{ width: `${share * 100}%` }} /></div>
    </div>
  );
}

export const money = (n: number): string => euros(n);
export const weeks = (n: number): string => `${n} week${n === 1 ? '' : 's'}`;
export const nameOf = (claim: unknown, id: string): string => {
  const words = text(claim).replace(/^(consumers|customers|buyers|users|people)\s+(will|would)\s+/i, '').split(/\s+/).slice(0, 6).join(' ');
  return words ? `${id}` : id;
};
