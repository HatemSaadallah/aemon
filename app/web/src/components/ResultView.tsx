import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { clock, cut, day, kindOf, stageName, stopName, text } from '../labels.ts';
import type { Project, RunDetail, Source } from '../types.ts';
import { FollowUps } from './FollowUps.tsx';
import { Icon } from './Icon.tsx';
import { StepsList } from './StepsList.tsx';
import { InvTabs } from './InvTabs.tsx';
import { ReportBody } from './report/ReportBody.tsx';
import { StepDetail, WorkflowCanvas } from './Workflow.tsx';

// One finished (or stopped) investigation: its header and actions, then three views of the same record: the report
// (components/report/ReportBody.tsx), the Reasoning map and the sources.

interface Props {
  workspace: string;
  company: string;
  id: string;
  question: string;
  started: number | null;
  pinned: boolean;
  project: string | null;
  projects: Project[];
  detail: RunDetail;
  onPin: () => void;
  onMove: (project: string | null) => void;
  onDelete: () => void;
  onRerun: ((edit?: { question: string; depth: string; live: boolean; project: string | null; attachments?: string[] }) => void) | null;
  depths: { id: string; label: string; searches: number; turns: number }[];
  onContinue: (() => void) | null;
  onReinvestigate: ((context: string, attachments: string[]) => void) | null;
  busy: boolean;
  onError: (error: unknown) => void;
  runs: RunOf[];
  onOpenRun: (id: string) => void;
}
export interface RunOf { id: string; started: number | null; status: string; finished: boolean; recommendation: string | null; stop: string | null }

const PROV: Record<string, string> = { quote: 'Quoted from the source', reading: "Agent's reading", agent: "Agent's conclusion", simulated: 'Simulated' };
// Where a statement comes from, on every item of the report (docs/RELIABILITY_REPORT.md)
function Prov({ kind }: { kind: 'quote' | 'reading' | 'agent' | 'simulated' }) {
  return <span className={`prov prov-${kind}`}>{PROV[kind]}</span>;
}

function SourceCard({ source, n }: { source: Source; n: number }) {
  return (
    <li className="source-card" id={`src-${source.id}`}>
      <span className="src-n">{n}</span>
      <div>
        <p className="src-title">{source.url ? <a href={source.url} target="_blank" rel="noreferrer noopener">{text(source.title)}</a> : text(source.title)}</p>
        <p className="src-meta"><span className={`kind k-${source.class}`}>{kindOf(source.class)}</span>{source.date ? <span>{text(source.date)}</span> : null}</p>
        {source.excerpt ? <p className="src-quote">“{text(source.excerpt)}”</p> : null}
      </div>
    </li>
  );
}

export function ResultView(props: Props) {
  const { detail, question, company, workspace, id, projects } = props;
  const { record, metrics } = detail;
  const [step, setStep] = useState<number | null>(null);
  const location = useLocation();
  const [view, setView] = useState<'report' | 'sources'>(() => ((location.state as { view?: string } | null)?.view === 'sources' ? 'sources' : 'report'));
  useEffect(() => {  // opened from the map at one of its sections
    const key = (location.state as { section?: string } | null)?.section;
    if (key) window.setTimeout(() => document.getElementById(`rp-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 120);
  }, [location.state]);
  const [confirm, setConfirm] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [edit, setEdit] = useState({ question: text(question).replace(/ \(live web\)$/, ''), depth: detail.settings?.depth ?? record.depth ?? 'standard', live: Boolean(detail.settings?.live), project: props.project });
  const final = record.final;
  const names = Object.fromEntries(Object.keys(record.theories || {}).map((tid, i) => [tid, `Hypothesis ${i + 1}`]));
  const sources = Object.values(record.sources || {});
  const number = Object.fromEntries(sources.map((s, i) => [s.id, i + 1]));
  return (
    <article className="result report">
      <header className="ihead result-head">
        <div className="ihead-top">
          <Link to="/history" className="ihead-back">Investigations</Link><span className="muted">/</span>
          <span className={`chip ${final && !final.draft ? 'good' : 'warn'}`}>{final && !final.draft ? 'Finished' : final?.draft ? 'Draft answer' : stopName(record.stop_reason)}</span>
          <span className="muted small">{text(company)}{props.started ? ` · ${day(props.started)}` : ''}</span>
        </div>
        <h1 className="display ihead-q">{text(question)}</h1>
        <div className="result-actions">
          {record.depth && record.depth !== 'standard' ? <span className="status-chip quiet">{record.depth === 'quick' ? 'Quick' : 'Thorough'} depth</span> : null}
          {record.continued_after_turn ? <span className="status-chip quiet" title="It stopped early; you continued it from where it stopped.">Continued after step {record.continued_after_turn}</span> : null}
          {record.resumed_after_turn ? <span className="status-chip quiet" title="aemon restarted during this run; it replayed the saved steps and carried on.">Resumed after a restart</span> : null}
          {detail.memory_used.length ? <span className="status-chip quiet" title={detail.memory_used.join('\n')}>Used {detail.memory_used.length} memory note{detail.memory_used.length === 1 ? '' : 's'}</span> : null}
          <span className="grow" />
          <a className="button primary" href={`/api/workspaces/${workspace}/history/${id}/report.pdf`} download><Icon name="doc" size={15} /> Download PDF</a>
          {props.onRerun ? <button type="button" className="button" aria-expanded={rerunning} onClick={() => setRerunning(!rerunning)}><Icon name="refresh" size={15} /> Run again</button> : null}
          <button type="button" className="button" aria-pressed={props.pinned} onClick={props.onPin}><Icon name="pin" size={15} /> {props.pinned ? 'Pinned' : 'Pin'}</button>
          {projects.length ? (
            <label className="button select-button"><Icon name="folder" size={15} />
              <select aria-label="Project" value={props.project ?? ''} onChange={(e) => props.onMove(e.target.value || null)}>
                <option value="">No project</option>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
          ) : null}
          {confirm ? (
            <span className="confirm-inline">Delete for good? <button type="button" className="button danger" onClick={props.onDelete}>Delete</button><button type="button" className="button" onClick={() => setConfirm(false)}>Cancel</button></span>
          ) : <button type="button" className="button ghost" aria-label="Delete this investigation" onClick={() => setConfirm(true)}><Icon name="trash" size={15} /></button>}
        </div>
      </header>
      {rerunning && props.onRerun ? (
        <section className="rerun" aria-label="Run this investigation again">
          <div className="row spread"><p className="kicker">Run again</p><button type="button" className="button ghost small" aria-label="Close" onClick={() => setRerunning(false)}><Icon name="cross" size={14} /></button></div>
          <label className="field"><span>Question</span>
            <textarea rows={2} maxLength={400} value={edit.question} onChange={(e) => setEdit({ ...edit, question: e.target.value })} />
          </label>
          <div className="rerun-row">
            <div className="field"><span>Depth</span>
              <div className="depth" role="radiogroup" aria-label="Depth">
                {props.depths.map((d) => <button key={d.id} type="button" role="radio" aria-checked={edit.depth === d.id} title={`${d.searches} searches, up to ${d.turns} steps`} onClick={() => setEdit({ ...edit, depth: d.id })}>{d.label}</button>)}
              </div>
            </div>
            {projects.length ? (
              <label className="field"><span>Project</span>
                <select value={edit.project ?? ''} onChange={(e) => setEdit({ ...edit, project: e.target.value || null })}>
                  <option value="">No project</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </label>
            ) : null}
            <div className="field"><span>Sources</span>
              <button type="button" className="chip-button toggle-chip" aria-pressed={edit.live} onClick={() => setEdit({ ...edit, live: !edit.live })}
                title="Search the live web instead of the company's source library. Experimental: every page is saved, and labelled as unchecked.">
                <Icon name="search" size={13} /> Web search{edit.live ? ' on' : ''}
              </button>
            </div>
          </div>
          <div className="row">
            <button type="button" className="button primary" disabled={props.busy || !edit.question.trim()} onClick={() => props.onRerun?.({ ...edit, attachments: (detail.settings?.attachments ?? []).map((a) => a.id) })}>Start the new run</button>
            <span className="muted small">{edit.question.trim() === text(question).replace(/ \(live web\)$/, '').trim() ? 'It will appear as another run of this question, next to this one.' : 'A new question starts its own investigation.'}{props.busy ? ' Another investigation is running; start this one when it finishes.' : ''}</span>
          </div>
        </section>
      ) : null}

      {detail.settings?.context || detail.settings?.attachments?.length || detail.settings?.asked_online ? (
        <section className="used-strip">
          {detail.settings?.context ? <p><b>New information you gave this run:</b> {text(detail.settings.context)}</p> : null}
          {detail.settings?.attachments?.length ? <p><b>Your material:</b> {detail.settings.attachments.map((a) => text(a.name)).join(' · ')}</p> : null}
          {detail.settings?.asked_online ? <p><b>Searched the web</b> because you asked it to search online.</p> : null}
        </section>
      ) : null}
      {props.runs.length > 1 ? (
        <section className="runs-strip" aria-label="Runs of this question">
          <p className="kicker small">This question was run {props.runs.length} times</p>
          <table className="runs-table">
            <thead><tr><th>Run</th><th>When</th><th>Outcome</th><th>Recommendation</th></tr></thead>
            <tbody>{props.runs.map((r, i) => (
              <tr key={r.id} className={r.id === id ? 'current' : ''} onClick={() => { if (r.id !== id) props.onOpenRun(r.id); }}>
                <td><button type="button" className="link" aria-current={r.id === id ? 'true' : undefined} onClick={(e) => { e.stopPropagation(); if (r.id !== id) props.onOpenRun(r.id); }}>Run {props.runs.length - i}{r.id === id ? ' (this one)' : ''}</button></td>
                <td>{clock(r.started)}</td>
                <td><span className={`status-chip ${r.finished ? 'good' : 'warn'}`}>{r.finished ? 'Finished' : stopName(r.stop || r.status)}</span></td>
                <td className="muted">{r.recommendation ? cut(r.recommendation).slice(0, 140) + (r.recommendation.length > 140 ? '…' : '') : '—'}</td>
              </tr>
            ))}</tbody>
          </table>
          {props.runs.filter((r) => r.recommendation).length > 1 && new Set(props.runs.map((r) => r.recommendation).filter(Boolean)).size === 1 ? <p className="muted small">Every finished run reached the same recommendation.</p> : null}
        </section>
      ) : null}

      <InvTabs id={id} active={view} sources={sources.length} onPick={setView} />
      {view === 'sources' ? (
        <section className="report-section"><ol className="sources">{sources.map((src, i) => <SourceCard key={src.id} source={src} n={i + 1} />)}</ol></section>
      ) : (
      <ReportBody record={record} metrics={metrics} names={names} number={number}
        stopped={(
              <div className="exec-card stopped">
                <p className="kicker">No recommendation</p>
                <p className="answer small-answer">The investigation stopped before recommending ({stopName(record.stop_reason).replace(/^Stopped early: /, '')}){record.stopping_point?.stage_at_stop ? `, while ${stageName(record.stopping_point.stage_at_stop).toLowerCase()}` : ''}. What it found up to then is below.</p>
                {record.position ? <p className="next"><b>Its interim view</b> <Prov kind="agent" />: {cut(record.position.recommendation)}</p> : null}
                <div className="row">
                  {props.onContinue ? <button type="button" className="button primary" disabled={props.busy} onClick={props.onContinue}><Icon name="zap" size={15} /> Continue from here</button> : null}
                  {props.onRerun ? <button type="button" className="button" onClick={() => setRerunning(true)}><Icon name="refresh" size={15} /> Run again</button> : null}
                </div>
                {props.onContinue ? <p className="muted small">Continue picks up exactly where it stopped, with up to 200 more steps and help for the step it was stuck on.</p> : null}
              </div>
        )}>
        {{
          method: (<>
            <h2 className="rp-h">Method</h2>
            <details className="block how">
              <summary><span>How the agent got here</span><span className="muted small">{metrics.steps.total} steps · {metrics.steps.searches} searches · {metrics.steps.reads} sources read{metrics.steps.corrected ? ` · ${metrics.steps.corrected} corrected by the checker` : ''}</span></summary>
              <p className="muted small">Every action the agent took, step by step. Open a step to see its actions, and an action to see exactly what it read, quoted or decided.</p>
              <StepsList record={record} />
              <details className="diagram" onToggle={(e) => { if (!(e.target as HTMLDetailsElement).open) setStep(null); }}>
                <summary className="small">Show as a diagram</summary>
                <div className="how-canvas"><WorkflowCanvas record={record} question={question} selected={step} onSelect={setStep} /></div>
                {step ? <div className="step-detail"><div className="row spread"><b>Action {step}</b><button type="button" className="button ghost" onClick={() => setStep(null)}>Close</button></div><StepDetail record={record} n={step} /></div> : null}
              </details>
            </details>
          </>),
          followups: (
      <FollowUps workspace={workspace} id={id} project={props.project} initial={detail.followups} suggestions={detail.suggestions} sources={record.sources || {}} number={number} onError={props.onError}
        onReinvestigate={props.onReinvestigate} busy={props.busy} />
          ),
        }}
      </ReportBody>
      )}
    </article>
  );
}
