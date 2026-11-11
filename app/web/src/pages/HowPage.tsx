import { STEPS } from '../labels.ts';

// How it works, for managers: the seven steps, where the sources come from, the safeguards and the limits.

const WHAT: string[] = [
  'It restates the decision and the real alternatives, including doing nothing.',
  'It searches the company’s source library: public reports, articles and the company’s own pages.',
  'It writes down two or more possible reasons customers would buy, each saying who would change their behaviour and why.',
  'It weighs each source for or against each explanation, quoting it exactly.',
  'It looks hardest for evidence against its favourite explanation.',
  'If more information is worth its cost, it designs a small market test with a clear rule for what each result means. If not, it says why.',
  'It recommends what to do, how sure it is, and what would change its mind.',
];

export function HowPage(_props: { onError?: (error: unknown) => void }) {
  return (
    <div className="page">
      <p className="eyebrow">How it works</p>
      <h1>Seven steps from question to recommendation</h1>
      <p className="lead">Aemon follows the habits of good strategy work: compare explanations, test them against evidence, and run a small test before a big commitment.</p>
      <ol className="how-steps">
        {STEPS.map((s, i) => <li key={s.label}><span className="dot">{i + 1}</span><div><h3>{s.label}</h3><p>{WHAT[i]}</p></div></li>)}
      </ol>
      <h2>Safeguards</h2>
      <ul className="plain">
        <li><b>Every quote is checked</b> against its source. A step that breaks a rule is not accepted and changes nothing; the assistant tries again.</li>
        <li><b>Sources are labelled:</b> independent sources, the company’s own claims, and simulated what-ifs, which are never treated as real evidence.</li>
        <li><b>Its confidence is its own judgement</b> on a five-step scale, not a measured probability.</li>
      </ul>
      <h2>Limits</h2>
      <ul className="plain">
        <li>It knows only the sources it read. Check the quotes before acting.</li>
        <li>It can stop before finishing. You can run it again, or read what it found so far.</li>
        <li>Live web search is experimental: those pages are saved but no analyst has checked them.</li>
      </ul>
    </div>
  );
}
