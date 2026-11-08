// Model text is untrusted: it is only ever rendered as React text children, never as HTML.
export const text = (value: unknown): string => (typeof value === 'string' ? value : value === undefined || value === null ? '' : JSON.stringify(value));

// Plain words for people who are not analysts (docs/DESIGN_RESEARCH.md, glossary)
export const STAGES: Record<string, string> = {
  brief: 'Understanding the question', frame: 'Defining the decision', evidence: 'Gathering sources', theories: 'Listing possible explanations', assessment: 'Weighing the evidence',
  challenge: 'Stress-testing the favourite', challenge_reading: 'Stress-testing the favourite', test: 'Designing a test', position: 'Forming a view',
  new_evidence: 'Reading new evidence', update: 'Updating the view', conclude: 'Writing the recommendation', done: 'Done',
};
const STOPS: Record<string, string> = {
  finished: 'Finished', 'repeated errors': 'Stopped early: it got stuck', 'turn limit': 'Stopped early: it ran out of time', 'context limit': 'Stopped early: too much to read',
  'left the stage': 'Stopped early', 'stopped by you': 'Stopped by you',
};
export const SHOCK: Record<string, string> = { undermines: 'simulated evidence against a theory', supports: 'simulated evidence for a theory', irrelevant: 'irrelevant simulated evidence' };
const SHORT: Record<string, string> = {
  brief: 'Question', frame: 'Decision', evidence: 'Sources', theories: 'Explanations', assessment: 'Weigh', challenge: 'Stress-test', challenge_reading: 'Stress-test',
  test: 'Test', position: 'View', new_evidence: 'New evidence', update: 'Update', conclude: 'Recommend', done: 'Done',
};
// The seven steps a manager sees, and which controller stages each covers
export const STEPS: { label: string; stages: string[] }[] = [
  { label: 'Understand the question', stages: ['brief', 'frame'] },
  { label: 'Gather sources', stages: ['evidence'] },
  { label: 'List possible explanations', stages: ['theories'] },
  { label: 'Weigh the evidence', stages: ['assessment'] },
  { label: 'Stress-test the favourite', stages: ['challenge', 'challenge_reading'] },
  { label: 'Design a test', stages: ['test'] },
  { label: 'Recommend', stages: ['position', 'new_evidence', 'update', 'conclude', 'done'] },
];
export const stepOf = (stage: unknown): number => Math.max(0, STEPS.findIndex((s) => s.stages.includes(text(stage))));
export const KIND: Record<string, string> = {
  verified_observation: 'Independent source', company_claim: "Company's own claim", analyst_assumption: 'Assumption', proposed_hypothesis: 'Hypothesis',
  synthetic: 'Simulated what-if', web_page: 'Web page (unchecked)',
};
export const kindOf = (cls: unknown): string => KIND[text(cls)] || text(cls);
// Text the model's length limit stopped mid-sentence ends in an ellipsis, so it reads as cut, not as a typo
export const cut = (value: unknown): string => { const t = text(value).trimEnd(); return t.length > 60 && /[A-Za-z0-9]$/.test(t) ? `${t}…` : t; };
export const day = (seconds: number | null | undefined): string => (seconds ? new Date(seconds * 1000).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '');
export const euros = (n: unknown): string => (typeof n === 'number' ? `€${Math.round(n).toLocaleString('en-GB')}` : '—');
export const stageName = (stage: unknown): string => STAGES[text(stage)] || text(stage).replaceAll('_', ' ');
export const shortName = (stage: unknown): string => SHORT[text(stage)] || stageName(stage);
export const stopName = (stop: unknown): string => STOPS[text(stop)] || text(stop) || 'Running';
export const sentence = (value: unknown): string => { const t = text(value).trim(); return t ? t.charAt(0).toUpperCase() + t.slice(1) : t; };
export const shortCompany = (name: unknown): string => text(name).replace(/\s*\([^)]*\)/g, '').trim();

// 'moldex-new-evidence-favours-looks' reads as 'Simulated evidence: favours looks'; a base case has none.
export function variant(id: string): string {
  const rest = text(id).split('-').slice(1).join(' ');
  return rest === 'base' ? 'No new evidence' : `Simulated evidence: ${rest.replace(/^new evidence /, '')}`;
}

export const when = (seconds: number): string => new Date(seconds * 1000).toLocaleString();
