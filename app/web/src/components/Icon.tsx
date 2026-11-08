// Small stroke icons for the agent's tools, drawn inline so they follow the text colour in both themes.

export type IconName = 'doc' | 'target' | 'search' | 'zap' | 'book' | 'bulb' | 'scale' | 'flask' | 'ban' | 'flag' | 'refresh' | 'check' | 'cross' | 'dot' | 'spark' | 'pin' | 'trash' | 'folder' | 'more' | 'plus';

const PATHS: Record<IconName, string[]> = {
  doc: ['M6 3h8l4 4v14H6z', 'M14 3v4h4', 'M9 12h6', 'M9 16h6'],
  target: ['M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18', 'M12 7a5 5 0 1 0 0 10a5 5 0 1 0 0-10', 'M12 11a1 1 0 1 0 0 2a1 1 0 1 0 0-2'],
  search: ['M11 4a7 7 0 1 0 0 14a7 7 0 1 0 0-14', 'M16.5 16.5L21 21'],
  zap: ['M13 2L4 14h7l-1 8l9-12h-7z'],
  book: ['M4 5a2 2 0 0 1 2-2h13v15H6a2 2 0 0 0-2 2z', 'M4 20a2 2 0 0 0 2 1h13v-3'],
  bulb: ['M9 18h6', 'M10 21h4', 'M12 3a6 6 0 0 0-4 10.5c.6.6 1 1.4 1 2.5h6c0-1.1.4-1.9 1-2.5A6 6 0 0 0 12 3z'],
  scale: ['M12 3v18', 'M7 21h10', 'M4 7h16', 'M4 7l-2.5 6a3 3 0 0 0 5 0z', 'M20 7l-2.5 6a3 3 0 0 0 5 0z'],
  flask: ['M9 3h6', 'M10 3v6l-5.5 9.5A2 2 0 0 0 6.2 21h11.6a2 2 0 0 0 1.7-2.5L14 9V3', 'M7.5 15h9'],
  ban: ['M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18', 'M5.6 5.6l12.8 12.8'],
  flag: ['M5 21V4', 'M5 4h12l-2.5 4l2.5 4H5'],
  refresh: ['M20 12a8 8 0 1 1-2.4-5.7', 'M20 4v5h-5'],
  check: ['M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18', 'M8 12.5l2.8 2.8L16.5 9'],
  cross: ['M6 6l12 12', 'M18 6L6 18'],
  dot: ['M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6'],
  spark: ['M12 3v4', 'M12 17v4', 'M3 12h4', 'M17 12h4', 'M6 6l2.5 2.5', 'M15.5 15.5L18 18', 'M18 6l-2.5 2.5', 'M8.5 15.5L6 18'],
  pin: ['M9 4h6l-1 6l3 3H7l3-3z', 'M12 13v8'],
  trash: ['M4 7h16', 'M9 7V4h6v3', 'M6 7l1 13h10l1-13', 'M10 11v6', 'M14 11v6'],
  folder: ['M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'],
  more: ['M6 12h.01', 'M12 12h.01', 'M18 12h.01'],
  plus: ['M12 5v14', 'M5 12h14'],
};

export function Icon({ name, size = 16 }: { name: IconName; size?: number }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {PATHS[name].map((d) => <path key={d} d={d} />)}
    </svg>
  );
}

// Each tool: its icon, its family (which sets the colour) and a short verb for the call strip.
export const TOOLS: Record<string, { icon: IconName; family: string; verb: string }> = {
  read_brief: { icon: 'doc', family: 'problem', verb: 'Brief' },
  frame_problem: { icon: 'target', family: 'problem', verb: 'Frame' },
  search_evidence: { icon: 'search', family: 'evidence', verb: 'Search' },
  read_source: { icon: 'book', family: 'evidence', verb: 'Read' },
  challenge_theory: { icon: 'zap', family: 'challenge', verb: 'Challenge' },
  add_theory: { icon: 'bulb', family: 'theory', verb: 'Theory' },
  assess_evidence: { icon: 'scale', family: 'assess', verb: 'Weigh' },
  propose_test: { icon: 'flask', family: 'experiment', verb: 'Test' },
  decline_test: { icon: 'ban', family: 'experiment', verb: 'No test' },
  state_position: { icon: 'flag', family: 'conclusion', verb: 'Position' },
  revise_theory: { icon: 'refresh', family: 'revision', verb: 'Revise' },
  finish: { icon: 'check', family: 'conclusion', verb: 'Finish' },
};

export const toolOf = (name: string): { icon: IconName; family: string; verb: string } => TOOLS[name] ?? { icon: 'dot', family: 'other', verb: name || 'Unreadable' };
