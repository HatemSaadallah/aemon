import { useState } from 'react';
import { Icon } from '../components/Icon.tsx';
import { Reveal } from './AboutPage.tsx';

// Who we are: the two people behind aemon, and nothing else. Photos live in app/web/public/assets/team/: their own
// photos, cut out and set on one shared backdrop. A missing photo falls back to a branded initials portrait. Only
// verified profile links are shown.

const PEOPLE: { name: string; initials: string; photo: string | null; role: string; note: string; links: [string, string][] }[] = [
  { name: 'Hatem Saadallah', initials: 'HS', photo: '/assets/team/hatem.jpg', role: 'AI Researcher & Co-creator', note: "Master's student in Artificial Intelligence.", links: [['GitHub', 'https://github.com/HatemSaadallah']] },
  { name: 'Nour Jennane', initials: 'NJ', photo: '/assets/team/nour.jpg', role: 'AI Researcher & Co-creator', note: "Master's student in Artificial Intelligence.", links: [] },
];

function Portrait({ photo, initials, name }: { photo: string | null; initials: string; name: string }) {
  const [failed, setFailed] = useState(false);
  if (photo && !failed) return <img className="tm-portrait" src={photo} alt={name} onError={() => setFailed(true)} />;
  return (
    <span className="tm-portrait mono" role="img" aria-label={`${name} (no photograph)`}>
      <svg viewBox="0 0 120 150" aria-hidden="true" preserveAspectRatio="xMidYMid slice"><circle cx="60" cy="75" r="52" /><circle cx="60" cy="75" r="34" /><circle cx="60" cy="75" r="16" /><path d="M0 75 H120 M60 0 V150" /></svg>
      <b>{initials}</b>
    </span>
  );
}

export function TeamPage() {
  return (
    <div className="tm">
      <Reveal as="header" className="tm-head">
        <span className="ab-eyebrow">Who we are</span>
        <h1 className="display tm-h1">Curious minds. Careful methods.</h1>
        <p className="ab-lede">aemon is built by two Master's students in Artificial Intelligence, interested in making sophisticated research methods more accessible to real business decisions.</p>
      </Reveal>
      <Reveal className="tm-people">
        {PEOPLE.map((p, i) => (
          <article key={p.name} className="tm-person">
            <Portrait photo={p.photo} initials={p.initials} name={p.name} />
            <div className="tm-text">
              <span className="tm-n">0{i + 1}</span>
              <h2 className="display">{p.name}</h2>
              <span className="ab-role">{p.role}</span>
              <p>{p.note}</p>
              {p.links.length ? <div className="ab-plinks">{p.links.map(([k, href]) => <a key={k} href={href} target="_blank" rel="noreferrer noopener">{k} <Icon name="arrow" size={12} /></a>)}</div> : null}
            </div>
          </article>
        ))}
      </Reveal>
    </div>
  );
}
