import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.ts';
import type { OnError } from '../App.tsx';
import { Investigation } from '../components/Run.tsx';
import { stageName, stopName, variant } from '../labels.ts';
import type { Arm, Outcome, PilotsResponse, RunRecord, Totals } from '../types.ts';

const ARMS: readonly Arm[] = ['untrained', 'trained'];
const isArm = (value: string | undefined): value is Arm => ARMS.includes(value as Arm);

function OutcomeCell({ o, onOpen, selected }: { o: Outcome; onOpen: () => void; selected: boolean }) {
  return (
    <button type="button" className={`outcome${o.finished ? ' good' : ''}${selected ? ' selected' : ''}`} onClick={onOpen} aria-pressed={selected}>
      <span className="outcome-stop">{stopName(o.stop_reason)}</span>
      <span className="muted small">{o.finished ? '' : `Stopped while ${stageName(o.stage_at_stop).toLowerCase()} · `}{o.calls} steps · {o.refused} refused</span>
    </button>
  );
}

function TotalsTable({ t, arms }: { t: Record<Arm, Totals>; arms: Record<Arm, string> }) {
  const rows: [label: string, read: (x: Totals) => string, words: boolean][] = [
    ['Finished', (x) => `${x.finished} of ${x.cases}`, false],
    ['Refused steps', (x) => String(x.refused), false],
    ['Steps per run, mean', (x) => x.mean_calls.toFixed(1), false],
    ['How runs ended', (x) => Object.entries(x.stop_reasons).map(([k, v]) => `${v} ${stopName(k).toLowerCase()}`).join(', '), true],
  ];
  return (
    <table className="totals">
      <thead><tr><th />{ARMS.map((a) => <th key={a} className="num" scope="col">{arms[a]}</th>)}</tr></thead>
      <tbody>
        {rows.map(([label, read, words]) => (
          <tr key={label}><th scope="row">{label}</th>{ARMS.map((a) => <td key={a} className={words ? '' : 'num'}>{read(t[a])}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}

export function ResultsPage({ onError }: { onError: OnError }) {
  const params = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<PilotsResponse | null>(null);
  const [detail, setDetail] = useState<{ key: string; record: RunRecord } | null>(null);
  useEffect(() => { api<PilotsResponse>('/api/pilots').then(setData).catch(onError); }, [onError]);

  const pilot = data ? data.pilots.find((p) => p.id === params.pilot) ?? data.pilots[data.pilots.length - 1] : undefined;
  const index = params.index === undefined ? NaN : Number(params.index);
  const open = pilot && pilot.id === params.pilot && isArm(params.arm) && Number.isInteger(index) ? { arm: params.arm, index } : null;
  const openKey = pilot && open ? `${pilot.id}/${open.arm}/${open.index}` : null;

  useEffect(() => {
    if (!openKey) return undefined;
    let live = true;
    api<{ record: RunRecord }>(`/api/pilots/${openKey}`).then(({ record }) => { if (live) setDetail({ key: openKey, record }); }).catch(onError);
    return () => { live = false; };
  }, [openKey, onError]);

  if (!data) return <div className="card"><p className="muted">Loading the pilots…</p></div>;
  if (!pilot) return <div className="card"><p>No paired pilot has finished yet.</p></div>;
  const show = (arm: Arm, i: number) => navigate(`/results/${pilot.id}/${arm}/${i}`, { replace: true });
  const isOpen = (arm: Arm, i: number): boolean => open !== null && open.arm === arm && open.index === i;

  return (
    <>
      <div className="card">
        <div className="row spread">
          <h2>{pilot.label}</h2>
          {data.pilots.length > 1 ? (
            <select aria-label="Pilot" value={pilot.id} onChange={(e) => navigate(`/results/${e.target.value}`, { replace: true })}>
              {data.pilots.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
            </select>
          ) : null}
        </div>
        <p className="lead">The same {pilot.totals.untrained.cases} cases, controller, prompt and settings for both models. The only difference is the trained adapter. {pilot.note}</p>
        <p className="banner">{data.banner}</p>
        <TotalsTable t={pilot.totals} arms={pilot.arms} />
      </div>
      <div className="card">
        <h3>Case by case</h3>
        <p className="muted small">Open a run to read it step by step.</p>
        <div className="pairs-grid">
          <div className="pg-head">Case</div>{ARMS.map((a) => <div key={a} className="pg-head">{pilot.arms[a]}</div>)}
          {pilot.cases.map((c) => [
            <div key={`${c.case}-case`} className="pg-case"><strong>{c.company}</strong><span className="muted small">{variant(c.case)}</span></div>,
            ...ARMS.map((a) => <OutcomeCell key={`${c.case}-${a}`} o={c[a]} onOpen={() => show(a, c[a].index)} selected={isOpen(a, c[a].index)} />),
          ])}
        </div>
      </div>
      {open && detail && detail.key === openKey ? <Investigation record={detail.record} label={pilot.arms[open.arm]} runKey={openKey ?? undefined} /> : null}
    </>
  );
}
