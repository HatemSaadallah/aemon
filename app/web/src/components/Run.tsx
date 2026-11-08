import { useReducer, useRef, useState } from 'react';
import { Chip, type ChipKind } from '../Chip.tsx';
import { SHOCK, shortName, stageName, stopName, text } from '../labels.ts';
import type { Final, RunRecord } from '../types.ts';
import { groupsOf, stageOrderOf, useWorkflow } from '../workflow.ts';
import { gist, plural, refusedIn, type Visit, visits } from './calls.tsx';
import { AgentTrace } from './Trace.tsx';

// Model text is untrusted. Everything here is rendered as React text, never as HTML.


function furthestVisit(vs: Visit[], order: string[]): number {
  let best = -1, at = -1;
  vs.forEach((v, i) => { const rank = order.indexOf(v.stage ?? ''); if (rank >= best) { best = rank; at = i; } });
  return at;
}

function endMarker(record: RunRecord): { kind: ChipKind; icon: string; label: string } {
  if (!record.stop_reason) return { kind: 'warn', icon: '…', label: 'Running' };
  if (record.final) return { kind: 'good', icon: '✓', label: 'Finished' };
  const at = record.stopping_point && record.stopping_point.stage_at_stop;
  return { kind: 'bad', icon: '■', label: `${stopName(record.stop_reason)}${at && at !== 'done' ? `, in ${shortName(at)}` : ''}` };
}


// Which stage visits are open, per run, kept across live updates and re-renders.
interface TreeState { collapsed: Set<number>; opened: Set<number> }
const treeState = new Map<string, TreeState>();
const stateFor = (key: string): TreeState => {
  let state = treeState.get(key);
  if (!state) { state = { collapsed: new Set(), opened: new Set() }; treeState.set(key, state); }
  return state;
};

export function RunTree({ record, runKey, onlyLast = false }: { record: RunRecord; runKey: string; onlyLast?: boolean }) {
  const workflow = useWorkflow();
  const order = stageOrderOf(workflow), groups = groupsOf(workflow);
  const [, rerender] = useReducer((x: number) => x + 1, 0);
  const nodes = useRef<Record<number, HTMLLIElement | null>>({});
  const state = stateFor(runKey);
  const vs = visits(record);
  const top = furthestVisit(vs, order);
  const end = endMarker(record);
  // In the chat only the current stage starts open, so a long run stays readable; whatever the user toggles is kept.
  const isOpen = (i: number): boolean => (state.opened.has(i) ? true : state.collapsed.has(i) ? false : !onlyLast || i === vs.length - 1);
  const setOpen = (i: number, open: boolean): void => {
    if (open) { state.opened.add(i); state.collapsed.delete(i); } else { state.collapsed.add(i); state.opened.delete(i); }
  };
  const all = (open: boolean): void => { vs.forEach((_, i) => setOpen(i, open)); rerender(); };
  const pick = (i: number): void => {
    setOpen(i, true);
    rerender();
    requestAnimationFrame(() => {
      const node = nodes.current[i];
      if (node) { node.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); node.querySelector<HTMLButtonElement>('.visit-toggle')?.focus({ preventScroll: true }); }
    });
  };
  const safeKey = runKey.replace(/[^a-z0-9]/gi, '-');
  return (
    <div className="tree-wrap">
      <ol className="path" aria-label="Path through the stages">
        {vs.map((v, i) => {
          const refused = refusedIn(v.calls);
          return (
            <li key={i}>
              <button type="button" className={`pill${i === top ? ' furthest' : ''}${refused ? ' has-refused' : ''}`} onClick={() => pick(i)}
                title={`${stageName(v.stage)}: ${plural(v.calls.length, 'call')}${refused ? `, ${refused} refused` : ''}${i === top ? ' · furthest stage reached' : ''}`}>
                <span>{shortName(v.stage)}</span><span className="pill-n">{v.calls.length}</span>
                {refused ? <span className="pill-refused">⚠ {refused}</span> : null}
              </button>
            </li>
          );
        })}
        <li><span className={`pill end ${end.kind}`}>{end.icon} {end.label}</span></li>
      </ol>
      <div className="row">
        <button type="button" className="quiet-button" onClick={() => all(true)}>Expand all</button>
        <button type="button" className="quiet-button" onClick={() => all(false)}>Collapse all</button>
      </div>
      <ol className="tree">
        {vs.map((v, i) => {
          const refused = refusedIn(v.calls);
          const open = isOpen(i);
          const id = `visit-${safeKey}-${i}`;
          return (
            <li key={i} className={`visit g-${groups[v.stage ?? ''] || 'other'}${refused ? ' has-refused' : ''}`} ref={(n) => { nodes.current[i] = n; }}>
              <button type="button" className="visit-toggle" aria-expanded={open} aria-controls={id} onClick={() => { setOpen(i, !open); rerender(); }}>
                <span className="chev" aria-hidden="true">▸</span>
                <span className="visit-name">{stageName(v.stage)}</span>
                <span className="muted small">{plural(v.calls.length, 'call')}{refused ? `, ${refused} refused` : ''}</span>
                {i === top ? <Chip kind="quiet">furthest</Chip> : null}
              </button>
              <ol className="leaves" id={id} hidden={!open}>
                {v.calls.map(([call, n]) => {
                  const ok = call.accepted;
                  const reason = call.result && call.result.error;
                  const line = gist(call, record);
                  return (
                    <li key={n} className={`leaf${ok ? '' : ' refused'}${call.prefix ? ' replayed' : ''}`}>
                      <span className="leaf-icon" aria-hidden="true">{ok ? '✓' : '✕'}</span>
                      <div className="leaf-body">
                        <div className="leaf-head">
                          <span className="leaf-n">{n}</span><code className="tool-name">{text(call.name)}</code>
                          <span className="visually-hidden">{ok ? 'accepted' : 'refused'}</span>
                          {!ok ? <Chip kind="bad">Refused</Chip> : null}
                          {call.prefix ? <Chip kind="quiet">recorded teacher step</Chip> : null}
                          {call.harness ? <Chip kind="quiet">by the harness</Chip> : null}
                        </div>
                        {line ? <p className="leaf-gist">{line}</p> : null}
                        {!ok && reason ? <p className="reason">Why refused: {text(reason)}</p> : null}
                      </div>
                    </li>
                  );
                })}
              </ol>
            </li>
          );
        })}
        <li className={`visit tree-end ${end.kind}`}><span className="end-mark">{end.icon} {end.label}</span></li>
      </ol>
    </div>
  );
}

const VIEW_KEY = 'strategy-lab-run-view';
type View = 'visual' | 'tree';
const storedView = (): View => { try { return localStorage.getItem(VIEW_KEY) === 'tree' ? 'tree' : 'visual'; } catch { return 'visual'; } };

// The visual trace or the compact tree, remembered per browser. Used in the chat and on the Results page.
export function RunView({ record, runKey, live = false, title }: { record: RunRecord; runKey: string; live?: boolean; title?: string }) {
  const [mode, setMode] = useState<View>(storedView);
  const choose = (m: View): void => { setMode(m); try { localStorage.setItem(VIEW_KEY, m); } catch { /* storage may be blocked */ } };
  return (
    <div className="run-view">
      <div className="row spread">
        {title ? <h3>{title}</h3> : <span />}
        <div className="segmented" role="group" aria-label="View">
          <button type="button" aria-pressed={mode === 'visual'} onClick={() => choose('visual')}>Visual</button>
          <button type="button" aria-pressed={mode === 'tree'} onClick={() => choose('tree')}>Tree</button>
        </div>
      </div>
      {mode === 'visual' ? <AgentTrace record={record} runKey={runKey} live={live} /> : <RunTree record={record} runKey={runKey} onlyLast={live} />}
    </div>
  );
}

function StepsCard({ record, runKey }: { record: RunRecord; runKey: string }) {
  return <div className="card"><RunView record={record} runKey={runKey} title="What the agent did" /></div>;
}

export function Pairs({ rows }: { rows: [string, unknown][] }) {
  return <dl className="pairs">{rows.map(([k, v]) => [<dt key={`${k}-t`}>{k}</dt>, <dd key={`${k}-d`}>{text(v)}</dd>])}</dl>;
}

function Conclusion({ final }: { final: Final }) {
  const all: [string, unknown][] = [['Recommendation', final.recommendation], ['Next action', final.next_action], ['Favoured theory', final.favoured_theory], ['Customer', final.target_customer],
    ['Proposition', final.value_proposition], ['Uncertainty', final.uncertainty]];
  const rows = all.filter(([, v]) => v);
  return (
    <div className="card conclusion">
      <h3>Conclusion</h3>
      <Pairs rows={rows} />
      {Array.isArray(final.would_change_if) && final.would_change_if.length ? <>
        <p className="muted">Would change if</p>
        <ul>{final.would_change_if.map((x, i) => <li key={i}>{text(x)}</li>)}</ul>
      </> : null}
    </div>
  );
}

// A whole recorded investigation, as on the Results page.
export function Investigation({ record, label, runKey }: { record: RunRecord; label?: string; runKey?: string }) {
  const point = record.stopping_point || {};
  const shock = record.coverage && record.coverage.shock;
  const running = !record.stop_reason;
  const calls = record.calls || [];
  return (
    <>
      <div className="card">
        <div className="row spread"><h2>{text(record.company)}</h2>{label ? <Chip kind="quiet">{label}</Chip> : null}</div>
        <p className="lead">{text(record.question)}</p>
        <div className="chips">
          <Chip kind={running ? 'warn' : record.final ? 'good' : 'bad'}>{running ? 'Running' : stopName(record.stop_reason)}</Chip>
          {point.stage_at_stop && !record.final ? <Chip kind="quiet">{running ? `Now: ${stageName(point.stage_at_stop)}` : `Stopped while ${stageName(point.stage_at_stop).toLowerCase()}`}</Chip> : null}
          <Chip kind="quiet">{calls.length} steps, {calls.filter((c) => !c.accepted).length} refused</Chip>
          {shock ? <Chip kind="warn">Case includes {SHOCK[shock.direction] ?? 'simulated evidence'}</Chip> : null}
        </div>
        <p className="muted small">Written by the model. Refused steps were blocked by the harness and changed nothing.</p>
      </div>
      {record.final ? <Conclusion final={record.final} /> : null}
      <StepsCard record={record} runKey={runKey || `${record.case}/${label}`} />
    </>
  );
}
