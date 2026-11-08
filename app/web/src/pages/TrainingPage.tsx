import { useCallback, useEffect, useState } from 'react';
import { api } from '../api.ts';
import type { OnError } from '../App.tsx';
import { Chip } from '../Chip.tsx';
import { text } from '../labels.ts';
import type { HeldPoint, LossPoint, TrainingLive } from '../types.ts';

// Per-step loss is noisy, so the line drawn is a trailing mean over 25 steps, over the faint raw line.
function smooth(points: LossPoint[], window = 25): LossPoint[] {
  let sum = 0;
  return points.map((p, i) => {
    sum += p.loss;
    const dropped = points[i - window];
    if (dropped) sum -= dropped.loss;
    return { step: p.step, loss: sum / Math.min(i + 1, window) };
  });
}

function LossChart({ train, held, best }: { train: LossPoint[]; held: HeldPoint[]; best: HeldPoint | null }) {
  const W = 680, H = 260, L = 44, R = 16, T = 16, B = 30;
  const maxX = Math.max(1, ...train.map((p) => p.step), ...held.map((p) => p.step));
  const maxY = Math.max(0.1, ...train.map((p) => p.loss), ...held.map((p) => p.eval_loss)) * 1.05;
  const x = (v: number): number => L + (v / maxX) * (W - L - R);
  const y = (v: number): number => T + (1 - v / maxY) * (H - T - B);
  const path = (pts: { step: number; value: number }[]): string => pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.step).toFixed(1)},${y(p.value).toFixed(1)}`).join('');
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * maxY);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Training loss and held-out loss by step">
      {ticks.map((v) => (
        <g key={v}>
          <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--grid)" strokeWidth={1} />
          <text x={L - 6} y={y(v) + 4} textAnchor="end" className="axis">{v.toFixed(2)}</text>
        </g>
      ))}
      <text x={L} y={H - 8} className="axis">step 0</text>
      <text x={W - R} y={H - 8} textAnchor="end" className="axis">step {maxX}</text>
      {train.length ? <path d={path(train.map((p) => ({ step: p.step, value: p.loss })))} fill="none" stroke="var(--series-1)" strokeWidth={1} opacity={0.25} /> : null}
      {train.length ? <path d={path(smooth(train).map((p) => ({ step: p.step, value: p.loss })))} fill="none" stroke="var(--series-1)" strokeWidth={2} /> : null}
      {held.length ? <path d={path(held.map((p) => ({ step: p.step, value: p.eval_loss })))} fill="none" stroke="var(--series-2)" strokeWidth={2} /> : null}
      {held.map((p) => <circle key={`hit-${p.step}`} cx={x(p.step)} cy={y(p.eval_loss)} r={8} fill="transparent"><title>Step {p.step}: held-out loss {p.eval_loss.toFixed(3)}</title></circle>)}
      {held.map((p) => <circle key={`dot-${p.step}`} cx={x(p.step)} cy={y(p.eval_loss)} r={3} fill="var(--series-2)" pointerEvents="none" />)}
      {best ? (
        <g pointerEvents="none">
          <line x1={x(best.step)} x2={x(best.step)} y1={T} y2={H - B} stroke="var(--ink-2)" strokeWidth={1} strokeDasharray="3 3" />
          <circle cx={x(best.step)} cy={y(best.eval_loss)} r={5} fill="var(--series-2)" stroke="var(--surface)" strokeWidth={2} />
          <text x={x(best.step) + 6} y={T + 10} className="axis">best, step {best.step}</text>
        </g>
      ) : null}
    </svg>
  );
}

const ACTIVE = ['PENDING', 'CONFIGURING', 'RUNNING', 'COMPLETING', 'REQUEUED', 'RESIZING', 'SUSPENDED'];

const Key = ({ swatch, label }: { swatch: string; label: string }) => <span className="key"><span className={`swatch ${swatch}`} />{label}</span>;

export function TrainingPage({ onError }: { onError: OnError }) {
  const [live, setLive] = useState<TrainingLive | null>(null);
  const load = useCallback(() => { api<TrainingLive>('/api/training/live').then(setLive).catch(onError); }, [onError]);
  useEffect(load, [load]);
  const running = Boolean(live?.state?.startsWith('RUNNING'));
  // Follow a queued job too, so the page sees it start and end; the feed polls the same states.
  const active = Boolean(live?.state && ACTIVE.some((s) => live.state?.startsWith(s)));
  useEffect(() => {
    if (!active) return undefined;
    const timer = window.setTimeout(load, 30000);
    return () => window.clearTimeout(timer);
  }, [active, live, load]);

  if (!live) return <div className="card"><h2>Training</h2><p className="muted">Loading…</p></div>;
  if (!live.state) {
    return <div className="card"><h2>Training</h2><p className="lead">No training run is being followed. Start scripts/training_feed.py with a job id.</p></div>;
  }
  const state = live.state;
  const train = live.train ?? [], held = live.held_out ?? [];
  const best = held.reduce<HeldPoint | null>((a, p) => (!a || p.eval_loss < a.eval_loss ? p : a), null);
  const last = train[train.length - 1];
  const pg = live.progress;
  return (
    <div className="card">
      <div className="row spread">
        <h2>{`Training job ${live.job ?? ''}`.trim()}</h2>
        <Chip kind={active ? 'warn' : state.startsWith('COMPLETED') ? 'good' : 'bad'}>{running ? 'Running' : state.charAt(0) + state.slice(1).toLowerCase()}</Chip>
      </div>
      <p className="lead">Held-out loss is measured on validation companies the model never trains on: Hellberg alone for the first two pilots, and from the third run on six companies, each weighted equally. It is used to choose a checkpoint, and it is not the final test. When it stops falling while training loss keeps falling, the model is fitting its training cases. Loss says how well it predicts the teacher, not how well it investigates.</p>
      <p className="muted small">Snapshot from {text(live.updated)}{active ? ', refreshed every 30 seconds while the job is queued or running' : ''}. If this time stops moving, the feed has stopped, not necessarily the job.</p>
      {pg && running ? (
        <div className="progress" role="progressbar" aria-label="Training progress" aria-valuemin={0} aria-valuemax={pg.total} aria-valuenow={pg.step}>
          <div style={{ width: `${((100 * pg.step) / pg.total).toFixed(1)}%` }} />
        </div>
      ) : null}
      <div className="row"><Key swatch="s1" label="Training loss, mean of 25 steps" /><Key swatch="s2" label="Held-out loss" /></div>
      <LossChart train={train} held={held} best={best} />
      <dl className="stats">
        <div><dt>Step</dt><dd>{pg ? `${pg.step} of ${pg.total}` : '–'}</dd></div>
        <div><dt>Training loss</dt><dd>{last ? last.loss.toFixed(3) : '–'}</dd></div>
        <div><dt>Best held-out loss</dt><dd>{best ? `${best.eval_loss.toFixed(3)} at step ${best.step}` : '–'}</dd></div>
        <div><dt>{running ? 'Time left' : 'Updated'}</dt><dd>{running && pg ? text(pg.remaining) : text(live.updated)}</dd></div>
      </dl>
      {live.notes?.length ? <p className="muted small">{live.notes.join(' · ')}</p> : null}
    </div>
  );
}
