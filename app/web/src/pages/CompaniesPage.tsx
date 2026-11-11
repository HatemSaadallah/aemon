import { useEffect, useMemo, useState } from 'react';
import { api } from '../api.ts';
import { CompanyCard } from '../components/company.tsx';
import { Icon } from '../components/Icon.tsx';
import type { CompanySummary } from '../types.ts';

// The directory: every company this account works on, from /api/companies. Filters use fields that exist in the data.

export function CompaniesPage({ onError }: { onError: (e: unknown) => void }) {
  const [list, setList] = useState<CompanySummary[] | null>(null);
  const [q, setQ] = useState('');
  const [industry, setIndustry] = useState('');
  const [era, setEra] = useState('all');
  const [withRuns, setWithRuns] = useState(false);
  useEffect(() => {
    let alive = true;
    api<{ companies: CompanySummary[] }>('/api/companies').then((d) => { if (alive) setList(d.companies); }).catch((e) => { if (alive) { setList([]); onError(e); } });
    return () => { alive = false; };
  }, [onError]);
  const industries = useMemo(() => [...new Set((list ?? []).map((c) => c.industry).filter((x): x is string => Boolean(x)))].sort(), [list]);
  const rows = (list ?? []).filter((c) => (!industry || c.industry === industry) && (era === 'all' || (era === 'historical' ? c.case_year : !c.case_year)) && (!withRuns || c.investigations > 0)
    && (!q.trim() || `${c.name} ${c.legal_name} ${c.industry ?? ''} ${c.tagline ?? ''} ${c.headquarters ?? ''}`.toLowerCase().includes(q.trim().toLowerCase())));
  return (
    <div className="page-wide">
      <header className="page-head">
        <div><p className="eyebrow">Directory</p><h1>Companies</h1><p className="section-lede">Each company is a research workspace with its own source library, investigations and questions.</p></div>
      </header>
      <div className="toolbar">
        <label className="search-field"><Icon name="search" size={15} /><input type="search" placeholder="Search companies, industries, places" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search companies" /></label>
        {industries.length > 1 ? (
          <select className="select" value={industry} onChange={(e) => setIndustry(e.target.value)} aria-label="Industry"><option value="">All industries</option>{industries.map((i) => <option key={i} value={i}>{i}</option>)}</select>
        ) : null}
        <div className="segmented" role="radiogroup" aria-label="Case period">
          {([['all', 'All'], ['present', 'Present day'], ['historical', 'Historical cases']] as const).map(([id, label]) => <button key={id} type="button" role="radio" aria-checked={era === id} onClick={() => setEra(id)}>{label}</button>)}
        </div>
        <label className="check"><input type="checkbox" checked={withRuns} onChange={(e) => setWithRuns(e.target.checked)} /> With investigations</label>
      </div>
      {list === null ? (
        <div className="company-grid">{[0, 1, 2].map((i) => <div key={i} className="company-card skeleton" aria-hidden="true" />)}</div>
      ) : !rows.length ? (
        <div className="empty-state big"><p>{list.length ? 'No company matches these filters.' : 'This account is not a member of any company yet.'}</p></div>
      ) : (
        <div className="company-grid">{rows.map((c) => <CompanyCard key={c.id} company={c} />)}</div>
      )}
      <p className="muted small">Profiles are written from each company's source library and cite it. Monograms stand in for logos: no logo is shown unless its source and licence are recorded.</p>
    </div>
  );
}
