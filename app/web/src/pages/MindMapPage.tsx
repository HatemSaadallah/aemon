import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.ts';
import { Icon } from '../components/Icon.tsx';
import { cut, day, text } from '../labels.ts';
import type { MindNode, Workspace } from '../types.ts';

// Every investigation in this company as a left-to-right tree: company, projects, investigations, the explanations
// each compared, and the strongest quotes for and against. A horizontal tree reads better than radial or force layouts
// for a few dozen nodes (docs/DESIGN_RESEARCH.md, section 7). Folding, search, zoom, drag to pan; click to see more.

const W = 236, H = 78, GAP_X = 64, GAP_Y = 14;
interface Placed { node: MindNode; x: number; y: number; depth: number; parent: Placed | null; hidden: number }

function layout(root: MindNode, closed: Set<string>): Placed[] {
  const out: Placed[] = [];
  let row = 0;
  const walk = (node: MindNode, depth: number, parent: Placed | null): Placed => {
    const me: Placed = { node, x: depth * (W + GAP_X), y: 0, depth, parent, hidden: 0 };
    out.push(me);
    const kids = closed.has(node.id) ? [] : node.children;
    me.hidden = closed.has(node.id) ? node.children.length : 0;
    if (!kids.length) { me.y = row * (H + GAP_Y); row += 1; return me; }
    const placed = kids.map((k) => walk(k, depth + 1, me));
    me.y = ((placed[0]?.y ?? 0) + (placed[placed.length - 1]?.y ?? 0)) / 2;
    return me;
  };
  walk(root, 0, null);
  return out;
}

const KIND_LABEL: Record<MindNode['kind'], string> = { company: 'Company', project: 'Project', investigation: 'Investigation', explanation: 'Explanation', evidence: 'Evidence' };

function initialClosed(root: MindNode): Set<string> {
  // A few investigations open to their explanations; many start folded, so the first view stays an overview
  let count = 0;
  const countWalk = (n: MindNode): void => { if (n.kind === 'investigation') count += 1; n.children.forEach(countWalk); };
  countWalk(root);
  const fold = count > 6 ? 'investigation' : 'explanation';
  const s = new Set<string>();
  const walk = (n: MindNode): void => { if (n.kind === fold && n.children.length) s.add(n.id); n.children.forEach(walk); };
  walk(root);
  return s;
}

export function MindMapPage({ workspace, onError }: { workspace: Workspace; onError: (e: unknown) => void }) {
  const navigate = useNavigate();
  const [root, setRoot] = useState<MindNode | null>(null);
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<Placed | null>(null);
  const [query, setQuery] = useState('');
  const [view, setView] = useState({ x: 24, y: 24, k: 1 });
  const box = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);

  useEffect(() => {
    api<MindNode>(`/api/workspaces/${workspace.id}/mindmap`).then((r) => { setRoot(r); setClosed(initialClosed(r)); }).catch(onError);
  }, [workspace.id, onError]);

  const placed = useMemo(() => (root ? layout(root, closed) : []), [root, closed]);
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || !root) return new Set<string>();
    const hit = new Set<string>();
    const walk = (n: MindNode): void => { if (`${n.label} ${n.detail ?? ''}`.toLowerCase().includes(q)) hit.add(n.id); n.children.forEach(walk); };
    walk(root);
    return hit;
  }, [query, root]);

  const fit = useCallback(() => {
    if (!box.current || !placed.length) return;
    const width = Math.max(...placed.map((p) => p.x)) + W, height = Math.max(...placed.map((p) => p.y)) + H;
    const k = Math.min(1.2, Math.max(0.35, Math.min((box.current.clientWidth - 48) / width, (box.current.clientHeight - 48) / height)));
    setView({ x: 24, y: Math.max(24, (box.current.clientHeight - height * k) / 2), k });
  }, [placed]);
  useEffect(() => { fit(); }, [root]);  // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (id: string): void => setClosed((c) => { const n = new Set(c); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const expandAll = (): void => setClosed(new Set());
  const collapseAll = (): void => { if (root) setClosed(initialClosed(root)); };
  const searchOpen = (): void => {  // open every branch that holds a match
    if (!root || !matches.size) return;
    const keep = new Set(closed);
    const walk = (n: MindNode, path: string[]): void => { if (matches.has(n.id)) path.forEach((p) => keep.delete(p)); n.children.forEach((c) => walk(c, [...path, n.id])); };
    walk(root, []);
    setClosed(keep);
  };
  const zoom = (f: number): void => setView((v) => ({ ...v, k: Math.min(2, Math.max(0.3, v.k * f)) }));

  if (!root) return <div className="page-pad"><p className="muted">Loading the map…</p></div>;
  const empty = !root.children.some((p) => p.children.length);
  const width = Math.max(...placed.map((p) => p.x)) + W + 40, height = Math.max(...placed.map((p) => p.y)) + H + 40;

  return (
    <div className="mindmap">
      <div className="map-toolbar">
        <h1>Mind map</h1>
        <span className="muted small">{text(workspace.company)}: every investigation, the explanations it compared and the strongest evidence.</span>
        <span className="grow" />
        <form className="map-search" onSubmit={(e) => { e.preventDefault(); searchOpen(); }}>
          <input value={query} placeholder="Search the map" aria-label="Search the map" onChange={(e) => setQuery(e.target.value)} />
          {query ? <span className="small muted">{matches.size} found</span> : null}
        </form>
        <button type="button" className="button small" onClick={expandAll}>Expand all</button>
        <button type="button" className="button small" onClick={collapseAll}>Collapse</button>
        <button type="button" className="button small" aria-label="Zoom out" onClick={() => zoom(0.85)}>−</button>
        <button type="button" className="button small" aria-label="Zoom in" onClick={() => zoom(1.18)}>+</button>
        <button type="button" className="button small" onClick={fit}>Fit</button>
      </div>
      {empty ? (
        <div className="empty"><h2>Your map grows as you investigate</h2><p>Each investigation appears here under its project, with the explanations it compared.</p>
          <button type="button" className="button primary" onClick={() => navigate('/investigate')}>Start an investigation</button></div>
      ) : (
        <div className="map-canvas" ref={box}
          onWheel={(e) => { if (e.ctrlKey || e.metaKey) { e.preventDefault(); zoom(e.deltaY < 0 ? 1.08 : 0.92); } }}
          onPointerDown={(e) => { if ((e.target as HTMLElement).closest('.mnode, .map-card')) return; drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y }; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); }}
          onPointerMove={(e) => { const d = drag.current; if (d) setView((v) => ({ ...v, x: d.vx + e.clientX - d.x, y: d.vy + e.clientY - d.y })); }}
          onPointerUp={() => { drag.current = null; }}>
          <div className="map-world" style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})`, width, height }} role="tree" aria-label="Mind map of investigations">
            <svg className="map-links" width={width} height={height} aria-hidden="true">
              {placed.filter((p) => p.parent).map((p) => {
                const a = p.parent as Placed, x1 = a.x + W, y1 = a.y + H / 2, x2 = p.x, y2 = p.y + H / 2, mx = (x1 + x2) / 2;
                return <path key={p.node.id} d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`} className={`link l-${p.node.kind}${p.node.direction ? ` l-${p.node.direction}` : ''}`} />;
              })}
            </svg>
            {placed.map((p) => {
              const n = p.node, kids = n.children.length;
              return (
                <div key={n.id} role="treeitem" aria-expanded={kids ? !closed.has(n.id) : undefined} aria-level={p.depth + 1}
                  className={`mnode m-${n.kind}${n.favoured ? ' favoured' : ''}${n.direction ? ` d-${n.direction}` : ''}${matches.has(n.id) ? ' hit' : ''}${selected?.node.id === n.id ? ' selected' : ''}`}
                  style={{ left: p.x, top: p.y, width: W, height: H }}>
                  <button type="button" className="mnode-body" onClick={() => setSelected(p)} onDoubleClick={() => { if (n.kind === 'investigation') navigate(`/investigate/${n.id}`); }}>
                    <span className="mnode-kind">
                      {n.kind === 'company' ? <Icon name="spark" size={11} /> : n.kind === 'project' ? <Icon name="folder" size={11} /> : n.kind === 'investigation' ? <span className={`sdot ${n.status === 'finished' ? 'good' : 'bad'}`} /> : n.kind === 'evidence' ? <b>{n.direction === 'supports' ? '+' : '−'}</b> : null}
                      {n.kind === 'explanation' ? (n.favoured ? '★ Leading explanation' : 'Explanation') : n.kind === 'evidence' ? (n.direction === 'supports' ? 'For' : 'Against') : KIND_LABEL[n.kind]}
                      {n.kind === 'explanation' && n.belief ? <span className="mnode-tag">{n.belief}</span> : null}
                      {n.kind === 'investigation' ? <span className="mnode-tag">{n.status === 'finished' ? 'Finished' : 'Stopped'}</span> : null}
                    </span>
                    <span className="mnode-label">{cut(n.label)}</span>
                  </button>
                  {kids ? <button type="button" className="mnode-fold" aria-label={closed.has(n.id) ? `Show ${kids} more` : 'Hide'} onClick={() => toggle(n.id)}>{closed.has(n.id) ? `+${kids}` : '−'}</button> : null}
                </div>
              );
            })}
          </div>
          {selected ? (
            <div className="map-card" role="dialog" aria-label="Details">
              <div className="row spread"><span className="eyebrow">{KIND_LABEL[selected.node.kind]}</span><button type="button" className="button ghost small" aria-label="Close" onClick={() => setSelected(null)}><Icon name="cross" size={14} /></button></div>
              <p className="map-card-title">{text(selected.node.label)}</p>
              {selected.node.kind === 'investigation' ? (
                <>
                  {selected.node.detail ? <p className="small"><b>Recommendation:</b> {cut(selected.node.detail)}</p> : <p className="small muted">It stopped before a recommendation.</p>}
                  {selected.node.started ? <p className="small muted">{day(selected.node.started)}</p> : null}
                  <button type="button" className="button primary" onClick={() => navigate(`/investigate/${selected.node.id}`)}>Open investigation</button>
                </>
              ) : selected.node.kind === 'explanation' ? (
                <p className="small">Judged <b>{selected.node.belief ?? 'not stated'}</b>. Sources weighed: {selected.node.supports ?? 0} for, {selected.node.contradicts ?? 0} against.</p>
              ) : selected.node.kind === 'evidence' ? (
                <p className="small muted">From: {text(selected.node.detail)}</p>
              ) : <p className="small muted">{selected.node.children.length} item{selected.node.children.length === 1 ? '' : 's'} inside.</p>}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
