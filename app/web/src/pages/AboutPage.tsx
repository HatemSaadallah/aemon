import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from '../components/Icon.tsx';

// About: four sections in one narrative (mission, how Aemon thinks, what makes it different, a closing statement).
// Every claim here is about the method; measured results and their limits live on the Methodology page, and the
// people behind Aemon on the Who we are page.

// Fades a section in once, the first time it scrolls into view (instantly when motion is reduced)
export function Reveal({ children, className = '', as: Tag = 'section' }: { children: ReactNode; className?: string; as?: 'section' | 'header' }) {
  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setShown(true); return undefined; }
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { setShown(true); io.disconnect(); } }, { threshold: 0.12 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return <Tag ref={ref as never} className={`rv${shown ? ' in' : ''} ${className}`}>{children}</Tag>;
}

// The investigation logic, drawn: one question, three rival hypotheses, evidence for and against, one recommended test.
// Illustrative only: no labels refer to a real investigation.
function InvestigationDiagram() {
  const H = [{ x: 96, label: 'Hypothesis A' }, { x: 260, label: 'Hypothesis B' }, { x: 424, label: 'Hypothesis C' }];
  const E: { x: number; h: number; sign: '+' | '−' | '·' }[] = [{ x: 60, h: 0, sign: '+' }, { x: 132, h: 0, sign: '−' }, { x: 224, h: 1, sign: '+' }, { x: 296, h: 1, sign: '+' }, { x: 388, h: 2, sign: '−' }, { x: 460, h: 2, sign: '·' }];
  return (
    <figure className="dia" aria-label="Illustration: a question branches into three competing hypotheses, each weighed against evidence for and against, leading to one recommended test.">
      <svg viewBox="0 0 520 452" role="img" aria-hidden="true">
        <defs>
          <pattern id="dia-grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" className="dia-dotgrid" /></pattern>
        </defs>
        <rect x="0" y="0" width="520" height="452" rx="18" fill="url(#dia-grid)" className="dia-bg" />
        {H.map((h, i) => <path key={h.label} className={`dia-line${i === 1 ? ' hot' : ''}`} style={{ animationDelay: `${0.1 + i * 0.08}s` }} d={`M260 78 C260 110, ${h.x} 112, ${h.x} 146`} />)}
        {E.map((e, i) => { const h = H[e.h]!; return <path key={i} className={`dia-line thin${e.h === 1 ? ' hot' : ''}`} style={{ animationDelay: `${0.4 + i * 0.05}s` }} d={`M${h.x} 182 C${h.x} 212, ${e.x} 214, ${e.x} 244`} />; })}
        {E.map((e, i) => (e.sign === '+' ? <path key={`t${i}`} className={`dia-line thin${e.h === 1 ? ' hot' : ' faint'}`} style={{ animationDelay: `${0.75 + i * 0.05}s` }} d={`M${e.x} 272 C${e.x} 320, 260 326, 260 366`} /> : null))}
        <g className="dia-node q"><rect x="170" y="40" width="180" height="38" rx="10" /><text x="260" y="64">Strategic question</text></g>
        {H.map((h, i) => <g key={h.label} className={`dia-node h${i === 1 ? ' fav' : ''}${i === 2 ? ' weak' : ''}`}><rect x={h.x - 66} y="146" width="132" height="36" rx="9" /><text x={h.x} y="169">{h.label}</text></g>)}
        {E.map((e, i) => <g key={`e${i}`} className={`dia-ev s${e.sign === '+' ? 'p' : e.sign === '−' ? 'n' : 'z'}`}><circle cx={e.x} cy="258" r="14" /><text x={e.x} y="263">{e.sign}</text></g>)}
        <g className="dia-node t"><rect x="172" y="366" width="176" height="40" rx="10" /><text x="260" y="391">Recommended test</text></g>
        <text className="dia-cap" x="20" y="226">weigh</text><text className="dia-cap" x="20" y="340">decide what to test</text><text className="dia-cap" x="20" y="124">compare</text>
      </svg>
      <figcaption><span className="lg p">+</span> supports <span className="lg n">−</span> contradicts <span className="lg z">·</span> no bearing</figcaption>
    </figure>
  );
}

function Hero() {
  return (
    <Reveal as="header" className="ab-hero">
      <div className="ab-hero-text">
        <span className="ab-eyebrow">About Aemon <i>/</i> Our mission</span>
        <h1 className="display ab-h1">Better decisions begin with better questions.</h1>
        <p className="ab-lede">Aemon turns uncertain business questions into structured investigations — weighing competing explanations, tracing claims to evidence, and identifying what to test before making a big commitment.</p>
        <p className="ab-sub">Built at the intersection of artificial intelligence, research methodology, and strategic decision-making.</p>
        <div className="ab-actions">
          <Link to="/investigate" className="button primary big">Start an investigation</Link>
          <Link to="/how" className="ab-link">How it works <Icon name="arrow" size={14} /></Link>
        </div>
      </div>
      <InvestigationDiagram />
    </Reveal>
  );
}

function StepGlyph({ n }: { n: number }) {
  return (
    <svg viewBox="0 0 64 40" className="ab-glyph" aria-hidden="true">
      {n === 0 ? <><circle cx="32" cy="8" r="4" /><path d="M32 12 C32 22, 12 18, 12 30 M32 12 V30 M32 12 C32 22, 52 18, 52 30" /><circle cx="12" cy="33" r="3" /><circle cx="32" cy="33" r="3" /><circle cx="52" cy="33" r="3" /></>
        : n === 1 ? <><path d="M8 20 H56" className="faint" /><rect x="12" y="12" width="8" height="8" rx="2" className="p" /><rect x="28" y="20" width="8" height="8" rx="2" className="n" /><rect x="44" y="12" width="8" height="8" rx="2" className="p" /></>
          : <><rect x="14" y="6" width="36" height="28" rx="6" /><path d="M22 20 l6 6 l12 -12" className="p" /></>}
    </svg>
  );
}

function HowItThinks() {
  const steps: [string, string][] = [
    ['Explore explanations', 'Start with competing hypotheses instead of jumping to a single conclusion.'],
    ['Evaluate the evidence', 'Examine what supports each explanation, what challenges it, and where uncertainty remains.'],
    ['Recommend a test', 'Translate the findings into a practical experiment before committing significant resources.'],
  ];
  return (
    <Reveal className="ab-sec">
      <div className="ab-head">
        <h2 className="display ab-h2">From uncertainty to evidence.</h2>
        <p className="ab-subhead">A structured approach to decisions that deserve more than a quick answer.</p>
      </div>
      <ol className="ab-steps">
        {steps.map(([t, d], i) => (
          <li key={t}>
            <StepGlyph n={i} />
            <span className="ab-num">0{i + 1}</span>
            <h3>{t}</h3>
            <p>{d}</p>
          </li>
        ))}
      </ol>
    </Reveal>
  );
}

function Different() {
  const principles: [string, string, 'scale' | 'compass' | 'flask'][] = [
    ['Evidence over confidence', 'Conclusions should distinguish supporting evidence from uncertainty.', 'scale'],
    ['Alternative explanations', 'A strong investigation considers what else could explain an observation.', 'compass'],
    ['Experiments over assumptions', 'When evidence is incomplete, the next step should be a test, not an unsupported assertion.', 'flask'],
  ];
  return (
    <Reveal className="ab-sec">
      <div className="ab-head"><h2 className="display ab-h2">Built to question its own conclusions.</h2></div>
      <div className="ab-diff">
        <article className="ab-feature">
          <span className="ab-eyebrow">Research approach</span>
          <h3 className="display">A smaller model. A more rigorous process.</h3>
          <p>Aemon explores whether a small open model can learn careful investigation. Tiny Aya Global, with 3 billion parameters, was fine-tuned on investigations carried out by a more capable teacher model, Command A+, under strict research rules.</p>
          <p>The aim is not plausible-sounding answers. It is investigations whose claims can be checked: every quote must match its source, every hypothesis must say who would change their behaviour and why, and a simulated result never counts as evidence.</p>
          <div className="ab-rules" aria-label="Rules every investigation follows">
            <span><Icon name="check" size={13} /> Quotes checked against sources</span>
            <span><Icon name="check" size={13} /> Rival hypotheses required</span>
            <span><Icon name="check" size={13} /> Simulations labelled, never evidence</span>
          </div>
          <p className="ab-note">A citation can be exact while the reading of it is wrong. The measured limits are published on the <Link to="/how">Methodology</Link> page.</p>
        </article>
        <ul className="ab-principles">
          {principles.map(([t, d, icon]) => <li key={t}><span className="ab-pi"><Icon name={icon} size={17} /></span><div><h3>{t}</h3><p>{d}</p></div></li>)}
        </ul>
      </div>
    </Reveal>
  );
}

function Closing() {
  return (
    <Reveal className="ab-close">
      <h2 className="display">The goal isn't to sound certain. It's to know what the evidence supports.</h2>
      <p>We're building Aemon around a simple idea: a trustworthy assistant should help people understand not just an answer, but why that answer deserves confidence — and what remains to be tested.</p>
      <Link to="/how" className="button primary big">Explore our methodology <Icon name="arrow" size={15} /></Link>
    </Reveal>
  );
}

export function AboutPage() {
  return (
    <div className="ab">
      <Hero />
      <HowItThinks />
      <Different />
      <Closing />
    </div>
  );
}
