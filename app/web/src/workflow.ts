import { useEffect, useState } from 'react';
import { api } from './api.ts';
import { STAGES } from './labels.ts';
import type { Workflow } from './types.ts';

// The controller's own table, from /api/workflow, which a test checks against the code. Loaded once and shared.
let promise: Promise<Workflow> | null = null;
export const loadWorkflow = (): Promise<Workflow> =>
  (promise = promise || api<Workflow>('/api/workflow').catch((error: unknown) => { promise = null; throw error; }));

export function useWorkflow(): Workflow | null {
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  useEffect(() => {
    let live = true;
    loadWorkflow().then((w) => { if (live) setWorkflow(w); }).catch(() => {});
    return () => { live = false; };
  }, []);
  return workflow;
}

export const stageOrderOf = (workflow: Workflow | null): string[] => (workflow ? [...workflow.stages.map((s) => s.stage), 'done'] : Object.keys(STAGES));
export const groupsOf = (workflow: Workflow | null): Record<string, string> => (workflow ? Object.fromEntries(workflow.stages.map((s) => [s.stage, s.group])) : {});
