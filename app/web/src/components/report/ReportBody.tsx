import { useEffect, useMemo, useState } from 'react';
import { cut, euros, kindOf, stageName, stopName, text } from '../../labels.ts';
import type { Assessment, Metrics, RunRecord, Source } from '../../types.ts';
import { Icon } from '../Icon.tsx';

// The report body, as a consulting deliverable: conclusion and its reasons first, hypotheses side by side, one card
// per source with the quote kept apart from the agent's reading, the test as a proposal (nothing in it was measured),
// warnings beside what they qualify, and a contextual sidebar that inspects a citation without moving the page.
// Presentation only: every value comes from the run record and its metrics, unchanged.

type Flag = { check: string; label: string; detail?: string };
const SECTIONS: [string, string][] = [['summary', 'Summary'], ['hypotheses', 'Hypotheses'], ['evidence', 'Evidence'], ['experiment', 'Experiment'], ['method', 'Method']];
// Which warnings qualify which part of the report
const AT: Record<string, string> = { no_invented_numbers: 'summary', evidence_numbers: 'summary', evidence_support: 'summary', evidence_company: 'summary', evidence_late: 'evidence', evidence_offering: 'summary', experiment: 'experiment' };
const DIR: Record<string, string> = { supports: 'Supports', contradicts: 'Contradicts', neutral: 'No bearing' };
const dateOf = (d: unknown): string | null => (/^\d{4}/.test(text(d)) ? text(d).slice(0, 10) : null);

// The same quote weighed for several hypotheses is shown once, with each hypothesis's reading under it
function Uses({ uses, names }: { uses: Assessment[]; names: Record<string, string> }) {
  const groups: { quote: string; items: Assessment[] }[] = [];
  for (const x of uses) { const g = groups.find((y) => y.quote === text(x.quote)); if (g) g.items.push(x); else groups.push({ quote: text(x.quote), items: [x] }); }
  return (
    <>{groups.map((g, i) => {
      const lead = g.items.some((x) => x.direction === 'contradicts') ? 'contradicts' : g.items.some((x) => x.direction === 'supports') ? 'supports' : 'neutral';
      return (
        <div key={i} className={`rp-use u-${lead}`}>
          <blockquote>“{g.quote}”</blockquote>
          {g.items.map((x, j) => (
            <div key={j} className="rp-reading-row">
              <p className="rp-use-head"><span className={`rp-dir d-${x.direction}`}>{DIR[x.direction]}</span> {names[x.theory_id] ?? x.theory_id}</p>
              {x.does_not_show ? <p className="rp-reading"><span className="prov prov-reading">Agent's reading</span> Does not show: {cut(x.does_not_show)}</p> : null}
            </div>
          ))}
        </div>
      );
    })}</>
  );
}

function Warn({ flags }: { flags: Flag[] }) {
  if (!flags.length) return null;
  return (
    <div className="rp-warn" role="note"><Icon name="alert" size={15} />
      <div><b>Check before relying on this</b><ul>{flags.map((f) => <li key={f.check}>{f.label}{f.detail ? <span className="muted"> ({f.detail})</span> : null}</li>)}</ul></div>
    </div>
  );
}

function Cite({ id, n, onInspect }: { id: string; n: number | undefined; onInspect: (id: string) => void }) {
  return <button type="button" className="rp-cite" onClick={() => onInspect(id)} aria-label={`Inspect source ${n ?? ''}`}>{n ?? '?'}</button>;
}

function Origin({ s }: { s: Source | undefined }) {
  if (!s) return null;
  const sim = s.class === 'synthetic' || s.simulated;
  return <span className={`rp-origin o-${sim ? 'synthetic' : s.class}`}>{sim ? 'Simulated, not evidence' : kindOf(s.class)}</span>;
}

export function ReportBody({ record, metrics, names, number, stopped, children }: { record: RunRecord; metrics: Metrics; names: Record<string, string>; number: Record<string, number>; stopped: React.ReactNode; children: { experimentExtra?: React.ReactNode; method: React.ReactNode; followups: React.ReactNode } }) {
  const [inspect, setInspect] = useState<string | null>(null);
  const [hyp, setHyp] = useState<string | null>(null);
  const [dir, setDir] = useState<'all' | 'supports' | 'contradicts' | 'neutral'>('all');
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const final = record.final;
  const a: Assessment[] = record.assessments ?? [];
  const sources = record.sources ?? {};
  const flags: Flag[] = record.answer_flags ?? [];
  const flagsAt = (where: string): Flag[] => flags.filter((f) => (AT[f.check] ?? 'summary') === where);
  const favoured = final?.favoured_theory ?? record.position?.favoured_theory;
  const theories = Object.entries(record.theories ?? {});
  const test = metrics.test;
  const sure = metrics.confidence;
  const count = (tid: string | null, d: string) => a.filter((x) => (tid === null || x.theory_id === tid) && x.direction === d).length;
  const forFav = a.filter((x) => x.theory_id === favoured && x.direction === 'supports');

  // A citation anywhere on the page opens the inspector instead of jumping
  useEffect(() => {
    const onOpen = (e: Event): void => { e.preventDefault(); setInspect((e as CustomEvent<string>).detail); };
    window.addEventListener('open-source', onOpen);
    return () => window.removeEventListener('open-source', onOpen);
  }, []);
  useEffect(() => { const esc = (e: KeyboardEvent): void => { if (e.key === 'Escape') setInspect(null); }; window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc); }, []);

  // One card per source, its uses grouped under it
  const cards = useMemo(() => {
    const by = new Map<string, Assessment[]>();
    for (const x of a) if ((hyp === null || x.theory_id === hyp) && (dir === 'all' || x.direction === dir)) by.set(x.evidence_id, [...(by.get(x.evidence_id) ?? []), x]);
    const rank = (xs: Assessment[]) => (xs.some((x) => x.direction === 'contradicts') ? 0 : xs.some((x) => x.direction === 'supports') ? 1 : 2);
    return [...by.entries()].sort((p, q) => rank(p[1]) - rank(q[1]) || (number[p[0]] ?? 0) - (number[q[0]] ?? 0));
  }, [a, hyp, dir, number]);
  const belief = (tid: string) => metrics.beliefs.find((b) => b.id === tid);
  const go = (key: string) => document.getElementById(`rp-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  const opposingNone = count(null, 'contradicts') === 0;

  // A confidence check that passes only because nothing was weighed says so
  const checkNote = (label: string): string | null => {
    if (/contradicts it/.test(label) && count(favoured ?? null, 'contradicts') === 0) return 'nothing was weighed against it, so this shows an absence of testing, not of contrary evidence';
    if (/were weighed for it/.test(label)) { const s = count(favoured ?? null, 'supports'); return `${s} of them weighed as supporting`; }
    return null;
  };

  const src = inspect ? sources[inspect] : undefined;
  const uses = inspect ? a.filter((x) => x.evidence_id === inspect) : [];

  return (
    <div className={`rp${inspect ? ' inspecting' : ''}`}>
      <nav className="rp-nav" aria-label="Report sections">
        <ol>{SECTIONS.filter(([k]) => k !== 'experiment' || test).map(([k, label], i) => <li key={k}><button type="button" onClick={() => go(k)}><span>{i + 1}</span>{label}</button></li>)}</ol>
      </nav>

      <div className="rp-main">
        <section id="rp-summary" className="rp-section">
          {final ? (
            <>
              <p className="rp-kicker">{final.draft ? 'Draft recommendation' : 'Recommendation'} <span className="prov prov-agent">Agent's conclusion</span></p>
              {final.draft ? <p className="rp-draft">The investigation stopped early{final.stopped_because ? ` because ${final.stopped_because}` : ''}; this was written from what it had found.</p> : null}
              <h2 className="rp-conclusion">{cut(final.recommendation)}</h2>
              {sure ? <p className="rp-conf"><span className={`rp-dot c-${sure.level.toLowerCase()}`} aria-hidden="true" />{sure.level} confidence ({sure.score} of {sure.out_of} checks) · {sure.action}</p> : null}
              <Warn flags={flagsAt('summary')} />
              <div className="rp-three">
                <div>
                  <h3>Why</h3>
                  {favoured && record.theories?.[favoured] ? <p className="rp-fav"><span className="muted small">Favoured: {names[favoured]}</span><br />{cut(record.theories[favoured]?.claim)}</p> : null}
                  {forFav.length ? (
                    <ul className="rp-reasons">{forFav.slice(0, 3).map((x, i) => <li key={i}>“{cut(x.quote)}” <Cite id={x.evidence_id} n={number[x.evidence_id]} onInspect={setInspect} /><span className="muted small rp-note">Weighed by the agent as supporting; quoted exactly.</span></li>)}</ul>
                  ) : <p className="rp-gap"><Icon name="alert" size={13} /> No source was weighed as supporting {favoured ? names[favoured] : 'the favoured hypothesis'}{count(favoured ?? null, 'neutral') ? ` (${count(favoured ?? null, 'neutral')} were weighed as having no bearing)` : ''}. The recommendation rests on the agent's reasoning, not on cited support.</p>}
                </div>
                <div>
                  <h3>What is uncertain</h3>
                  {final.uncertainty ? <p>{cut(final.uncertainty)}</p> : <p className="muted">Not stated.</p>}
                  {Array.isArray(final.would_change_if) && final.would_change_if.length ? <><p className="rp-sub">Would change if</p><ul className="rp-list">{final.would_change_if.map((x, i) => <li key={i}>{cut(x)}</li>)}</ul></> : null}
                  {opposingNone ? <p className="rp-gap"><Icon name="alert" size={13} /> No evidence was weighed against any hypothesis. That is a gap in the investigation, not proof that none exists.</p> : null}
                </div>
                <div>
                  <h3>Next step</h3>
                  {final.next_action ? <p>{cut(final.next_action)}</p> : <p className="muted">Not stated.</p>}
                  {test && !test.declined ? <button type="button" className="rp-link" onClick={() => go('experiment')}>Proposed test: {text(test.name)}{typeof test.cost === 'number' ? ` · ${euros(test.cost)} proposed` : ''} →</button> : test?.declined ? <p className="muted small">The agent declined to test.</p> : null}
                </div>
              </div>
              {final.company_position ? <dl className="rp-two"><div><dt>Where the company stands</dt><dd>{cut(final.company_position)}</dd></div></dl> : null}
              {final.target_customer || final.value_proposition ? (
                <dl className="rp-two">
                  {final.target_customer ? <div><dt>Who it is for</dt><dd>{cut(final.target_customer)}</dd></div> : null}
                  {final.value_proposition ? <div><dt>Value proposition</dt><dd>{cut(final.value_proposition)}</dd></div> : null}
                </dl>
              ) : null}
            </>
          ) : stopped}
          {sure ? (
            <details className="rp-checks"><summary>How the confidence label was set</summary>
              <ul>{sure.checks.map((c) => { const note = checkNote(c.label); return <li key={c.label} className={c.passed ? 'pass' : 'fail'}><span aria-hidden="true">{c.passed ? '✓' : '✗'}</span> {c.label}{note ? <span className="muted"> · {note}</span> : null}</li>; })}</ul>
              <p className="muted small">{sure.rule} The label summarises the agent's own record; it is not a probability and not an independent check.</p>
            </details>
          ) : null}
        </section>

        {theories.length ? (
          <section id="rp-hypotheses" className="rp-section">
            <h2 className="rp-h">Hypotheses compared</h2>
            <p className="rp-lede">The rival explanations of why customers would buy, as the agent wrote them.</p>
            <div className="rp-hyp-cards">{theories.map(([tid, t]) => (
              <article key={tid} className="rp-hyp-card">
                <p className="rp-hyp-name">{names[tid]}{tid === favoured ? <span className="rp-fav-tag">Favoured</span> : null}</p>
                <p className="rp-claim">{cut(t.claim)}</p>
                <dl>
                  {(['who_benefits', 'why_behaviour_changes', 'how_value_is_captured'] as const).map((f) => text((t as Record<string, unknown>)[f]) ? <div key={f}><dt>{f === 'who_benefits' ? 'Who it is for' : f === 'why_behaviour_changes' ? 'Why they would change' : 'How the company earns'}</dt><dd>{cut((t as Record<string, unknown>)[f])}</dd></div> : null)}
                  <div><dt>Evidence weighed</dt><dd><span className="t-for">{count(tid, 'supports')} for</span> · <span className="t-against">{count(tid, 'contradicts')} against</span> · {count(tid, 'neutral')} no bearing</dd></div>
                </dl>
              </article>
            ))}</div>
            <div className="rp-table-wrap">
              <table className="rp-compare">
                <thead><tr><th scope="col" className="rl" />{theories.map(([tid]) => <th key={tid} scope="col">{names[tid]}{tid === favoured ? <span className="rp-fav-tag">Favoured</span> : null}</th>)}</tr></thead>
                <tbody>
                  <tr><th scope="row" className="rl">Claim</th>{theories.map(([tid, t]) => <td key={tid} className="rp-claim">{cut(t.claim)}</td>)}</tr>
                  {(['who_benefits', 'why_behaviour_changes', 'how_value_is_captured'] as const).map((f) => (
                    <tr key={f}><th scope="row" className="rl">{f === 'who_benefits' ? 'Who it is for' : f === 'why_behaviour_changes' ? 'Why they would change' : 'How the company earns'}</th>
                      {theories.map(([tid, t]) => { const k = `${tid}:${f}`; const v = text((t as Record<string, unknown>)[f]); const long = v.length > 160; return (
                        <td key={tid}>{v ? <>{long && !open[k] ? `${v.slice(0, 150).trimEnd()}…` : cut(v)}{long ? <button type="button" className="rp-more" onClick={() => setOpen((o) => ({ ...o, [k]: !o[k] }))}>{open[k] ? 'Less' : 'More'}</button> : null}</> : <span className="muted">—</span>}</td>
                      ); })}</tr>
                  ))}
                  <tr><th scope="row" className="rl">Agent's belief</th>{theories.map(([tid]) => { const b = belief(tid); return <td key={tid}>{b?.before || b?.after ? <>{text(b.before ?? '—')} → <b>{text(b.after ?? b.before ?? '—')}</b></> : <span className="muted">not stated</span>}<span className="muted small rp-note">its own five-step scale</span></td>; })}</tr>
                  <tr><th scope="row" className="rl">Evidence weighed</th>{theories.map(([tid]) => (
                    <td key={tid}><span className="t-for">{count(tid, 'supports')} for</span> · <span className="t-against">{count(tid, 'contradicts')} against</span> · <span className="muted">{count(tid, 'neutral')} no bearing</span>
                      <button type="button" className="rp-more" onClick={() => { setHyp(tid); setDir('all'); go('evidence'); }}>See</button></td>
                  ))}</tr>
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        <section id="rp-evidence" className="rp-section">
          <h2 className="rp-h">Evidence</h2>
          <div className="rp-filters">
            <div className="segmented small" role="radiogroup" aria-label="Hypothesis">
              <button type="button" role="radio" aria-checked={hyp === null} onClick={() => setHyp(null)}>All hypotheses</button>
              {theories.map(([tid]) => <button key={tid} type="button" role="radio" aria-checked={hyp === tid} onClick={() => setHyp(tid)}>{names[tid]}</button>)}
            </div>
            <div className="segmented small" role="radiogroup" aria-label="Direction">
              {(['all', 'supports', 'contradicts', 'neutral'] as const).map((d) => <button key={d} type="button" role="radio" aria-checked={dir === d} onClick={() => setDir(d)}>{d === 'all' ? 'All' : `${DIR[d]} (${count(hyp, d)})`}</button>)}
            </div>
          </div>
          {opposingNone && a.length ? <p className="rp-gap wide"><Icon name="alert" size={13} /> The agent weighed no source against any hypothesis. Opposing evidence may exist in the library; it was not looked at here.</p> : null}
          <Warn flags={flagsAt('evidence')} />
          {cards.length ? (
            <ol className="rp-sources">{cards.map(([id, uses]) => { const s = sources[id]; return (
              <li key={id} className="rp-card">
                <header>
                  <span className="rp-n">{number[id] ?? '?'}</span>
                  <div className="rp-card-head">
                    <button type="button" className="rp-card-title" onClick={() => setInspect(id)}>{text(s?.title ?? id)}</button>
                    <p className="rp-meta"><Origin s={s} />{dateOf(s?.date) ? <span>{dateOf(s?.date)}</span> : <span className="muted">date unknown</span>}{s?.url ? <a href={s.url} target="_blank" rel="noreferrer noopener">Original <Icon name="link" size={12} /></a> : null}</p>
                  </div>
                </header>
                <Uses uses={uses} names={names} />
                {s?.class === 'company_claim' ? <p className="rp-caveat">The company's own words: not independent evidence of demand.</p> : null}
              </li>
            ); })}</ol>
          ) : <p className="muted">{a.length ? 'No source matches these filters.' : 'No source was weighed against a hypothesis.'}</p>}
        </section>

        {test ? (
          <section id="rp-experiment" className="rp-section">
            <h2 className="rp-h">{test.declined ? 'Experiment: declined' : 'Proposed experiment'}</h2>
            {test.declined ? <p className="rp-prose"><span className="prov prov-agent">Agent's decision</span> {cut(test.reason)}</p> : (
              <div className="rp-test">
                <p className="rp-test-name">{text(test.name)}</p>
                <p className="rp-status"><b>Status:</b> proposed by the agent, not run. There are no observed results.</p>
                <Warn flags={flagsAt('experiment')} />
                {test.method ? <p className="rp-prose">{cut(test.method)}</p> : null}
                <p className="rp-sub">Proposed parameters <span className="muted">(the agent's choices, not measurements)</span></p>
                <dl className="rp-params">
                  <div><dt>Cost</dt><dd>{typeof test.cost === 'number' ? euros(test.cost) : '—'}{typeof test.budget === 'number' ? <span className="muted"> of a {euros(test.budget)} budget</span> : null}</dd></div>
                  <div><dt>Duration</dt><dd>{typeof test.weeks === 'number' ? `${test.weeks} weeks` : '—'}{typeof test.max_weeks === 'number' ? <span className="muted"> of {test.max_weeks} allowed</span> : null}</dd></div>
                  {test.sample ? <div className="wide"><dt>Sample</dt><dd>{cut(test.sample)}</dd></div> : null}
                  {test.measure ? <div className="wide"><dt>Measure</dt><dd>{cut(test.measure)}</dd></div> : null}
                </dl>
                {test.predictions && Object.keys(test.predictions).length ? (
                  <>
                    <p className="rp-sub">What each hypothesis predicts</p>
                    <table className="rp-pred"><tbody>{Object.entries(test.predictions).map(([tid, p]) => <tr key={tid}><th scope="row">{names[tid] ?? tid}</th><td>{cut(p)}</td></tr>)}</tbody></table>
                  </>
                ) : null}
                {test.rule ? <><p className="rp-sub">Decision rule</p><p className="rp-prose">{cut(test.rule)}</p></> : null}
                <p className="muted small">The mechanical experiment check is lenient: most tests it accepts fail stricter design screens (a test that varies only the message cannot separate why people would buy).</p>
              </div>
            )}
            {children.experimentExtra}
          </section>
        ) : null}

        <section id="rp-method" className="rp-section">{children.method}</section>
        <section id="rp-followups" className="rp-section"><h2 className="rp-h">Ask about this report</h2>{children.followups}</section>
      </div>

      <aside className={`rp-aside${inspect ? ' open' : ''}`} aria-label={inspect ? 'Source' : 'At a glance'}>
        {inspect ? (
          <div className="rp-inspect">
            <div className="rp-aside-head"><span className="eyebrow">Source {number[inspect] ?? ''}</span><button type="button" className="button ghost small" onClick={() => setInspect(null)} aria-label="Close the source"><Icon name="cross" size={14} /></button></div>
            {src ? (
              <>
                <p className="rp-aside-title">{src.url ? <a href={src.url} target="_blank" rel="noreferrer noopener">{text(src.title)}</a> : text(src.title)}</p>
                <p className="rp-meta"><Origin s={src} />{dateOf(src.date) ? <span>{dateOf(src.date)}</span> : <span className="muted">date unknown</span>}</p>
                {src.excerpt ? <><p className="rp-sub">What the source says</p><blockquote className="rp-excerpt">“{text(src.excerpt)}”</blockquote></> : null}
                <p className="rp-sub">How the agent used it</p>
                {uses.length ? <Uses uses={uses} names={names} /> : <p className="muted small">Read, but not weighed against a hypothesis.</p>}
                {src.class === 'company_claim' ? <p className="rp-caveat">The company's own words: not independent evidence.</p> : null}
                <p className="muted small">The quote was checked word for word against the source. Whether it supports the hypothesis is the agent's reading, and is not checked.</p>
              </>
            ) : <p className="muted">This source is not in the record.</p>}
          </div>
        ) : (
          <div className="rp-glance">
            <p className="eyebrow">At a glance</p>
            <dl>
              <div><dt>Status</dt><dd>{final ? (final.draft ? 'Draft answer' : 'Finished') : stopName(record.stop_reason)}{record.stopping_point?.stage_at_stop && !final ? ` · while ${stageName(record.stopping_point.stage_at_stop).toLowerCase()}` : ''}</dd></div>
              <div><dt>Hypotheses</dt><dd>{theories.length}</dd></div>
              <div><dt>Evidence weighed</dt><dd><span className="t-for">{count(null, 'supports')} for</span> · <span className="t-against">{count(null, 'contradicts')} against</span> · {count(null, 'neutral')} no bearing</dd></div>
              <div><dt>Sources</dt><dd>{metrics.sources.map((x) => `${x.count} ${x.label.toLowerCase()}`).join(' · ') || '—'}</dd></div>
              {test && !test.declined ? <div><dt>Test</dt><dd>Proposed, not run</dd></div> : null}
              <div><dt>Warnings</dt><dd>{flags.length ? `${flags.length}, shown where they apply` : 'None from the automated checks'}</dd></div>
            </dl>
            <p className="muted small">Aemon, a 3B research model. Quotes are verified against their sources; the agent's readings and conclusions are not. Click any numbered source to inspect it here.</p>
          </div>
        )}
      </aside>
    </div>
  );
}
