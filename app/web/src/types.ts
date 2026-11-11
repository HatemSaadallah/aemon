// The shapes the FastAPI backend (app/server.py) returns. Model-written fields are typed as unknown or optional
// strings and are only ever rendered as text.

export type StopReason = 'finished' | 'repeated errors' | 'turn limit' | 'context limit' | 'left the stage' | string;
export type Direction = 'undermines' | 'supports' | 'irrelevant';

export interface CallResult {
  error?: string;
  results?: { id?: string; title?: string }[];
  theory_id?: string;
  [key: string]: unknown;
}

export interface Call {
  name: string;
  arguments: Record<string, unknown> | unknown;
  stage?: string;
  accepted: boolean;
  result?: CallResult;
  prefix?: boolean;
  harness?: boolean;
}

export interface Source {
  id: string;
  title: string;
  class: string;
  url: string | null;
  date?: string;
  excerpt?: string;
  simulated?: boolean;
}

export interface Final {
  draft?: boolean;
  stopped_because?: string;
  draft_source?: string;
  recommendation?: string;
  next_action?: string;
  favoured_theory?: string;
  target_customer?: string;
  value_proposition?: string;
  uncertainty?: string;
  company_position?: string;
  would_change_if?: unknown[];
  [key: string]: unknown;
}

export interface Theory {
  claim?: string;
  status?: string;
  [key: string]: unknown;
}

export interface Position {
  favoured_theory?: string;
  recommendation?: string;
  beliefs?: Record<string, string>;
}

export interface StoppingPoint {
  furthest_stage?: string | null;
  stage_at_stop?: string | null;
  calls?: number;
  refused?: number;
}

export interface RunRecord {
  case: string;
  answer_flags?: { check: string; label: string; detail?: string }[];
  finish_guard?: boolean;
  company: string;
  question?: string;
  calls: Call[];
  stop_reason: StopReason | null;
  final: Final | null;
  position?: Position | null;
  theories?: Record<string, Theory>;
  stopping_point?: StoppingPoint;
  coverage?: { shock?: { direction: Direction } | null };
  sources?: Record<string, Source>;
  assessments?: Assessment[];
  tests?: Record<string, Record<string, unknown>>;
  test_declined?: { reason?: string } | null;
  revisions?: { theory_id: string; status: string; reason?: string; evidence_ids?: string[]; new_claim?: string }[];
  challenge_searches?: { theory_id: string; query: string; found?: string[] }[];
  frame?: { objective?: string; alternatives?: string[]; constraints?: string[] };
  memory_used?: string[];
  depth?: string;
  resumed_after_turn?: number;
  continued_after_turn?: number;
}

export interface Workflow {
  stages: { stage: string; tools: string[]; moves_on: string; group: string; optional?: boolean }[];
  tools: Record<string, string>;
}

export interface Workspace {
  id: string;
  company: string;
  description: string;
  base_case: string;
  examples: string[];
  scenarios: { case: string; label: string; question: string }[];
}

export interface TryStatus {
  model_ready: boolean;
  adapter_loaded: boolean;
  model: { id: string; label: string; available: boolean };
  busy: boolean;
  depths?: { id: string; label: string; searches: number; turns: number }[];
}

export interface RunSummary {
  stop_reason: StopReason | null;
  finished: boolean;
  calls: number;
  refused: number;
  stage_at_stop: string | null;
  recommendation: string | null;
  position: string | null;
  draft?: boolean;
}

export interface HistoryEntry {
  id: string;
  question: string;
  case: string;
  started: number | null;
  ended: number | null;
  summary: RunSummary | null;
  error: string | null;
  cached_at: number | null;
  status: 'running' | 'finished' | 'failed' | 'interrupted' | string;
  pinned?: boolean;
  project?: string | null;
}

export interface Project {
  id: string;
  name: string;
  created: number;
}

export interface TryRun {
  status: 'running' | 'finished' | 'failed' | string;
  record: RunRecord | null;
  error: string | null;
  wrapping?: boolean;
  cached_at?: number | null;
  identity?: Record<string, unknown> | null;
}

export interface Outcome {
  index: number;
  stop_reason: StopReason | null;
  finished: boolean;
  furthest: string | null;
  stage_at_stop: string | null;
  calls: number;
  refused: number;
  guards_cleared: boolean;
}

export interface Totals {
  cases: number;
  finished: number;
  refused: number;
  mean_calls: number;
  stop_reasons: Record<string, number>;
}

export type Arm = 'untrained' | 'trained';

export interface Pilot {
  id: string;
  label: string;
  note: string;
  arms: Record<Arm, string>;
  totals: Record<Arm, Totals>;
  cases: ({ case: string; company: string } & Record<Arm, Outcome>)[];
}

export interface PilotsResponse {
  banner: string;
  pilots: Pilot[];
}

export interface BeliefMove {
  theory: string;
  before: string | null;
  after: string | null;
  verdict: string;
}

export interface BeliefsResponse {
  scale: string[];
  arms: {
    pilot: string;
    pilot_label: string;
    arm: Arm;
    arm_label: string;
    cases: { case: string; index: number; direction: Direction; delivered: boolean; read: boolean; revisions: [string, string][]; moves: BeliefMove[] }[];
  }[];
}

export interface LossPoint { step: number; loss: number }
export interface HeldPoint { step: number; eval_loss: number }

export interface TrainingLive {
  state: string | null;
  job?: string;
  updated?: string;
  progress?: { step: number; total: number; elapsed?: string; remaining?: string } | null;
  train?: LossPoint[];
  held_out?: HeldPoint[];
  notes?: string[];
}

// The numbers behind one investigation (app/insights.py): counted from its record, never estimated
export interface BeliefRow { id: string; claim: string; before: string | null; after: string | null; before_step: number | null; after_step: number | null; favoured: boolean }
export interface EvidenceRow { id: string; supports: number; contradicts: number; neutral: number; independent_supports: number; independent_contradicts: number }
export interface TestNumbers { declined: boolean; reason?: string; name?: string; cost?: number; budget?: number; weeks?: number; max_weeks?: number; people?: number; predictions?: Record<string, string>; rule?: string; method?: string; measure?: string; sample?: string }
export interface Metrics {
  confidence: { level: 'High' | 'Moderate' | 'Low'; score: number; out_of: number; checks: { label: string; passed: boolean }[]; action: string; why: string; rule: string } | null;
  finished: boolean;
  beliefs: BeliefRow[];
  scale: string[];
  evidence: EvidenceRow[];
  sources: { class: string; label: string; count: number }[];
  test: TestNumbers | null;
  steps: { total: number; corrected: number; searches: number; reads: number; by_group: { label: string; count: number }[] };
  checks: { passed: number; evaluated: number };
}
export interface Assessment { theory_id: string; evidence_id: string; direction: 'supports' | 'contradicts' | 'neutral'; quote?: string; does_not_show?: string; class?: string }
export interface FollowUpItem { id: string; question: string; answer: string | null; sources: string[]; status: 'answering' | 'answered' | 'not_in_record' | 'failed' | string; created: number }
export interface RunDetail { record: RunRecord; metrics: Metrics; suggestions: string[]; followups: FollowUpItem[]; memory_used: string[]; settings?: { depth?: string; live?: boolean; context?: string | null; asked_online?: boolean; attachments?: { id: string; name: string; kind: string; url?: string; passages: number; words: number }[] } }
export interface MemoryNote { id: string; text: string; project: string | null; workspace: string | null; created: number }
export interface MemoryState { enabled: boolean; global: MemoryNote[]; company: MemoryNote[]; project: MemoryNote[]; limit: number }

// Company directory and profiles (app/companies.py). Facts are curated from the company's dossier and cite it.
export interface Asset { illustrative?: string; file: string; source_url: string; author?: string; licence?: string; licence_url?: string | null; trademark?: boolean; retrieved: string }
export interface Cite { id: string; title: string; date?: string; origin: string; url?: string | null }
export interface Fact { text: string; sources: Cite[]; basis?: 'company' | 'independent' }
export interface CompanySummary { id: string; name: string; legal_name: string; tagline: string | null; industry: string | null; headquarters: string | null; case_year: number | null; accent: string; logo?: Asset | null; banner?: Asset | null; sources: number; independent_sources: number; investigations: number; profiled: boolean }
export interface LibrarySource { id: string; title: string; publisher: string | null; url: string | null; date: string | null; origin: string; kind: string | null; about: string | null; excerpt: string; limitation: string | null; does_not_establish: string | null; after_case: boolean; existing_offering: boolean }
export interface CompanyProfile extends Omit<CompanySummary, 'investigations'> {
  brief_description: string;
  facts: Partial<Record<'industry' | 'headquarters' | 'founded' | 'parent' | 'website', Fact>>;
  case_context: { set_in: string; note: string | null } | null;
  about: Fact[]; customers: Fact[]; markets: Fact[]; positioning: Fact[];
  products: { name: string; description: string; customers?: string | null; sources: Cite[] }[];
  timeline: { date: string; event: string; sources: Cite[] }[];
  context_companies: { name: string; relation_in_records: string; sources: Cite[] }[];
  library: LibrarySource[];
  investigations: HistoryEntry[];
  questions: string[];
  scenarios: { case: string; label: string; question: string }[];
  related: CompanySummary[];
  others: CompanySummary[];
}
