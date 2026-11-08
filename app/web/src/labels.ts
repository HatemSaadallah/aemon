// Model text is untrusted: it is only ever rendered as React text children, never as HTML.
export const text = (value: unknown): string => (typeof value === 'string' ? value : value === undefined || value === null ? '' : JSON.stringify(value));

export const STAGES: Record<string, string> = {
  brief: 'Reading the brief', frame: 'Framing the problem', evidence: 'Gathering evidence', theories: 'Building theories', assessment: 'Weighing evidence',
  challenge: 'Challenging the favourite', challenge_reading: 'Reading what the challenge found', test: 'Designing a test', position: 'Taking a position',
  new_evidence: 'New evidence', update: 'Updating beliefs', conclude: 'Concluding', done: 'Done',
};
const STOPS: Record<string, string> = {
  finished: 'Finished', 'repeated errors': 'Stopped after repeated refusals', 'turn limit': 'Ran out of turns', 'context limit': 'Ran out of context', 'left the stage': 'Left the stage',
};
export const SHOCK: Record<string, string> = { undermines: 'simulated evidence against a theory', supports: 'simulated evidence for a theory', irrelevant: 'irrelevant simulated evidence' };
const SHORT: Record<string, string> = {
  brief: 'Brief', frame: 'Frame', evidence: 'Evidence', theories: 'Theories', assessment: 'Assess', challenge: 'Challenge', challenge_reading: 'Read challenge',
  test: 'Test', position: 'Position', new_evidence: 'New evidence', update: 'Update', conclude: 'Conclude', done: 'Done',
};
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
