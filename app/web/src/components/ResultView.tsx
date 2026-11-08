import { useState } from 'react';
import { cut, day, euros, kindOf, stopName, text } from '../labels.ts';
import type { Assessment, Project, RunDetail, Source } from '../types.ts';
import { BeliefChart, Bullet, EvidenceBars, money, SourceMix, weeks } from './charts.tsx';
import { FollowUps } from './FollowUps.tsx';
import { Icon } from './Icon.tsx';
import { StepDetail, WorkflowCanvas } from './Workflow.tsx';

// One finished (or stopped) investigation, answer first: the recommendation and how sure it is, the numbers, the
// explanations compared, the sources, the test, and only then how it got there (docs/DESIGN_RESEARCH.md, section 4c).

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
  onRerun: (() => void) | null;
  onError: (error: unknown) => void;
}

type Level = 'High' | 'Moderate' | 'Low';
const ACTION: Record<Level, string> = {
  High: 'The evidence is consistent: check the quotes, then act.',
  Moderate: 'Reasonable to act on small, reversible steps.',
  Low: 'Treat it as a hypothesis: run the test before committing.',
};

function confidence(detail: RunDetail): { level: Level; why: string } {
  const lead = detail.metrics.beliefs.find((b) => b.favoured);
  const belief = lead ? lead.after ?? lead.before : null;
  const support = detail.metrics.evidence.find((e) => e.id === lead?.id)?.independent_supports ?? 0;
  const level: Level = support >= 2 && belief === 'very likely' ? 'High' : support >= 2 && belief === 'likely' ? 'Moderate' : 'Low';
  const why = lead ? `Leading explanation judged ${belief ?? 'not stated'}, with ${support} independent source${support === 1 ? '' : 's'} in support.` : 'No leading explanation was stated.';
  return { level, why };
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
  const [open, setOpen] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const final = record.final;
  const names = Object.fromEntries(Object.keys(record.theories || {}).map((tid, i) => [tid, `Explanation ${i + 1}`]));
  const sources = Object.values(record.sources || {});
  const number = Object.fromEntries(sources.map((s, i) => [s.id, i + 1]));
  const assessments: Assessment[] = record.assessments || [];
  const test = metrics.test;
  const sure = final ? confidence(detail) : null;
  const independent = metrics.sources.find((s) => s.class === 'verified_observation')?.count ?? 0;
  const lead = metrics.beliefs.find((b) => b.favoured);

  return (
    <article className="result">
      <header className="result-head">
        <p className="eyebrow">{text(company)}{props.started ? ` · ${day(props.started)}` : ''}</p>
        <h1>{text(question)}</h1>
        <div className="result-actions">
          <span className={`status-chip ${final ? 'good' : 'warn'}`}>{final ? 'Finished' : stopName(record.stop_reason)}</span>
          {detail.memory_used.length ? <span className="status-chip quiet" title={detail.memory_used.join('\n')}>Used {detail.memory_used.length} memory note{detail.memory_used.length === 1 ? '' : 's'}</span> : null}
          <span className="grow" />
          <a className="button primary" href={`/api/workspaces/${workspace}/history/${id}/report.pdf`} download><Icon name="doc" size={15} /> Download PDF</a>
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

      {final ? (
        <section className="answer-card">
          <p className="kicker">Our recommendation</p>
          <p className="answer">{cut(final.recommendation)}</p>
          {sure ? (
            <div className={`confidence c-${sure.level.toLowerCase()}`}>
              <span className="conf-chip" title="High: leading explanation very likely and at least two independent sources support it. Moderate: likely, with at least two. Low: anything else.">{sure.level} confidence</span>
              <span>{ACTION[sure.level]} <span className="muted">{sure.why}</span></span>
            </div>
          ) : null}
          {final.next_action ? <p className="next"><b>Next step:</b> {cut(final.next_action)}</p> : null}
          {Array.isArray(final.would_change_if) && final.would_change_if.length ? (
            <div className="change"><p className="kicker small">What would change our mind</p><ul>{final.would_change_if.slice(0, 3).map((x, i) => <li key={i}>{cut(x)}</li>)}</ul></div>
          ) : null}
        </section>
      ) : (
        <section className="answer-card stopped">
          <p className="kicker">No recommendation yet</p>
          <p className="answer small-answer">It stopped before recommending{record.stopping_point?.stage_at_stop ? ', while it was working on the evidence' : ''}. Here is what it found up to that point.</p>
          {record.position ? <p className="next"><b>Its interim view:</b> {cut(record.position.recommendation)}</p> : null}
          {props.onRerun ? <button type="button" className="button primary" onClick={props.onRerun}><Icon name="refresh" size={15} /> Run again</button> : null}
        </section>
      )}

      <section className="tiles" aria-label="At a glance">
        <div className="tile"><b>{metrics.beliefs.length}</b><span>explanations compared</span></div>
        <div className="tile"><b>{sources.length}</b><span>sources · {independent} independent</span></div>
        <div className="tile"><b>{assessments.length}</b><span>pieces of evidence weighed</span></div>
        <div className="tile"><b>{test && !test.declined && typeof test.cost === 'number' ? euros(test.cost) : test?.declined ? 'No test' : '—'}</b><span>{test && !test.declined && test.budget ? `test, of ${euros(test.budget)} budget` : test?.declined ? 'judged not worth it' : 'no test designed'}</span></div>
      </section>

      {metrics.beliefs.length ? (
        <section className="block">
          <h2>Why customers might buy: the explanations compared</h2>
          {lead ? <p className="lead-line">Leading: <b>{names[lead.id]}</b>. {cut(lead.claim)}</p> : null}
          <BeliefChart rows={metrics.beliefs} scale={metrics.scale} names={names} />
          <EvidenceBars rows={metrics.evidence} names={names} />
          <div className="explanations">
            {Object.entries(record.theories || {}).map(([tid, t]) => {
              const quotes = assessments.filter((a) => a.theory_id === tid);
              const isOpen = open === tid;
              return (
                <div key={tid} className={`explanation${lead?.id === tid ? ' leading' : ''}`}>
                  <button type="button" className="exp-head" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : tid)}>
                    <span className="exp-name">{names[tid]}{lead?.id === tid ? <span className="lead-chip">★ Leading</span> : null}</span>
                    <span className="exp-claim">{cut(t.claim)}</span>
                    <span className="exp-count">{quotes.length} source{quotes.length === 1 ? '' : 's'} weighed ▾</span>
                  </button>
                  {isOpen ? (
                    <div className="exp-body">
                      <dl>
                        {t.who_benefits ? <><dt>Who it is for</dt><dd>{cut(t.who_benefits)}</dd></> : null}
                        {t.why_behaviour_changes ? <><dt>Why they would change</dt><dd>{cut(t.why_behaviour_changes)}</dd></> : null}
                        {t.how_value_is_captured ? <><dt>How the company earns from it</dt><dd>{cut(t.how_value_is_captured)}</dd></> : null}
                      </dl>
                      {quotes.length ? <ul className="quotes">{quotes.map((a, i) => (
                        <li key={i} className={`quote q-${a.direction}`}>
                          <span className="q-tag">{a.direction === 'supports' ? '+ for' : a.direction === 'contradicts' ? '− against' : 'no bearing'}</span>
                          <span>“{text(a.quote)}” <a className="cite" href={`#src-${a.evidence_id}`}>[{number[a.evidence_id] ?? '?'}]</a>{a.does_not_show ? <span className="muted small block">Does not show: {cut(a.does_not_show)}</span> : null}</span>
                        </li>
                      ))}</ul> : <p className="muted small">No source was weighed against this explanation.</p>}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {test && !test.declined ? (
        <section className="block">
          <h2>The test we propose</h2>
          <p className="test-name">{text(test.name)}</p>
          <p>{cut(test.method)}</p>
          <div className="bullets">
            <Bullet value={test.cost} limit={test.budget} label="Cost" format={money} />
            <Bullet value={test.weeks} limit={test.max_weeks} label="Time" format={weeks} />
          </div>
          <dl className="test-facts">
            {test.sample ? <><dt>Who takes part</dt><dd>{cut(test.sample)}</dd></> : null}
            {test.measure ? <><dt>What is measured</dt><dd>{cut(test.measure)}</dd></> : null}
          </dl>
          {test.predictions && Object.keys(test.predictions).length ? (
            <table className="predictions"><thead><tr><th>If this is right…</th><th>…we would expect</th></tr></thead>
              <tbody>{Object.entries(test.predictions).map(([tid, p]) => <tr key={tid}><td>{names[tid] ?? tid}</td><td>{cut(p)}</td></tr>)}</tbody></table>
          ) : null}
          {test.rule ? <div className="rule"><p className="kicker small">How we will decide</p><p>{cut(test.rule)}</p></div> : null}
        </section>
      ) : test?.declined ? (
        <section className="block"><h2>Why a test is not worth it here</h2><p>{cut(test.reason)}</p></section>
      ) : null}

      {sources.length ? (
        <section className="block">
          <h2>Where the evidence came from</h2>
          <SourceMix sources={metrics.sources} />
          <ol className="sources">{sources.map((s, i) => <SourceCard key={s.id} source={s} n={i + 1} />)}</ol>
        </section>
      ) : null}

      <details className="block how" onToggle={(e) => { if (!(e.target as HTMLDetailsElement).open) setStep(null); }}>
        <summary><h2>How we got here</h2><span className="muted small">{metrics.steps.total} steps · {metrics.steps.searches} searches · {metrics.steps.reads} sources read{metrics.steps.corrected ? ` · ${metrics.steps.corrected} corrected by the checker` : ''}</span></summary>
        <p className="muted small">Every step the assistant took. A step the checker did not accept changed nothing; the assistant then tried again. Click a step to see it.</p>
        <div className="how-canvas"><WorkflowCanvas record={record} question={question} selected={step} onSelect={setStep} /></div>
        {step ? <div className="step-detail"><div className="row spread"><b>Step {step}</b><button type="button" className="button ghost" onClick={() => setStep(null)}>Close</button></div><StepDetail record={record} n={step} /></div> : null}
      </details>

      <FollowUps workspace={workspace} id={id} project={props.project} initial={detail.followups} suggestions={detail.suggestions} sources={record.sources || {}} number={number} onError={props.onError} />
    </article>
  );
}
