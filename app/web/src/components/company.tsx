import { type CSSProperties, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { cut, day, kindOf, text } from '../labels.ts';
import type { Cite, CompanyProfile, CompanySummary, Fact, HistoryEntry, LibrarySource } from '../types.ts';
import { outcomeOf } from '../pages/HomePage.tsx';
import { Icon } from './Icon.tsx';

// The reusable pieces of every company page (one template for the whole catalog). Facts always show where they come
// from; a fact resting only on the company's own words says so.

export const accentStyle = (c: { accent: string }): CSSProperties => ({ ['--brand' as string]: c.accent });

export function Monogram({ company, size = 44 }: { company: Pick<CompanySummary, 'name' | 'logo'>; size?: number }) {
  const letters = text(company.name).split(/[\s&]+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
  return company.logo?.file
    ? <img className="company-logo" src={company.logo.file} alt={`${company.name} logo`} width={size} height={size} />
    : <span className="monogram" style={{ width: size, height: size, fontSize: size * 0.38 }} aria-hidden="true">{letters}</span>;
}

export function CompanyCard({ company }: { company: CompanySummary }) {
  return (
    <Link to={`/companies/${company.id}`} className="company-card" style={accentStyle(company)}>
      <div className="cc-top"><Monogram company={company} /><span className="cc-era">{company.case_year ? `Case set in ${company.case_year}` : 'Present day'}</span></div>
      <h3 className="cc-name">{text(company.name)}</h3>
      {company.industry ? <p className="cc-industry">{text(company.industry)}</p> : null}
      <p className="cc-tagline">{company.tagline ? text(company.tagline) : 'No profile summary yet.'}</p>
      <div className="cc-meta">
        {company.headquarters ? <span><Icon name="map" size={13} /> {text(company.headquarters)}</span> : null}
        <span><Icon name="book" size={13} /> {company.sources} sources · {company.independent_sources} independent</span>
        <span><Icon name="list" size={13} /> {company.investigations} investigation{company.investigations === 1 ? '' : 's'}</span>
      </div>
      <span className="cc-open">Open workspace <Icon name="arrow" size={14} /></span>
    </Link>
  );
}

export function Sources({ sources, basis }: { sources: Cite[]; basis?: string }) {
  if (!sources.length) return null;
  return (
    <span className="cites">
      {basis === 'company' ? <span className="basis">Company's own claim</span> : null}
      {sources.map((s) => <a key={s.id} href={`#src-${s.id}`} className="cite-chip" title={`${text(s.title)}${s.date ? ` (${s.date})` : ''}`}>{/^\d{4}/.test(text(s.date)) ? text(s.date).slice(0, 4) : 'src'}</a>)}
    </span>
  );
}

export function FactLine({ fact }: { fact: Fact }) {
  return <p className="fact-line">{text(fact.text)} <Sources sources={fact.sources} basis={fact.basis} /></p>;
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty-state"><Icon name="doc" size={18} /><p>{children}</p></div>;
}

export function EvidenceLibrary({ sources, year, company, focus = null }: { sources: LibrarySource[]; year: number | null; company: string; focus?: string | null }) {
  const [q, setQ] = useState('');
  const [origin, setOrigin] = useState('all');
  const [hideLate, setHideLate] = useState(false);
  const [open, setOpen] = useState<string | null>(focus);
  useEffect(() => { if (focus) { setOpen(focus); setQ(''); setOrigin('all'); setHideLate(false); window.setTimeout(() => document.getElementById(`src-${focus}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 80); } }, [focus]);
  const rows = useMemo(() => sources.filter((s) => (origin === 'all' || s.origin === origin) && (!hideLate || (!s.after_case && /^\d{4}/.test(text(s.date))))
    && (!q.trim() || `${s.title} ${s.excerpt} ${s.publisher ?? ''}`.toLowerCase().includes(q.trim().toLowerCase()))), [sources, q, origin, hideLate]);
  const late = sources.filter((s) => s.after_case).length;
  return (
    <div className="library">
      <div className="toolbar">
        <label className="search-field"><Icon name="search" size={15} /><input type="search" placeholder="Search sources" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search sources" /></label>
        <div className="segmented" role="radiogroup" aria-label="Origin">
          {([['all', 'All'], ['verified_observation', 'Independent'], ['company_claim', "Company's own"]] as const).map(([id, label]) => <button key={id} type="button" role="radio" aria-checked={origin === id} onClick={() => setOrigin(id)}>{label}</button>)}
        </div>
        {year && late ? <label className="check"><input type="checkbox" checked={hideLate} onChange={(e) => setHideLate(e.target.checked)} /> Only sources dated by {year}</label> : null}
      </div>
      {year && late ? <p className="notice quiet small-notice"><Icon name="alert" size={14} /> {late} of {sources.length} sources were published after {year}, the year this case is set in. They are marked, and the agent does not see dates by default. {sources.filter((x) => !/^\d{4}/.test(text(x.date))).length} more have no known date; whether they were available in {year} cannot be checked.</p> : null}
      {!rows.length ? <Empty>No source matches.</Empty> : (
        <ul className="lib-list">{rows.map((s) => (
          <li key={s.id} id={`src-${s.id}`} className={`lib-item${open === s.id ? ' open' : ''}`}>
            <button type="button" className="lib-head" aria-expanded={open === s.id} onClick={() => setOpen(open === s.id ? null : s.id)}>
              <span className="lib-title">{text(s.title)}</span>
              <span className="lib-meta">
                <span className={`kind k-${s.origin}`}>{kindOf(s.origin)}</span>
                {/^\d{4}/.test(text(s.date)) ? <span>{text(s.date).slice(0, 10)}</span> : <span className="undated">Date unknown</span>}
                {s.after_case ? <span className="late">after {year}</span> : null}
                {s.existing_offering ? <span className="tag">What {company} already sells</span> : null}
                {s.about && !s.about.toLowerCase().includes((company.toLowerCase().split(' ')[0] ?? '')) ? <span className="muted">About: {text(s.about).slice(0, 50)}</span> : null}
              </span>
            </button>
            {open === s.id ? (
              <div className="lib-body">
                <blockquote>“{text(s.excerpt)}”</blockquote>
                <dl>
                  {s.publisher ? <><dt>Publisher</dt><dd>{text(s.publisher)}</dd></> : null}
                  {s.kind ? <><dt>Evidence kind</dt><dd>{text(s.kind).replaceAll('_', ' ')} <span className="muted small">(dossier label; about 80% reliable on our audit)</span></dd></> : null}
                  {s.does_not_establish ? <><dt>Does not establish</dt><dd>{cut(s.does_not_establish)} <span className="muted small">(case author's note)</span></dd></> : null}
                  {s.limitation ? <><dt>Limitation</dt><dd>{cut(s.limitation)}</dd></> : null}
                </dl>
                {s.url ? <a className="link small" href={s.url} target="_blank" rel="noreferrer noopener"><Icon name="link" size={13} /> Open the original</a> : null}
              </div>
            ) : null}
          </li>
        ))}</ul>
      )}
    </div>
  );
}

export function InvestigationList({ entries }: { entries: HistoryEntry[] }) {
  if (!entries.length) return <Empty>No investigation of this company yet.</Empty>;
  return (
    <ul className="inv-list">{entries.slice(0, 8).map((e) => { const o = outcomeOf(e); return (
      <li key={e.id}><Link to={`/investigate/${e.id}`} className="inv-row" data-ws="">
        <span className={`status-dot s-${o.kind}`} aria-hidden="true" />
        <span className="inv-main"><span className="inv-q">{text(e.question)}</span>
          <span className="inv-rec">{e.summary?.recommendation ? cut(e.summary.recommendation).slice(0, 160) + (e.summary.recommendation.length > 160 ? '…' : '') : '—'}</span></span>
        <span className="inv-meta"><span className={`status-chip ${o.kind === 'good' ? 'good' : o.kind === 'run' ? 'quiet' : o.kind === 'warn' ? 'warn' : 'bad'}`}>{o.label}</span><span className="muted small">{day(e.started)}</span></span>
      </Link></li>
    ); })}</ul>
  );
}

export function Credits({ company }: { company: Pick<CompanySummary, 'logo' | 'banner'> }) {
  const items = [company.banner && ['Banner', company.banner], company.logo && ['Logo', company.logo]].filter(Boolean) as [string, NonNullable<CompanySummary['banner']>][];
  if (!items.length) return null;
  return (
    <p className="credits">{items.map(([label, a]) => (
      <span key={label}>{label}: {a.source_url ? <>{a.author ? `${text(a.author)}, ` : ''}<a href={a.source_url} target="_blank" rel="noreferrer noopener">{text(a.licence)} via Wikimedia Commons</a>{a.trademark ? ' (trademark, shown to identify the company)' : ''}</> : <>{text(a.licence)}{a.illustrative ? `: ${text(a.illustrative)}` : ''}</>}</span>
    ))}</p>
  );
}

// The company's hero, on its profile and on Home: identity and the main action on the left, the company's image on the
// right (a licensed photo, or an illustration labelled as one), with its credit underneath.
export function CompanyHero({ p, onInvestigate, actions, children }: { p: CompanyProfile; onInvestigate: () => void; actions?: React.ReactNode; children?: React.ReactNode }) {
  const f = p.facts;
  const illustrative = Boolean(p.banner?.illustrative);
  return (
    <header className="chero" style={accentStyle(p)}>
      <div className="chero-text">
        <div className="chero-id">
          <Monogram company={p} size={52} />
          <span className="kicker">{[p.industry, p.headquarters].filter(Boolean).map(text).join(' · ') || 'Company'}</span>
        </div>
        <h1 className="display chero-name">{text(p.name)}</h1>
        {p.legal_name && p.legal_name !== p.name ? <p className="muted small chero-legal">{text(p.legal_name)}</p> : null}
        <p className="chero-lede">{text(p.tagline || p.brief_description)}</p>
        <div className="chero-chips">
          {f.website ? <a className="chip" href={`https://${text(f.website.text).replace(/^https?:\/\//, '')}`} target="_blank" rel="noreferrer noopener"><Icon name="link" size={12} /> {text(f.website.text)}</a> : null}
          <span className="chip">{p.case_year ? `Historical case · set in ${p.case_context?.set_in ?? p.case_year}` : 'Present-day case'}</span>
          <span className="chip">{p.sources} source records · {p.independent_sources} independent</span>
        </div>
        <div className="chero-actions">
          <button type="button" className="button primary big" onClick={onInvestigate}><Icon name="search" size={16} /> Start a strategic investigation</button>
          {actions}
        </div>
        {children}
      </div>
      <figure className={`chero-media${p.banner ? '' : ' plain'}`}>
        {p.banner ? <img src={p.banner.file} alt="" loading="eager" /> : <span className="chero-pattern" aria-hidden="true" />}
        {illustrative ? <span className="chip chero-tag">Illustration · not a company image</span> : null}
        <figcaption><Credits company={p} /></figcaption>
      </figure>
    </header>
  );
}
