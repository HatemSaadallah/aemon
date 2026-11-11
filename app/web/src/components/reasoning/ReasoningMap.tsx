import { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { cut, kindOf, text } from '../../labels.ts';
import type { Assessment, RunRecord } from '../../types.ts';
import { Icon, type IconName } from '../Icon.tsx';
import { StepsList } from '../StepsList.tsx';
import { buildGraph, type EdgeKind, type GEdge, type Graph, layout, type Level, type Options, type Placed, related, structureKey } from './graph.ts';

// Semantic zoom: a few stable detail levels with hysteresis, so the level changes only when the zoom clearly crosses a
// threshold, never on every frame (docs/REASONING_MAP.md)
const UP: Record<Level, number> = { 0: 0.64, 1: 1.3, 2: Infinity }, DOWN: Record<Level, number> = { 0: -Infinity, 1: 0.56, 2: 1.18 };
const levelFor = (k: number, now: Level): Level => { let l = now; while (l < 2 && k >= UP[l]) l = (l + 1) as Level; while (l > 0 && k < DOWN[l]) l = (l - 1) as Level; return l; };

// The Strategy Reasoning Map: the investigation's recorded reasoning, question to recommendation. Performance choices
// (docs/REASONING_MAP.md): the graph and its layout are memoized on the record's structure and the view options; pan
// and zoom write the transform straight to the DOM in requestAnimationFrame (no React state, no CSS transition); cards
// are memoized; edges are one SVG. It shows what the agent recorded, not that its reasoning is right.

const KIND: Record<string, { label: string; icon: IconName }> = {
  question: { label: 'Strategic question', icon: 'target' }, hypothesis: { label: 'Hypothesis', icon: 'bulb' }, group: { label: 'Evidence', icon: 'book' },
  evidence: { label: 'Source', icon: 'book' }, challenge: { label: 'Challenge', icon: 'zap' }, experiment: { label: 'Experiment', icon: 'flask' },
  declined: { label: 'Experiment', icon: 'ban' }, simulated: { label: 'Simulated result', icon: 'spark' }, revision: { label: 'Revision', icon: 'refresh' },
  recommendation: { label: 'Recommendation', icon: 'flag' },
};
const EDGE: Record<EdgeKind, string> = { considers: 'considers', supports: 'supports', contradicts: 'contradicts', no_bearing: 'no bearing', challenges: 'challenges', tests: 'tested by', observed: 'observed', revises: 'revises', favours: 'favoured in', cites: 'cited by' };
type View = { x: number; y: number; k: number };

const Card = memo(function Card({ n, level, state, onSelect, onToggle, names }: { n: Placed; level: Level; state: '' | 'selected' | 'dim' | 'hit'; onSelect: (id: string) => void; onToggle: (id: string) => void; names: Record<string, string> }) {
  const k = KIND[n.kind] ?? { label: n.kind, icon: 'dot' as IconName };
  const dir = n.direction === 'supports' ? 'for' : n.direction === 'contradicts' ? 'against' : n.direction ? 'none' : '';
  return (
    <div className={`rnode r-${n.kind} lv${level}${dir ? ` dir-${dir}` : ''}${n.favoured ? ' favoured' : ''}${state ? ` ${state}` : ''}`} style={{ transform: `translate(${n.x}px, ${n.y}px)`, width: n.w, height: n.h }}>
      <button type="button" className="rnode-body" onClick={() => onSelect(n.id)} aria-label={`${k.label}: ${n.title}`}>
        <span className="rnode-kind"><Icon name={k.icon} size={12} />{n.kind === 'hypothesis' ? names[n.theory ?? ''] ?? k.label : n.kind === 'group' ? (dir === 'for' ? 'Supporting' : dir === 'against' ? 'Opposing' : 'No bearing') : k.label}
          {n.favoured ? <span className="rtag">Favoured</span> : null}
          {level > 0 && n.kind === 'recommendation' && n.status !== 'final' ? <span className="rtag warn">{n.status === 'draft' ? 'Draft' : n.status === 'interim' ? 'Interim view' : 'Incomplete'}</span> : null}
          {level > 0 && n.kind === 'recommendation' && n.flags ? <span className="rtag warn">{n.flags} warning{n.flags === 1 ? '' : 's'}</span> : null}
          {n.kind === 'simulated' ? <span className="rtag sim">Not evidence</span> : null}
          {level > 0 && n.kind === 'challenge' ? <span className="rtag">{n.count} found</span> : null}
        </span>
        <span className="rnode-title">{level === 2 ? n.title : cut(n.title)}</span>
        {level === 1 && n.sub && n.kind !== 'group' ? <span className="rnode-sub">{cut(n.sub)}</span> : null}
        {level >= 1 && n.tally ? <span className="rnode-tally"><span className="t-for">{n.tally.for} for</span><span className="t-against">{n.tally.against} against</span><span>{n.tally.none} no bearing</span></span> : null}
        {level === 2 && n.detail?.length ? (
          <span className="rnode-detail">{n.detail.map((d, i) => (
            <span key={i} className={`rd${d.tone ? ` rd-${d.tone}` : ''}`}>{d.label ? <span className="rd-label">{d.label}</span> : null}<span className="rd-text">{d.text}</span></span>
          ))}</span>
        ) : null}
      </button>
      {n.kind === 'group' || n.kind === 'hypothesis' ? (
        <button type="button" className="rnode-fold" onClick={() => onToggle(n.id)} aria-label={n.kind === 'group' ? `Show the ${n.count} sources` : 'Show or hide this hypothesis\'s sources'}>
          {n.kind === 'group' ? <>+{n.count}</> : <Icon name="list" size={12} />}
        </button>
      ) : null}
    </div>
  );
});

function path(a: Placed, b: Placed): string {
  const ltr = a.x <= b.x;
  const x1 = ltr ? a.x + a.w : a.x, y1 = a.y + a.h / 2, x2 = ltr ? b.x : b.x + b.w, y2 = b.y + b.h / 2;
  if (a.x === b.x) { const xr = a.x + a.w, mx = xr + 40; return `M${xr},${y1} C${mx},${y1} ${mx},${y2} ${xr},${y2}`; }
  const mx = (x1 + x2) / 2;
  return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
}

const Edges = memo(function Edges({ edges, at, focus, width, height }: { edges: GEdge[]; at: Map<string, Placed>; focus: Set<string> | null; width: number; height: number }) {
  return (
    <svg className="redges" width={width + 120} height={height + 40} aria-hidden="true">
      <defs><marker id="rarrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor" /></marker></defs>
      {edges.map((e) => {
        const a = at.get(e.from), b = at.get(e.to);
        if (!a || !b) return null;
        const on = !focus || (focus.has(e.from) && focus.has(e.to));
        return <path key={e.id} d={path(a, b)} className={`redge e-${e.kind}${on ? '' : ' dim'}`} markerEnd="url(#rarrow)" />;
      })}
    </svg>
  );
});

export function ReasoningMap({ record, live = false, onOpenReport }: { record: RunRecord; live?: boolean; onOpenReport?: (section: string) => void }) {
  // On a phone the canvas cannot show the reasoning at a readable size, so the map opens on its text outline
  const [mode, setMode] = useState<'overview' | 'evidence' | 'timeline' | 'outline'>(() => (window.matchMedia('(max-width: 700px)').matches ? 'outline' : 'overview'));
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [show, setShow] = useState<Options['show']>({ supports: true, contradicts: true, no_bearing: true, challenges: true, experiments: true });
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [mini, setMini] = useState(false);  // shown when the map is larger than the screen
  const box = useRef<HTMLDivElement>(null), world = useRef<HTMLDivElement>(null), viewRect = useRef<SVGRectElement>(null);
  const view = useRef<View>({ x: 40, y: 40, k: 1 });
  const frame = useRef(0);
  const fitted = useRef(false);
  const [level, setLevel] = useState<Level>(1);
  const levelRef = useRef<Level>(1);
  const anchor = useRef<{ id: string; fx: number; fy: number; sx: number; sy: number } | null>(null);
  const focusPt = useRef<{ x: number; y: number } | null>(null);

  const key = structureKey(record);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const graph: Graph = useMemo(() => buildGraph(record, { expanded, mode: mode === 'evidence' ? 'evidence' : 'overview', show }), [key, expanded, mode, show]);
  const { placed, width, height } = useMemo(() => { (window as unknown as { __rmapLayouts?: number }).__rmapLayouts = ((window as unknown as { __rmapLayouts?: number }).__rmapLayouts ?? 0) + 1; return layout(graph, level); }, [graph, level]);
  const at = useMemo(() => new Map(placed.map((p) => [p.id, p])), [placed]);
  const focus = useMemo(() => related(graph, selected), [graph, selected]);
  const hits = useMemo(() => { const q = query.trim().toLowerCase(); return q ? new Set(placed.filter((p) => `${p.title} ${p.sub ?? ''}`.toLowerCase().includes(q)).map((p) => p.id)) : null; }, [query, placed]);

  const placedRef = useRef<Placed[]>([]);
  placedRef.current = placed;
  const apply = useCallback(() => {  // one DOM write per frame; the detail level changes only across a threshold
    frame.current = 0;
    const v = view.current;
    const next = levelFor(v.k, levelRef.current);
    if (next !== levelRef.current) {
      // keep the card under the focal point (the pointer, or the centre) under it after the cards change size
      const b0 = box.current, fp = focusPt.current ?? (b0 ? { x: b0.clientWidth / 2, y: b0.clientHeight / 2 } : { x: 0, y: 0 });
      const wx = (fp.x - v.x) / v.k, wy = (fp.y - v.y) / v.k;
      let best: Placed | null = null, bd = Infinity;
      for (const p of placedRef.current) { const dx = Math.max(p.x - wx, 0, wx - p.x - p.w), dy = Math.max(p.y - wy, 0, wy - p.y - p.h), d = dx * dx + dy * dy; if (d < bd) { bd = d; best = p; } }
      if (best) anchor.current = { id: best.id, fx: Math.min(1, Math.max(0, (wx - best.x) / best.w)), fy: Math.min(1, Math.max(0, (wy - best.y) / best.h)), sx: fp.x, sy: fp.y };
      levelRef.current = next;
      setLevel(next);
    }
    if (world.current) world.current.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.k})`;
    const b = box.current, r = viewRect.current;
    if (b && r) { r.setAttribute('x', String(-v.x / v.k)); r.setAttribute('y', String(-v.y / v.k)); r.setAttribute('width', String(b.clientWidth / v.k)); r.setAttribute('height', String(b.clientHeight / v.k)); }
  }, []);
  const schedule = useCallback(() => { if (!frame.current) frame.current = requestAnimationFrame(apply); }, [apply]);
  useEffect(() => () => { if (frame.current) cancelAnimationFrame(frame.current); }, []);
  useLayoutEffect(() => {  // a new detail level: put the anchored card back under the focal point
    const a = anchor.current; if (!a) return;
    anchor.current = null;
    const p = placed.find((x) => x.id === a.id); if (!p) return;
    const k = view.current.k;
    view.current = { k, x: a.sx - (p.x + a.fx * p.w) * k, y: a.sy - (p.y + a.fy * p.h) * k };
    if (world.current) world.current.style.transform = `translate(${view.current.x}px, ${view.current.y}px) scale(${k})`;
    schedule();
  }, [placed, schedule]);

  const fit = useCallback((whole = false) => {
    const b = box.current;
    if (!b) return;
    // Opens at the overview level, the default reading level: the whole map when it fits there, otherwise its middle at
    // the smallest overview scale. "Fit" (whole) shows everything, falling back to the bird's-eye level when needed.
    const one = layout(graph, 1), zero = layout(graph, 0);
    const kOf = (w: number, h: number): number => Math.min((b.clientWidth - 60) / w, (b.clientHeight - 60) / h);
    const k1 = Math.min(1.2, kOf(one.width, one.height));  // up to 1.2, still the overview level
    const useOne = !whole || k1 >= 0.62;
    const L: Level = useOne ? 1 : 0;
    const w = useOne ? one.width : zero.width, h = useOne ? one.height : zero.height;
    const k = useOne ? Math.max(0.62, k1) : Math.min(0.62, Math.max(0.3, kOf(zero.width, zero.height)));
    setMini(w * k > b.clientWidth - 20 || h * k > b.clientHeight - 20);
    view.current = { k, x: w * k < b.clientWidth ? (b.clientWidth - w * k) / 2 : 32, y: (b.clientHeight - h * k) / 2 };
    focusPt.current = null; anchor.current = null;
    levelRef.current = L; setLevel(L);
    schedule();
  }, [graph, schedule]);
  // Fit once when the map first has content; later updates (expanding, live events) keep the user's view
  useEffect(() => { if (mode === 'overview' || mode === 'evidence') { fitted.current = false; } }, [mode]);
  useEffect(() => { if (!fitted.current && placed.length && mode !== 'timeline' && mode !== 'outline') { fitted.current = true; fit(); } }, [placed.length, fit, mode]);

  const zoomAt = useCallback((f: number, cx?: number, cy?: number) => {
    const b = box.current; if (!b) return;
    const v = view.current, k = Math.min(2.2, Math.max(0.25, v.k * f));
    const px = cx ?? b.clientWidth / 2, py = cy ?? b.clientHeight / 2;
    focusPt.current = { x: px, y: py };
    view.current = { k, x: px - ((px - v.x) * k) / v.k, y: py - ((py - v.y) * k) / v.k };
    schedule();
  }, [schedule]);
  const centreOn = useCallback((id: string) => {
    const p = at.get(id), b = box.current; if (!p || !b) return;
    const k = Math.max(view.current.k, 0.85);
    focusPt.current = null;
    view.current = { k, x: b.clientWidth / 2 - (p.x + p.w / 2) * k - 180, y: b.clientHeight / 2 - (p.y + p.h / 2) * k };
    schedule();
  }, [at, schedule]);

  useEffect(() => {  // wheel: zoom around the pointer (passive: false so the page does not scroll)
    const b = box.current; if (!b) return;
    const onWheel = (e: WheelEvent): void => { e.preventDefault(); const r = b.getBoundingClientRect(); zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top); };
    b.addEventListener('wheel', onWheel, { passive: false });
    return () => b.removeEventListener('wheel', onWheel);
  }, [zoomAt, mode]);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const onDown = (e: React.PointerEvent): void => {
    if ((e.target as HTMLElement).closest('.rnode, .rmini, .rpanel')) return;
    drag.current = { x: e.clientX, y: e.clientY, vx: view.current.x, vy: view.current.y };
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
  };
  const onMove = (e: React.PointerEvent): void => { const d = drag.current; if (!d) return; view.current = { ...view.current, x: d.vx + e.clientX - d.x, y: d.vy + e.clientY - d.y }; schedule(); };
  const onUp = (): void => { drag.current = null; };
  const onKey = (e: React.KeyboardEvent): void => {
    if (e.key === '+' || e.key === '=') zoomAt(1.15); else if (e.key === '-') zoomAt(1 / 1.15); else if (e.key === '0') fit(true); else if (e.key === 'Escape') setSelected(null);
  };

  const select = useCallback((id: string) => setSelected((s) => (s === id ? null : id)), []);
  const toggle = useCallback((id: string) => setExpanded((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; }), []);
  const stateOf = (id: string): '' | 'selected' | 'dim' | 'hit' => (id === selected ? 'selected' : hits ? (hits.has(id) ? 'hit' : 'dim') : focus && !focus.has(id) ? 'dim' : '');
  const node = selected ? at.get(selected) ?? null : null;
  const assessments: Assessment[] = record.assessments ?? [];

  return (
    <div className="rmap">
      <div className="rbar" role="toolbar" aria-label="Map controls">
        <div className="seg" role="radiogroup" aria-label="View">
          {([['overview', 'Overview'], ['evidence', 'Evidence'], ['timeline', 'Timeline'], ['outline', 'Outline']] as const).map(([id, label]) => <button key={id} type="button" role="radio" aria-checked={mode === id} onClick={() => setMode(id)}>{label}</button>)}
        </div>
        {mode === 'overview' || mode === 'evidence' ? (
          <>
            <label className="field rsearch"><Icon name="search" size={14} /><input type="search" placeholder="Find a hypothesis, claim or source" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && hits?.size) centreOn([...hits][0] as string); }} aria-label="Find on the map" /></label>
            <Filters show={show} setShow={setShow} />
            <span className="grow" />
            <span className="rlevel" title={`${level === 0 ? 'Structure' : level === 1 ? 'Overview' : 'Detail'} level. Zoom in for more detail on every card, out for the overall structure.`}><span className={`lvdots l${level}`} aria-hidden="true"><i /><i /><i /></span>{level === 0 ? 'Structure' : level === 1 ? 'Overview' : 'Detail'}</span>
            <div className="rzoomg" role="group" aria-label="Zoom">
              <button type="button" aria-label="Zoom out" title="Zoom out (−)" onClick={() => zoomAt(1 / 1.2)}>−</button>
              <button type="button" title="Fit the whole map (0)" onClick={() => { setSelected(null); setQuery(''); setExpanded(new Set()); fit(true); }}>Fit</button>
              <button type="button" aria-label="Zoom in" title="Zoom in (+)" onClick={() => zoomAt(1.2)}>+</button>
            </div>
            <button type="button" className={`button small ghost${mini ? ' on' : ''}`} aria-pressed={mini} title="Minimap" onClick={() => { setMini(!mini); window.setTimeout(schedule, 0); }}><Icon name="map" size={14} /></button>
            <button type="button" className="button small rgo" title="Go to the recommendation" onClick={() => { setSelected('r'); centreOn('r'); }}><Icon name="flag" size={13} /><span>Recommendation</span></button>
          </>
        ) : null}
      </div>

      {mode === 'timeline' ? <div className="rtimeline"><p className="muted small">Every action the agent took, in order, including the refused ones.</p><StepsList record={record} live={live} /></div> : mode === 'outline' ? (
        <Outline record={record} graph={graph} />
      ) : (
        <div className="rcanvas" ref={box} tabIndex={0} onKeyDown={onKey} onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}
          aria-label="Reasoning map. Drag to pan, scroll to zoom, plus and minus keys to zoom, 0 to fit. The Outline view has the same content as text.">
          <div className="rworld" ref={world} style={{ width: width + 120, height: height + 40 }}>
            <Edges edges={graph.edges} at={at} focus={hits ?? focus} width={width} height={height} />
            {placed.map((p) => <Card key={p.id} n={p} level={level} state={stateOf(p.id)} onSelect={select} onToggle={toggle} names={graph.names} />)}
          </div>
          <Legend />
          {mini ? (
            <svg className="rmini" viewBox={`-20 -20 ${width + 160} ${height + 80}`} onClick={(e) => {
              const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect(), b = box.current; if (!b) return;
              const mx = ((e.clientX - r.left) / r.width) * (width + 160) - 20, my = ((e.clientY - r.top) / r.height) * (height + 80) - 20;
              const k = view.current.k; view.current = { k, x: b.clientWidth / 2 - mx * k, y: b.clientHeight / 2 - my * k }; schedule();
            }} role="img" aria-label="Overview of the whole map; click to move there">
              {placed.map((p) => <rect key={p.id} x={p.x} y={p.y} width={p.w} height={p.h} rx={10} className={`mini-${p.kind}`} />)}
              <rect ref={viewRect} className="mini-view" rx={8} />
            </svg>
          ) : null}
          {node ? <Panel n={node} record={record} graph={graph} assessments={assessments} onClose={() => setSelected(null)} onOpenReport={onOpenReport} onFocus={centreOn} onExpand={toggle} /> : null}
          {live ? <p className="rlive"><span className="pulse" aria-hidden="true" /> Live: new steps appear as the agent records them</p> : null}
        </div>
      )}
      <p className="rnote muted small">A map of the agent's recorded reasoning (Strategy Agent V1), not a check that it is right. Quotes are verified against their sources; the agent's readings and conclusions are not.</p>
    </div>
  );
}

// The edge and card types to show, folded into one control so the toolbar stays calm
const KINDS = [['supports', 'Supporting'], ['contradicts', 'Opposing'], ['no_bearing', 'No bearing'], ['challenges', 'Challenges'], ['experiments', 'Experiments']] as const;
function Filters({ show, setShow }: { show: Options['show']; setShow: (f: (s: Options['show']) => Options['show']) => void }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return undefined;
    const close = (e: MouseEvent | KeyboardEvent): void => { if (e instanceof KeyboardEvent ? e.key === 'Escape' : !box.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', close); document.addEventListener('keydown', close);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', close); };
  }, [open]);
  const hidden = KINDS.filter(([k]) => !show[k]).length;
  return (
    <div className="rpop" ref={box}>
      <button type="button" className={`button small${hidden ? ' on' : ''}`} aria-expanded={open} onClick={() => setOpen(!open)}><Icon name="list" size={14} /> Filters{hidden ? <span className="itab-n">{hidden} hidden</span> : null}</button>
      {open ? (
        <div className="rpop-panel" role="group" aria-label="Show on the map">
          {KINDS.map(([k, label]) => (
            <label key={k} className="rpop-row"><input type="checkbox" checked={show[k]} onChange={() => setShow((s) => ({ ...s, [k]: !s[k] }))} /><span className={`ln ln-${k === 'experiments' ? 'tests' : k}`} aria-hidden="true" />{label}</label>
          ))}
          <button type="button" className="button ghost small" disabled={!hidden} onClick={() => setShow(() => ({ supports: true, contradicts: true, no_bearing: true, challenges: true, experiments: true }))}>Show everything</button>
        </div>
      ) : null}
    </div>
  );
}

function Legend() {
  const [open, setOpen] = useState(false);
  return (
    <div className={`rlegend${open ? ' open' : ''}`}>
      <button type="button" className="button small" aria-expanded={open} onClick={() => setOpen(!open)}>Legend</button>
      {open ? (
        <ul>
          <li><span className="sw sw-question" /> Strategic question</li><li><span className="sw sw-hypothesis" /> Hypothesis (★ favoured)</li>
          <li><span className="ln ln-supports" /> supports</li><li><span className="ln ln-contradicts" /> contradicts</li><li><span className="ln ln-no_bearing" /> no bearing</li>
          <li><span className="ln ln-challenges" /> challenges</li><li><span className="ln ln-tests" /> tested by</li><li><span className="ln ln-revises" /> revises</li>
          <li><span className="sw sw-simulated" /> Simulated result: never evidence</li><li><span className="sw sw-recommendation" /> Recommendation</li>
        </ul>
      ) : null}
    </div>
  );
}

function Panel({ n, record, graph, assessments, onClose, onOpenReport, onFocus, onExpand }: { n: Placed; record: RunRecord; graph: Graph; assessments: Assessment[]; onClose: () => void; onOpenReport?: (s: string) => void; onFocus: (id: string) => void; onExpand: (id: string) => void }) {
  const k = KIND[n.kind]?.label ?? n.kind;
  const ins = graph.edges.filter((e) => e.to === n.id || e.from === n.id);
  const quote = (a: Assessment, i: number) => {
    const s = record.sources?.[a.evidence_id];
    return (
      <li key={i} className={`pq q-${a.direction}`}>
        <span className="prov prov-quote">Quoted</span> “{text(a.quote)}”
        <span className="muted small block">{s ? `${text(s.title)}${s.date ? ` · ${text(s.date).slice(0, 10)}` : ''} · ${kindOf(s.class)}` : a.evidence_id}</span>
        {a.does_not_show ? <span className="small block"><span className="prov prov-reading">Agent's reading</span> Does not show: {cut(a.does_not_show)}</span> : null}
      </li>
    );
  };
  let body: React.ReactNode = null;
  if (n.kind === 'hypothesis') {
    const t = record.theories?.[n.theory ?? ''] as Record<string, unknown> | undefined;
    const mine = assessments.filter((a) => a.theory_id === n.theory);
    const chall = ((record.challenge_searches ?? []) as unknown as { theory_id: string; query: string; found?: string[] }[]).filter((c) => c.theory_id === n.theory);
    const revs = ((record.revisions ?? []) as unknown as { theory_id: string; status: string; reason?: string }[]).filter((v) => v.theory_id === n.theory);
    body = (
      <>
        <p className="ptitle">{text(t?.claim)}</p>
        <p className="small"><span className="prov prov-agent">Agent's hypothesis</span>{n.favoured ? ' · favoured in the recommendation' : ''}</p>
        {t?.why_behaviour_changes ? <p className="small"><b>Why customers would change:</b> {cut(t.why_behaviour_changes)}</p> : null}
        {t?.how_value_is_captured ? <p className="small"><b>How the company earns from it:</b> {cut(t.how_value_is_captured)}</p> : null}
        <h4>Supporting ({mine.filter((a) => a.direction === 'supports').length})</h4><ul className="plist">{mine.filter((a) => a.direction === 'supports').map(quote)}</ul>
        <h4>Opposing ({mine.filter((a) => a.direction === 'contradicts').length})</h4>{mine.some((a) => a.direction === 'contradicts') ? <ul className="plist">{mine.filter((a) => a.direction === 'contradicts').map(quote)}</ul> : <p className="muted small">None weighed: this hypothesis was not tested against opposing evidence.</p>}
        {chall.length ? <><h4>Challenges</h4><ul className="plist">{chall.map((c, i) => <li key={i}>Searched “{text(c.query)}”: {c.found?.length ?? 0} source{c.found?.length === 1 ? '' : 's'} found</li>)}</ul></> : null}
        {revs.length ? <><h4>Revisions</h4><ul className="plist">{revs.map((v, i) => <li key={i}><b>{text(v.status)}</b>: {cut(v.reason)}</li>)}</ul></> : null}
        <button type="button" className="button small" onClick={() => onExpand(n.id)}>Show its sources on the map</button>
      </>
    );
  } else if (n.kind === 'evidence' || n.kind === 'group') {
    const list = n.kind === 'group' ? assessments.filter((a) => a.theory_id === n.theory && a.direction === n.direction) : assessments.filter((a) => a.evidence_id === n.ref);
    const s = n.ref ? record.sources?.[n.ref] : undefined;
    body = (
      <>
        {s ? <p className="ptitle">{s.url ? <a href={s.url} target="_blank" rel="noreferrer noopener">{text(s.title)}</a> : text(s.title)}</p> : <p className="ptitle">{text(n.title)}</p>}
        {s ? <p className="small muted">{kindOf(s.class)}{s.date ? ` · ${text(s.date).slice(0, 10)}` : ' · date unknown'}</p> : null}
        {s?.excerpt ? <blockquote className="pexcerpt">“{text(s.excerpt)}”</blockquote> : null}
        <h4>How the agent used it</h4>
        <ul className="plist">{list.map((a, i) => <li key={i}><b>{a.direction === 'supports' ? 'Supports' : a.direction === 'contradicts' ? 'Contradicts' : 'No bearing on'}</b> {graph.names[a.theory_id] ?? a.theory_id}{quote(a, i)}</li>)}</ul>
        {s?.class === 'company_claim' ? <p className="notice quiet small-notice">The company's own claim: not independent evidence.</p> : null}
        <p className="muted small">Evidence kinds are the dossier's labels, about 80% reliable on our audit.</p>
        {n.kind === 'group' ? <button type="button" className="button small" onClick={() => onExpand(n.id)}>Show these sources on the map</button> : null}
      </>
    );
  } else if (n.kind === 'experiment') {
    const t = (record.tests ?? {})[n.ref ?? ''] as Record<string, unknown> | undefined;
    body = (
      <>
        <p className="ptitle">{text(t?.name)}</p>
        <p className="small"><span className="prov prov-agent">Proposed by the agent</span> · not run</p>
        {t?.method ? <p className="small">{cut(t.method)}</p> : null}
        {t?.sample ? <p className="small"><b>Sample:</b> {cut(t.sample)}</p> : null}
        {t?.measure ? <p className="small"><b>Measure:</b> {cut(t.measure)}</p> : null}
        {t?.prediction_by_theory ? <><h4>Competing predictions</h4><ul className="plist">{Object.entries(t.prediction_by_theory as Record<string, string>).map(([tid, p]) => <li key={tid}><b>{graph.names[tid] ?? tid}:</b> {cut(p)}</li>)}</ul></> : null}
        {t?.decision_rule ? <p className="small"><b>Decision rule:</b> {cut(t.decision_rule)}</p> : null}
        <p className="muted small">Sample sizes, thresholds and costs are the agent's proposed parameters, not facts. The mechanical experiment check is lenient: most tests it accepts fail stricter design screens.</p>
      </>
    );
  } else if (n.kind === 'declined') {
    body = <><p className="ptitle">The agent declined to test</p><p className="small">{cut(record.test_declined?.reason)}</p></>;
  } else if (n.kind === 'simulated') {
    const s = record.sources?.[n.ref ?? ''];
    body = <><p className="ptitle">{text(s?.title)}</p><p className="small"><span className="prov prov-simulated">Simulated</span> A what-if result written for the case. Never evidence about real demand.</p>{s?.excerpt ? <blockquote className="pexcerpt">“{text(s.excerpt)}”</blockquote> : null}</>;
  } else if (n.kind === 'revision' || n.kind === 'challenge') {
    body = <><p className="ptitle">{text(n.title)}</p>{n.sub ? <p className="small">{cut(n.sub)}</p> : null}</>;
  } else if (n.kind === 'recommendation') {
    const f = record.final;
    body = (
      <>
        <p className="ptitle">{text(n.title)}</p>
        <p className="small"><span className="prov prov-agent">Agent's conclusion</span>{n.status === 'draft' ? ' · draft written after the run stopped early' : n.status === 'interim' ? ' · interim view: the run stopped before recommending' : n.status === 'none' ? ' · the run stopped before recommending' : ''}</p>
        {record.answer_flags?.length ? <div className="notice warn small-notice"><b>Check before relying on this answer.</b><ul>{record.answer_flags.map((x) => <li key={x.check}>{x.label}</li>)}</ul></div> : null}
        {f?.next_action ? <p className="small"><b>Next step:</b> {cut(f.next_action)}</p> : null}
        {f?.uncertainty ? <p className="small"><b>Still uncertain:</b> {cut(f.uncertainty)}</p> : null}
        {Array.isArray(f?.would_change_if) && f.would_change_if.length ? <><h4>Would change if</h4><ul className="plist">{f.would_change_if.map((x, i) => <li key={i}>{cut(x)}</li>)}</ul></> : null}
        {onOpenReport ? <button type="button" className="button small" onClick={() => onOpenReport('summary')}>Open in the report</button> : null}
      </>
    );
  } else if (n.kind === 'question') {
    body = <><p className="ptitle">{text(n.title)}</p>{record.frame?.objective ? <p className="small"><b>Objective as framed:</b> {cut(record.frame.objective)}</p> : null}
      {record.frame?.alternatives?.length ? <><h4>Alternatives considered</h4><ul className="plist">{record.frame.alternatives.map((a, i) => <li key={i}>{cut(a)}</li>)}</ul></> : null}</>;
  }
  return (
    <aside className="rpanel" aria-label={`${k} details`}>
      <div className="rpanel-head"><span className="eyebrow">{k}</span><button type="button" className="button ghost small" aria-label="Close details" onClick={onClose}><Icon name="cross" size={14} /></button></div>
      <div className="rpanel-body">{body}</div>
      {ins.length ? <div className="rpanel-links"><h4>Connections</h4><ul className="plist">{ins.map((e) => { const other = e.from === n.id ? e.to : e.from; const o = graph.nodes.find((x) => x.id === other); return o ? <li key={e.id}><button type="button" className="link small" onClick={() => onFocus(other)}>{e.from === n.id ? EDGE[e.kind] : `${EDGE[e.kind]} (from)`}: {cut(o.kind === 'hypothesis' ? graph.names[o.theory ?? ''] ?? o.title : o.title).slice(0, 70)}</button></li> : null; })}</ul></div> : null}
    </aside>
  );
}

// The same content as text, for keyboard and screen-reader use and for printing
function Outline({ record, graph }: { record: RunRecord; graph: Graph }) {
  const a = record.assessments ?? [];
  return (
    <div className="routline">
      <h3>Question</h3><p>{text(record.question)}</p>
      {Object.entries(record.theories ?? {}).map(([tid, t]) => (
        <section key={tid}><h3>{graph.names[tid]}{(record.final?.favoured_theory ?? record.position?.favoured_theory) === tid ? ' (favoured)' : ''}</h3><p>{text(t.claim)}</p>
          <ul>{a.filter((x) => x.theory_id === tid).map((x, i) => <li key={i}><b>{x.direction === 'supports' ? 'Supports' : x.direction === 'contradicts' ? 'Contradicts' : 'No bearing'}:</b> “{text(x.quote)}” ({text(record.sources?.[x.evidence_id]?.title ?? x.evidence_id)})</li>)}</ul>
        </section>
      ))}
      {Object.values(record.tests ?? {}).map((t, i) => <section key={i}><h3>Experiment (proposed)</h3><p>{text((t as Record<string, unknown>).name)}: {cut((t as Record<string, unknown>).method)}</p></section>)}
      {record.test_declined ? <section><h3>Experiment declined</h3><p>{cut(record.test_declined.reason)}</p></section> : null}
      <h3>Recommendation</h3><p>{record.final ? text(record.final.recommendation) : record.position ? `Interim view: ${text(record.position.recommendation)}` : 'None: the investigation stopped first.'}</p>
    </div>
  );
}
