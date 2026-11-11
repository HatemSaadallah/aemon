import { Link } from 'react-router-dom';
import { Icon } from './Icon.tsx';

// The three views of one investigation, the same on the report and on its map: Report, Reasoning map, Sources.
// The map has its own address (/map/<id>), so a map always belongs to the investigation named above it.
export function InvTabs({ id, active, sources, onPick }: { id: string; active: 'report' | 'map' | 'sources'; sources?: number; onPick?: (v: 'report' | 'sources') => void }) {
  const tab = (key: 'report' | 'map' | 'sources', label: React.ReactNode) => {
    const on = active === key;
    if (key !== 'map' && onPick) return <button type="button" role="tab" aria-selected={on} onClick={() => onPick(key)}>{label}</button>;
    return <Link role="tab" aria-selected={on} to={key === 'map' ? `/map/${id}` : `/investigate/${id}`} state={key === 'sources' ? { view: 'sources' } : undefined}>{label}</Link>;
  };
  return (
    <nav className="itabs" role="tablist" aria-label="Investigation views">
      {tab('report', <><Icon name="doc" size={14} /> Report</>)}
      {tab('map', <><Icon name="map" size={14} /> Reasoning map</>)}
      {tab('sources', <><Icon name="book" size={14} /> Sources{sources !== undefined ? <span className="itab-n">{sources}</span> : null}</>)}
    </nav>
  );
}
