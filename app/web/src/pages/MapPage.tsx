import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.ts';
import { InvTabs } from '../components/InvTabs.tsx';
import { ReasoningMap } from '../components/reasoning/ReasoningMap.tsx';
import { day, text } from '../labels.ts';
import type { HistoryEntry, RunDetail, Workspace } from '../types.ts';
import { outcomeOf } from './HomePage.tsx';

// One investigation's reasoning map, over the whole workspace below its header. The header names the investigation and
// carries the same tabs as its report, so the map is never mistaken for a map of everything. /map alone opens the
// newest finished investigation.

export function MapPage({ workspace: w, onError }: { workspace: Workspace; onError: (e: unknown) => void }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [entry, setEntry] = useState<HistoryEntry | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [none, setNone] = useState(false);
  useEffect(() => {
    let alive = true;
    api<{ entries: HistoryEntry[] }>(`/api/workspaces/${w.id}/history`).then((d) => {
      if (!alive) return;
      const list = [...d.entries].sort((a, b) => (b.started ?? 0) - (a.started ?? 0));
      if (!id) { const first = list.find((e) => e.status !== 'running'); if (first) navigate(`/map/${first.id}`, { replace: true }); else setNone(true); return; }
      setEntry(list.find((e) => e.id === id) ?? null);
    }).catch((e) => { if (alive) onError(e); });
    return () => { alive = false; };
  }, [w.id, id, navigate, onError]);
  useEffect(() => {
    if (!id) return undefined;
    let alive = true;
    setDetail(null);
    api<RunDetail>(`/api/workspaces/${w.id}/history/${id}`).then((d) => { if (alive) setDetail(d); }).catch((e) => { if (alive) onError(e); });
    return () => { alive = false; };
  }, [w.id, id, onError]);

  if (none) return <div className="pg"><div className="empty-box"><b>No reasoning map yet</b><span>Each investigation draws one as it runs.</span><Link to="/investigate" className="button primary">Start an investigation</Link></div></div>;
  const o = entry ? outcomeOf(entry) : null;
  return (
    <div className="mapv">
      <header className="ihead">
        <div className="ihead-top">
          <Link to="/history" className="ihead-back">Investigations</Link><span className="muted">/</span>
          {o ? <span className={`chip ${o.kind === 'good' ? 'good' : o.kind === 'run' ? 'accent' : o.kind === 'warn' ? 'warn' : 'bad'}`}>{o.label}</span> : null}
          <span className="muted small">{text(w.company)}{entry?.started ? ` · ${day(entry.started)}` : ''}</span>
        </div>
        <h1 className="display ihead-q" title={entry ? text(entry.question) : undefined}>{entry ? text(entry.question) : ' '}</h1>
        {id ? <InvTabs id={id} active="map" sources={detail ? Object.keys(detail.record.sources ?? {}).length : undefined} /> : null}
      </header>
      {!id ? null : !detail ? <div className="rcanvas skel" aria-hidden="true" /> : <ReasoningMap key={id} record={detail.record} onOpenReport={(section) => navigate(`/investigate/${id}`, { state: { section } })} />}
    </div>
  );
}
