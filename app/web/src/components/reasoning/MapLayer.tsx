import { useEffect, useState, type ReactNode } from 'react';

// The reasoning map over the whole page below the top bar, wherever it is opened from (a report, a live run).
// Escape or the back button closes it; the page underneath keeps its scroll position.

export function MapLayer({ title, back, onClose, children }: { title: string; back: string; onClose: () => void; children: ReactNode }) {
  const [top, setTop] = useState(0);
  useEffect(() => {
    const measure = (): void => setTop(Math.max(0, document.querySelector('.top')?.getBoundingClientRect().bottom ?? 0));
    measure();
    window.addEventListener('resize', measure);
    document.body.classList.add('map-layer-open');
    const key = (e: KeyboardEvent): void => { if (e.key === 'Escape' && !document.querySelector('.map-layer .rpanel') && !(e.target as HTMLElement | null)?.closest('input')) onClose(); };  // with a details panel open, Escape closes the panel first
    window.addEventListener('keydown', key, true);  // capture: sees whether a panel was open before the map closes it
    return () => { window.removeEventListener('resize', measure); window.removeEventListener('keydown', key, true); document.body.classList.remove('map-layer-open'); };
  }, [onClose]);
  return (
    <div className="map-layer" style={{ top }} role="dialog" aria-modal="true" aria-label={`Reasoning map: ${title}`}>
      <header className="map-head">
        <button type="button" className="button small" onClick={onClose}>‹ {back}</button>
        <h1>{title}</h1>
      </header>
      {children}
    </div>
  );
}
