import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.ts';
import { accentStyle, CompanyCard, CompanyHero, Empty, EvidenceLibrary, FactLine, InvestigationList, Sources } from '../components/company.tsx';
import { Icon } from '../components/Icon.tsx';
import { text } from '../labels.ts';
import type { CompanyProfile } from '../types.ts';

// One company's research workspace: who they are (cited facts only), what they sell, their background and market,
// the evidence library, and the investigations, ending in "Investigate this company". One template for every company.

const TABS: [string, string][] = [['overview', 'Overview'], ['products', 'Products'], ['background', 'Background'], ['market', 'Market'], ['evidence', 'Evidence'], ['investigations', 'Investigations']];

export function CompanyPage({ onWorkspace, onError }: { onWorkspace: (id: string) => void; onError: (e: unknown) => void }) {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [p, setP] = useState<CompanyProfile | null>(null);
  const [missing, setMissing] = useState(false);
  const [tab, setTab] = useState('overview');
  useEffect(() => {
    let alive = true;
    setP(null); setMissing(false); setTab('overview');
    api<CompanyProfile>(`/api/companies/${id}`).then((d) => { if (alive) { setP(d); onWorkspace(d.id); } }).catch((e) => { if (alive) { setMissing(true); onError(e); } });
    return () => { alive = false; };
  }, [id, onError, onWorkspace]);

  useEffect(() => {
    const open = (e: Event): void => { setTab('evidence'); setFocus((e as CustomEvent<string>).detail); };
    window.addEventListener('open-source', open);
    return () => window.removeEventListener('open-source', open);
  }, []);
  const [focus, setFocus] = useState<string | null>(null);

  if (missing) return <div className="page-wide"><Empty>This company is not in your directory. <Link to="/companies">Back to companies</Link></Empty></div>;
  if (!p) return <div className="page-wide"><div className="hero-skel skeleton" aria-hidden="true" /><p className="muted">Loading the company…</p></div>;
  const investigate = (question?: string) => navigate('/investigate', question ? { state: { question } } : undefined);
  const f = p.facts;
  return (
    <div className="company-page" style={accentStyle(p)}>
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/companies">Companies</Link><span aria-hidden="true">/</span><span>{text(p.name)}</span></nav>
      <CompanyHero p={p} onInvestigate={() => investigate()}><span className="muted small">{p.investigations.length} investigation{p.investigations.length === 1 ? '' : 's'} so far</span></CompanyHero>

      <div className="company-tabs" role="tablist" aria-label="Company sections">
        {TABS.map(([key, label]) => <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>{label}{key === 'evidence' ? <span className="count">{p.library.length}</span> : key === 'investigations' ? <span className="count">{p.investigations.length}</span> : null}</button>)}
      </div>

      {tab === 'overview' ? (
        <div className="company-grid-2">
          <section className="panel">
            <h2 className="panel-title">About the company</h2>
            {p.case_year ? <p className="notice warn small-notice" role="note"><Icon name="alert" size={14} /> This profile is written from sources published up to today, and some describe events after {p.case_year}. The case is set in {p.case_context?.set_in ?? p.case_year}: an analyst then could not have known them. Each fact shows its source's publication year.</p> : null}
            {p.about.length ? p.about.map((a, i) => <FactLine key={i} fact={a} />) : <p>{text(p.brief_description)} <span className="muted small">(from the case brief)</span></p>}
          </section>
          <aside className="panel">
            <h2 className="panel-title">At a glance</h2>
            <dl className="glance">
              {([['industry', 'Industry'], ['headquarters', 'Headquarters'], ['founded', 'Founded'], ['parent', 'Owner or group'], ['website', 'Website']] as const).map(([k, label]) => (
                <div key={k}><dt>{label}</dt><dd>{f[k] ? <>{text(f[k]?.text)} <Sources sources={f[k]?.sources ?? []} basis={f[k]?.basis} /></> : <span className="muted">Not in the records</span>}</dd></div>
              ))}
              <div><dt>Case period</dt><dd>{p.case_year ? p.case_year : 'Present day'}</dd></div>
            </dl>
          </aside>
          <section className="panel span-2">
            <div className="panel-head"><h2 className="panel-title">Questions you could investigate</h2><span className="muted small">Starting points, not findings</span></div>
            <ul className="question-grid">{p.questions.map((q) => <li key={q}><button type="button" className="question-card" onClick={() => investigate(q)}><span>{text(q)}</span><Icon name="arrow" size={14} /></button></li>)}</ul>
          </section>
        </div>
      ) : null}

      {tab === 'products' ? (
        <section className="tab-body">
          {p.products.length ? <div className="product-grid">{p.products.map((pr) => (
            <article key={pr.name} className="product-card"><span className="product-icon" aria-hidden="true"><Icon name="target" size={18} /></span>
              <h3>{text(pr.name)}</h3><p>{text(pr.description)}</p>{pr.customers ? <p className="muted small">For: {text(pr.customers)}</p> : null}<Sources sources={pr.sources} /></article>
          ))}</div> : <Empty>No product information has been curated from the records yet.</Empty>}
          {p.customers.length ? <section className="panel"><h2 className="panel-title">Customers</h2>{p.customers.map((c, i) => <FactLine key={i} fact={c} />)}</section> : null}
        </section>
      ) : null}

      {tab === 'background' ? (
        <section className="tab-body">
          {p.timeline.length ? <ol className="timeline">{p.timeline.map((t, i) => (
            <li key={i} className={p.case_year && /^\d{4}/.test(t.date) && Number(t.date.slice(0, 4)) > p.case_year ? 'after' : ''}>
              <span className="tl-date">{text(t.date)}</span><div className="tl-body"><p>{text(t.event)}</p><Sources sources={t.sources} />
                {p.case_year && /^\d{4}/.test(t.date) && Number(t.date.slice(0, 4)) > p.case_year ? <span className="late">After the case date ({p.case_year})</span> : null}</div>
            </li>
          ))}</ol> : <Empty>No dated events are recorded for this company.</Empty>}
        </section>
      ) : null}

      {tab === 'market' ? (
        <section className="tab-body company-grid-2">
          <section className="panel"><h2 className="panel-title">Markets and channels</h2>{p.markets.length ? p.markets.map((m, i) => <FactLine key={i} fact={m} />) : <p className="muted">Not in the records.</p>}</section>
          <section className="panel"><h2 className="panel-title">Positioning, challenges and openings <span className="muted small">as stated in the records</span></h2>{p.positioning.length ? p.positioning.map((m, i) => <FactLine key={i} fact={m} />) : <p className="muted">Not in the records.</p>}</section>
          {p.context_companies.length ? (
            <section className="panel span-2"><h2 className="panel-title">Other organisations in this dossier</h2>
              <p className="muted small">Records about other organisations are part of the library. They are listed with what the records say about them, not as competitors or partners.</p>
              <ul className="org-list">{p.context_companies.map((c) => <li key={c.name}><b>{text(c.name)}</b> <span className="muted">{text(c.relation_in_records)}</span> <Sources sources={c.sources} /></li>)}</ul>
            </section>
          ) : null}
        </section>
      ) : null}

      {tab === 'evidence' ? <section className="tab-body"><EvidenceLibrary sources={p.library} year={p.case_year} company={p.name} focus={focus} /></section> : null}

      {tab === 'investigations' ? (
        <section className="tab-body company-grid-2">
          <section className="panel"><div className="panel-head"><h2 className="panel-title">Investigations</h2><button type="button" className="button primary" onClick={() => investigate()}><Icon name="plus" size={14} /> New</button></div><InvestigationList entries={p.investigations} /></section>
          <aside className="panel"><h2 className="panel-title">What-if scenarios</h2>
            <p className="muted small">Each adds a simulated result halfway through, to see how the agent updates its view. Simulated results are never evidence.</p>
            {p.scenarios.length ? <ul className="plain">{p.scenarios.map((s) => <li key={s.case} className="scenario-line">{text(s.label)}</li>)}</ul> : <p className="muted">None for this company.</p>}
            <Link to="/investigate" className="link small">Choose one on the investigation page</Link>
          </aside>
        </section>
      ) : null}

      {p.related.length ? <section className="related"><h2 className="panel-title">Same industry in your directory</h2><div className="company-grid">{p.related.map((c) => <CompanyCard key={c.id} company={c} />)}</div></section> : null}
    </div>
  );
}
