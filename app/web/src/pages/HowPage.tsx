import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api.ts';
import { Icon, type IconName } from '../components/Icon.tsx';
import { cut, text } from '../labels.ts';
import type { HistoryEntry, RunDetail, RunRecord, Workspace } from '../types.ts';

// Methodology: the seven stages as one interactive process. Each stage opens to what the agent does, why it matters,
// the tools it calls, and an example taken from a recorded investigation of the current company (never written for
// the page). Then the technology in plain words, the measured results with their limits, and the published resources.

interface Stage { title: string; icon: IconName; short: string; does: string; why: string; tools: string[]; example: (r: RunRecord) => string | null }

const STAGES: Stage[] = [
  { title: 'Understand the question', icon: 'target', short: 'Restate the decision and its real alternatives.',
    does: 'Restates the decision, the objective and the real alternatives, including doing nothing, and the constraints that matter.',
    why: 'A vague question produces a vague answer. Naming the alternatives keeps the investigation honest about what is being compared.',
    tools: ['frame_problem'], example: (r) => (r.frame?.objective ? `Objective: ${cut(r.frame.objective)}` : null) },
  { title: 'Gather evidence', icon: 'search', short: "Search the company's source library and read what is relevant.",
    does: "Searches the company's curated library of public reports, articles and the company's own pages, and reads the passages that look relevant.",
    why: 'Every later claim must trace back to something that was actually read. Sources are labelled: independent, the company\'s own claim, or simulated.',
    tools: ['search_evidence', 'read_source'], example: (r) => { const s = Object.values(r.sources ?? {}); return s.length ? `${s.length} sources read, for example “${cut(s[0]?.title)}”.` : null; } },
  { title: 'Form competing hypotheses', icon: 'bulb', short: 'Write down two or more rival explanations.',
    does: 'Writes down at least two rival explanations of why customers would change what they do, each naming who changes and why.',
    why: 'With one explanation, every source looks like support. Rivals force the evidence to discriminate.',
    tools: ['add_theory'], example: (r) => { const t = Object.values(r.theories ?? {})[0]; return t?.claim ? `“${cut(String(t.claim))}”` : null; } },
  { title: 'Weigh the evidence', icon: 'scale', short: 'Mark each source for, against or of no bearing, quoting it.',
    does: 'Weighs each source against each hypothesis as supporting, contradicting or of no bearing, quoting the passage word for word.',
    why: 'Quotes are checked mechanically against the source. The reading of the quote is the agent\'s, and is shown as such.',
    tools: ['assess_evidence'], example: (r) => { const a = (r.assessments ?? []).find((x) => x.quote); return a ? `Weighed as ${a.direction === 'neutral' ? 'no bearing' : a.direction}: “${cut(a.quote)}”` : null; } },
  { title: 'Challenge assumptions', icon: 'zap', short: 'Look hardest for evidence against the favourite.',
    does: 'Searches specifically for evidence against the explanation it currently favours, and revises or drops hypotheses when the evidence demands it.',
    why: 'The cheapest way to be wrong is to stop looking once a story fits.',
    tools: ['challenge_theory', 'revise_theory'], example: (r) => (r.challenge_searches?.[0]?.query ? `Searched for: “${cut(r.challenge_searches[0].query)}”` : null) },
  { title: 'Propose or decline a test', icon: 'flask', short: 'Design a small market test, or say why none is worth it.',
    does: 'If more information is worth its cost, designs a small test with competing predictions and a decision rule. If not, declines and says why.',
    why: 'A cheap test before a big commitment is often the best recommendation. A proposed test is a plan, never a result.',
    tools: ['propose_test', 'decline_test'], example: (r) => { const t = Object.values(r.tests ?? {})[0] as { name?: string } | undefined; return t?.name ? `Proposed: ${cut(t.name)}` : r.test_declined?.reason ? `Declined: ${cut(r.test_declined.reason)}` : null; } },
  { title: 'Recommend', icon: 'flag', short: 'State what to do, how sure, and what would change it.',
    does: 'States a position and a recommendation, the main uncertainty and what would change its mind. Runs that stop early are shown as stopped.',
    why: 'A recommendation is only useful with its uncertainty attached, and with the trail that produced it.',
    tools: ['state_position', 'conclude'], example: (r) => (r.final?.recommendation ? `“${cut(r.final.recommendation)}”` : null) },
];

const LINKS: [string, string, string][] = [
  ['Public code', 'github.com/HatemSaadallah/aemon', 'https://github.com/HatemSaadallah/aemon'],
  ['Model card', 'Strategy Agent V1 on Hugging Face', 'https://huggingface.co/HatemSaadallah/tiny-aya-global-strategy-agent'],
  ['Dataset card', 'Teacher investigations on Hugging Face', 'https://huggingface.co/datasets/HatemSaadallah/strategy-agent-investigations'],
  ['Collection', 'Model, data and results together', 'https://huggingface.co/collections/HatemSaadallah/strategy-investigation-agent-6af0d2ab19339ae58d020326'],
];

export function HowPage({ workspace: w }: { workspace?: Workspace | null }) {
  const [open, setOpen] = useState(0);
  const [sample, setSample] = useState<{ entry: HistoryEntry; record: RunRecord } | null>(null);
  useEffect(() => {  // a recorded investigation of this company, to show each stage on real data
    if (!w) return undefined;
    let alive = true;
    api<{ entries: HistoryEntry[] }>(`/api/workspaces/${w.id}/history`).then(async ({ entries }) => {
      const e = [...entries].sort((a, b) => (b.started ?? 0) - (a.started ?? 0)).find((x) => x.summary?.finished);
      if (!e) return;
      const d = await api<RunDetail>(`/api/workspaces/${w.id}/history/${e.id}`);
      if (alive) setSample({ entry: e, record: d.record });
    }).catch(() => {});
    return () => { alive = false; };
  }, [w]);
  const s = STAGES[open] ?? STAGES[0]!;
  const ex = sample ? s.example(sample.record) : null;
  return (
    <div className="pg method">
      <header className="pg-head">
        <div>
          <span className="kicker accent">Methodology</span>
          <h1 className="pg-title">How Aemon investigates</h1>
          <p className="pg-sub">Seven stages, the habits of careful strategy work: frame the decision, compare explanations, weigh evidence for and against, challenge the favourite, and test before a big commitment.</p>
        </div>
      </header>

      <section className="proc" aria-label="The seven stages">
        <ol className="proc-steps" role="tablist" aria-label="Stages">
          {STAGES.map((st, i) => (
            <li key={st.title}>
              <button type="button" role="tab" aria-selected={open === i} onClick={() => setOpen(i)}>
                <span className="proc-n"><Icon name={st.icon} size={16} /></span>
                <span className="proc-t"><span className="muted small">Stage {i + 1}</span><b>{st.title}</b></span>
              </button>
            </li>
          ))}
        </ol>
        <div className="proc-panel panel pad" role="tabpanel" key={open}>
          <div className="proc-main">
            <span className="kicker accent">Stage {open + 1} of 7</span>
            <h2 className="display">{s.title}</h2>
            <p className="proc-lede">{s.does}</p>
            <div className="proc-cols">
              <div><h3>Why it matters</h3><p>{s.why}</p></div>
              <div><h3>Tools the agent calls</h3><p className="proc-tools">{s.tools.map((t) => <code key={t}>{t}</code>)}</p></div>
            </div>
          </div>
          <aside className="proc-ex">
            <h3>From a recorded investigation</h3>
            {sample ? (ex ? <>
              <p className="proc-ex-text">{ex}</p>
              <Link to={`/investigate/${sample.entry.id}`} className="small">{text(sample.entry.question)} →</Link>
            </> : <p className="muted small">The latest finished investigation recorded nothing for this stage.</p>)
              : <p className="muted small">{w ? 'A finished investigation of this company will appear here.' : 'Choose a company to see an example.'}</p>}
          </aside>
        </div>
        <div className="proc-nav">
          <button type="button" className="button small ghost" disabled={open === 0} onClick={() => setOpen(open - 1)}>← Previous</button>
          <button type="button" className="button small" disabled={open === STAGES.length - 1} onClick={() => setOpen(open + 1)}>Next stage →</button>
        </div>
      </section>

      <section className="sec">
        <div className="sec-head"><h2 className="display">The technology, simply</h2></div>
        <div className="tech-grid">
          <article className="panel pad"><Icon name="compass" size={18} /><h3>An AI agent</h3><p>A language model that works in steps: it decides what to do next, calls a tool, reads the result, and continues, instead of answering in one go.</p></article>
          <article className="panel pad"><Icon name="search" size={18} /><h3>Why tools</h3><p>Searching, reading and recording are tools with strict rules. A step that breaks a rule (a quote not in the source, a missing rival) is refused and changes nothing.</p></article>
          <article className="panel pad"><Icon name="book" size={18} /><h3>Fine-tuning</h3><p>A small open model (Tiny Aya Global, 3B) learned the workflow from 158 investigations by a much larger teacher model, Command A+, on 57 training companies.</p></article>
          <article className="panel pad"><Icon name="check" size={18} /><h3>What V1 showed</h3><p>On a frozen test of 4 new companies, blind judges scored the fine-tuned agent higher than the base model, and it finished far more investigations.</p></article>
          <article className="panel pad"><Icon name="alert" size={18} /><h3>Where it falls short</h3><p>Exact quotes do not guarantee sound readings. Numbers can be invented, evidence types misjudged, and test designs weak. Every report flags its own.</p></article>
        </div>
      </section>

      <section className="sec">
        <div className="sec-head"><h2 className="display">Measured results</h2><span className="muted small">Strategy Agent V1, frozen; scores 0 to 3 from blind judges</span></div>
        <div className="res-grid">
          <div className="panel pad res">
            <span className="kicker">Final test · 4 companies, 48 runs per arm</span>
            <p className="res-big">0.65 → 1.48</p>
            <p className="muted small">Base model against V1, mean of two blind judges. Difference +0.83, 95% interval 0.69 to 0.97.</p>
            <p className="small">Finished investigations: <b>4 of 48</b> base, <b>28 of 48</b> V1.</p>
          </div>
          <div className="panel pad res">
            <span className="kicker">Second frozen test · 12 companies, 72 runs per arm</span>
            <p className="res-big">0.57 → 1.09</p>
            <p className="muted small">Base model against V1, mean of two blind judges, 144 runs. Difference +0.52, 95% interval 0.33 to 0.70 (Claude +0.41 [0.24, 0.57]; Codex +0.63 [0.43, 0.84]).</p>
            <p className="small">Finished investigations: <b>2 of 72</b> base, <b>32 of 72</b> V1.</p>
          </div>
          <div className="panel pad res warnish">
            <span className="kicker">Reliability audit</span>
            <ul className="res-list">
              <li><b>21–46%</b> of V1's finished recommendations use a number found in no source it read, depending on the test set.</li>
              <li>Evidence types are often wrong: “independent study” is applied to news and company text.</li>
              <li>Only 1 of 27 proposed development tests passed the stricter design checks.</li>
              <li>Finishing is not the same as being right: only 1 of 48 final-test runs passed every mechanical check.</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="sec">
        <div className="sec-head"><h2 className="display">Research transparency</h2></div>
        <ul className="links-grid">
          {LINKS.map(([k, label, href]) => (
            <li key={k}><a className="panel pad hover link-card" href={href} target="_blank" rel="noreferrer noopener"><span className="kicker">{k}</span><b>{label}</b><Icon name="arrow" size={15} /></a></li>
          ))}
        </ul>
        <p className="muted small">The research paper is published with the code: <a href="https://github.com/HatemSaadallah/aemon/blob/main/docs/PAPER.pdf" target="_blank" rel="noreferrer noopener">docs/PAPER.pdf</a>.</p>
      </section>
    </div>
  );
}
