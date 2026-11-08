import { useState } from 'react';

// Who we are: the two people behind Strategy Lab. Photos live in app/web/public/assets/team/ (served from /assets/team/);
// until a photo is there, the initials are shown.

const PEOPLE = [
  { name: 'Hatem Saadallah', initials: 'HS', photo: '/assets/team/hatem.jpg', role: "Master's student in Artificial Intelligence · AI researcher" },
  { name: 'Nour Jennane', initials: 'NJ', photo: '/assets/team/nour.jpg', role: "Master's student in Artificial Intelligence · AI researcher" },
];

function Avatar({ photo, initials, name }: { photo: string; initials: string; name: string }) {
  const [failed, setFailed] = useState(false);
  return failed ? <span className="avatar" aria-hidden="true">{initials}</span> : <img className="avatar photo" src={photo} alt={name} onError={() => setFailed(true)} />;
}

export function AboutPage() {
  return (
    <div className="page">
      <p className="eyebrow">Who we are</p>
      <h1>The team behind Strategy Lab</h1>
      <p className="lead">We are two AI researchers studying for a Master's in Artificial Intelligence. We build AI assistants that approach a business decision the way a careful strategist does: by comparing possible explanations, weighing evidence for and against each, and proposing a small test before a big commitment.</p>
      <div className="people">
        {PEOPLE.map((p) => (
          <div key={p.name} className="person">
            <Avatar photo={p.photo} initials={p.initials} name={p.name} />
            <div><h2>{p.name}</h2><p className="muted">{p.role}</p></div>
          </div>
        ))}
      </div>
      <h2>What we are building</h2>
      <p>Strategy Lab runs a small open model on your own computer. It learned from more than 150 investigations by a much larger model, carried out under strict rules: every quote must match a real source, each explanation must say why customers would change what they do, and simulated what-if results can never count as evidence of real demand.</p>
      <p>Our aim is an assistant that a manager can trust because they can check it: every claim points to the source it came from.</p>
    </div>
  );
}
