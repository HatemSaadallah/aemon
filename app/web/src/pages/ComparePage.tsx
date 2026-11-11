import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api.ts';
import { Icon } from '../components/Icon.tsx';
import { cut, day, text } from '../labels.ts';
import type { HistoryEntry, RunDetail, Workspace } from '../types.ts';
import { outcomeOf } from './HomePage.tsx';

// Two investigations side by side, field by field, from their saved records. Nothing is scored or reconciled: where a
// run did not record something, the cell says so.

interface Side { entry: HistoryEntry | null; detail: RunDetail | null }

function rows(d: RunDetail | null): [string, string | null][] {
  const r = d?.record; const f = r?.final ?? null;
  const fav = f?.favoured_theory ?? r?.position?.favoured_theory;
  const test = d?.metrics.test;
  const weighed = r?.assessments ?? [];
  return [
    ['Recommendation', f?.recommendation ? `${f.draft ? 'Draft: ' : ''}${cut(f.recommendation)}` : r?.position?.recommendation ? `Interim view: ${cut(r.position.recommendation)}` : null],
    ['Favoured explanation', fav && r?.theories?.[fav]?.claim ? cut(String(r.theories[fav].claim)) : null],
    ['For whom', f?.target_customer ? cut(f.target_customer) : null],
    ['Main uncertainty', f?.uncertainty ? cut(f.uncertainty) : null],
    ['Proposed test', test ? (test.declined ? `Declined: ${test.reason ?? 'no reason recorded'}` : [test.name, test.method].filter(Boolean).join(': ')) : null],
    ['Evidence weighed', weighed.length ? `${weighed.length} weighings: ${weighed.filter((a) => a.direction === 'supports').length} for, ${weighed.filter((a) => a.direction === 'contradicts').length} against, ${weighed.filter((a) => a.direction === 'neutral').length} no bearing` : null],
    ['Confidence label', d?.metrics.confidence ? `${d.metrics.confidence.level} (${d.metrics.confidence.score} of ${d.metrics.confidence.out_of} checks)` : null],
    ['Reliability flags', r?.answer_flags?.length ? r.answer_flags.map((x) => x.label).join('; ') : r ? 'none raised' : null],
  ];
}

export function ComparePage({ workspace: w, onError }: { workspace: Workspace; onError: (e: unknown) => void }) {
  const { a, b } = useParams();
  const [sides, setSides] = useState<Side[]>([{ entry: null, detail: null }, { entry: null, detail: null }]);
  useEffect(() => {
    let alive = true;
    api<{ entries: HistoryEntry[] }>(`/api/workspaces/${w.id}/history`).then(async ({ entries }) => {
      const got = await Promise.all([a, b].map(async (id) => ({ entry: entries.find((e) => e.id === id) ?? null, detail: id ? await api<RunDetail>(`/api/workspaces/${w.id}/history/${id}`).catch(() => null) : null })));
      if (alive) setSides(got);
    }).catch(onError);
    return () => { alive = false; };
  }, [w.id, a, b, onError]);
  const table = sides.map((s) => rows(s.detail));
  return (
    <div className="pg cmp">
      <header className="pg-head">
        <div>
          <Link to="/history" className="small">← Investigations</Link>
          <h1 className="pg-title">Side by side</h1>
          <p className="pg-sub">Two saved investigations, field by field, as each recorded them. Agreement between runs is not evidence that either is right.</p>
        </div>
      </header>
      <div className="cmp-grid">
        {sides.map((s, i) => { const o = s.entry ? outcomeOf(s.entry) : null; return (
          <section key={i} className="panel pad cmp-col">
            {s.entry ? <>
              <div className="inv-top"><span className={`chip ${o?.kind === 'good' ? 'good' : o?.kind === 'warn' ? 'warn' : 'bad'}`}>{o?.label}</span><span className="muted small">{day(s.entry.started)} · run {s.entry.id.slice(0, 8)}</span></div>
              <h2 className="display cmp-q">{text(s.entry.question)}</h2>
              <div className="row"><Link to={`/investigate/${s.entry.id}`} className="button small">Report</Link><Link to={`/map/${s.entry.id}`} className="button small ghost"><Icon name="map" size={13} /> Map</Link></div>
              <dl className="cmp-dl">{(table[i] ?? []).map(([k, v]) => <div key={k}><dt>{k}</dt><dd className={v ? '' : 'muted'}>{v ?? 'Not recorded'}</dd></div>)}</dl>
            </> : <div className="skel" style={{ height: 320 }} />}
          </section>
        ); })}
      </div>
    </div>
  );
}
