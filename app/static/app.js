'use strict';
// Model text is untrusted. Everything goes through textContent, and nothing is ever built as HTML.

const $ = (id) => document.getElementById(id);

function el(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (key === 'class') node.className = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null && value !== false) node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child !== null && child !== undefined && child !== false) node.append(child);
  }
  return node;
}

async function api(path, options) {
  const response = await fetch(path, { credentials: 'same-origin', ...options });
  if (response.status === 401) { location.replace('/login'); throw new Error('Signed out'); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed: ${response.status}`);
  return data;
}

function showError(error) {
  const box = $('error');
  box.textContent = error.message || String(error);
  box.hidden = false;
  clearTimeout(showError.timer);
  showError.timer = setTimeout(() => { box.hidden = true; }, 6000);
}

const text = (value) => (typeof value === 'string' ? value : value === undefined || value === null ? '' : JSON.stringify(value));
const chip = (kind, label) => el('span', { class: `chip ${kind}` }, label);

const STAGES = {
  brief: 'Reading the brief', frame: 'Framing the problem', evidence: 'Gathering evidence', theories: 'Building theories', assessment: 'Weighing evidence',
  challenge: 'Challenging the favourite', challenge_reading: 'Reading what the challenge found', test: 'Designing a test', position: 'Taking a position',
  new_evidence: 'New evidence', update: 'Updating beliefs', conclude: 'Concluding', done: 'Done',
};
const STOPS = {
  finished: 'Finished', 'repeated errors': 'Stopped after repeated refusals', 'turn limit': 'Ran out of turns', 'context limit': 'Ran out of context', 'left the stage': 'Left the stage',
};
const SHOCK = { undermines: 'simulated evidence against a theory', supports: 'simulated evidence for a theory', irrelevant: 'irrelevant simulated evidence' };
const SHORT = {
  brief: 'Brief', frame: 'Frame', evidence: 'Evidence', theories: 'Theories', assessment: 'Assess', challenge: 'Challenge', challenge_reading: 'Read challenge',
  test: 'Test', position: 'Position', new_evidence: 'New evidence', update: 'Update', conclude: 'Conclude', done: 'Done',
};
const stageName = (stage) => STAGES[stage] || text(stage).replaceAll('_', ' ');
const shortName = (stage) => SHORT[stage] || stageName(stage);
const sentence = (value) => { const t = text(value).trim(); return t ? t.charAt(0).toUpperCase() + t.slice(1) : t; };

// The controller's own table, from /api/workflow. A test checks it against the controller, so nothing here can drift.
let workflowPromise = null;
const workflowData = () => (workflowPromise = workflowPromise || api('/api/workflow').catch((error) => { workflowPromise = null; throw error; }));
let stageOrder = Object.keys(STAGES);
workflowData().then((w) => { stageOrder = [...w.stages.map((s) => s.stage), 'done']; }).catch(() => {});
const stopName = (stop) => STOPS[stop] || text(stop) || 'Running';

// One investigation as readable steps

function sourceTitle(record, id) {
  const source = record.sources && record.sources[id];
  if (!source) return text(id);
  return source.url ? el('a', { href: source.url, target: '_blank', rel: 'noreferrer noopener' }, source.title) : source.title;
}

function quote(body, record, id) {
  return el('figure', { class: 'quote' }, el('blockquote', {}, text(body)), el('figcaption', {}, sourceTitle(record, id)));
}

// What the model did, in words. Arguments come from the model, so every field is read defensively.
function describe(call, record) {
  const a = call.arguments && typeof call.arguments === 'object' ? call.arguments : {};
  const r = call.result && typeof call.result === 'object' ? call.result : {};
  switch (call.name) {
    case 'read_brief': return ['Read the brief'];
    case 'frame_problem': return ['Framed the problem', el('p', {}, text(a.objective))];
    case 'search_evidence': return [`Searched for “${text(a.query)}”`, Array.isArray(r.results) ? el('p', { class: 'muted' }, r.results.length ? `Found ${r.results.map((x) => text(x.title)).join('; ')}` : 'Found nothing') : null];
    case 'challenge_theory': return [`Looked for evidence against ${text(a.theory_id)}: “${text(a.query)}”`];
    case 'read_source': return [el('span', {}, 'Read ', sourceTitle(record, a.id))];
    case 'add_theory': return [`Proposed theory ${text(r.theory_id || '')}`.trim(), el('p', {}, text(a.claim)), a.why_behaviour_changes ? el('p', { class: 'muted' }, `Why: ${text(a.why_behaviour_changes)}`) : null];
    case 'assess_evidence': return [`Weighed evidence for ${text(a.theory_id)}: ${text(a.direction)}`, a.quote ? quote(a.quote, record, a.evidence_id) : null, a.does_not_show ? el('p', { class: 'muted' }, `Does not show: ${text(a.does_not_show)}`) : null];
    case 'propose_test': return [`Proposed a test: ${text(a.name)}`, el('p', {}, text(a.method)), a.decision_rule ? el('p', { class: 'muted' }, `Decision rule: ${text(a.decision_rule)}`) : null];
    case 'decline_test': return ['Decided no test is worth running', el('p', {}, text(a.reason))];
    case 'state_position': return [`Took a position: favours ${text(a.favoured_theory)}`, el('p', {}, text(a.recommendation))];
    case 'revise_theory': return [`Marked ${text(a.theory_id)} as ${text(a.status)}`, el('p', {}, text(a.reason))];
    case 'finish': return ['Finished with a recommendation', el('p', {}, text(a.recommendation))];
    default: return [text(call.name) || 'Unreadable call'];
  }
}

function step(call, record, number) {
  const [title, ...body] = describe(call, record);
  const refused = !call.accepted;
  const reason = call.result && call.result.error;
  return el('li', { class: `step${refused ? ' refused' : ''}${call.prefix ? ' replayed' : ''}` },
    el('div', { class: 'step-head' }, el('span', { class: 'step-n' }, String(number)), el('span', { class: 'step-title' }, title),
      call.harness ? chip('quiet', 'by the harness') : null, refused ? chip('bad', 'Refused') : null),
    refused && reason ? el('p', { class: 'reason' }, `Why: ${text(reason)}`) : null, ...body);
}

// Steps grouped under the stage they happened in, so the shape of the run is visible at a glance.
function timeline(record) {
  const groups = [];
  record.calls.forEach((call, index) => {
    const last = groups[groups.length - 1];
    if (last && last.stage === call.stage) last.calls.push([call, index + 1]);
    else groups.push({ stage: call.stage, calls: [[call, index + 1]] });
  });
  return el('div', { class: 'timeline' }, groups.map((group) => {
    const refused = group.calls.filter(([c]) => !c.accepted).length;
    return el('section', { class: 'stage' }, el('h4', {}, stageName(group.stage), el('span', { class: 'muted' }, ` · ${group.calls.length} ${group.calls.length === 1 ? 'step' : 'steps'}${refused ? `, ${refused} refused` : ''}`)),
      el('ol', { class: 'steps' }, group.calls.map(([call, n]) => step(call, record, n))));
  }));
}

// The same run as a tree: stage visits in the order they happened, each holding its calls.

function visits(record) {
  const out = [];
  record.calls.forEach((call, index) => {
    const last = out[out.length - 1];
    if (last && last.stage === call.stage) last.calls.push([call, index + 1]);
    else out.push({ stage: call.stage, calls: [[call, index + 1]] });
  });
  return out;
}

// One line saying what a call was about. Model text, so it is only ever set as text.
function gist(call, record) {
  const a = call.arguments && typeof call.arguments === 'object' ? call.arguments : {};
  const r = call.result && typeof call.result === 'object' ? call.result : {};
  const found = Array.isArray(r.results) ? `, ${r.results.length} found` : '';
  switch (call.name) {
    case 'read_brief': return 'the company, the question and the budgets';
    case 'frame_problem': return text(a.objective);
    case 'search_evidence': return `“${text(a.query)}”${found}`;
    case 'challenge_theory': return `against ${text(a.theory_id)}: “${text(a.query)}”${found}`;
    case 'read_source': { const source = record.sources && record.sources[a.id]; return source ? text(source.title) : text(a.id); }
    case 'add_theory': return `${r.theory_id ? `${text(r.theory_id)}: ` : ''}${text(a.claim)}`;
    case 'assess_evidence': return `${text(a.theory_id)} ${text(a.direction)}: “${text(a.quote)}”`;
    case 'propose_test': return text(a.name);
    case 'decline_test': return text(a.reason);
    case 'state_position': return `favours ${text(a.favoured_theory)}: ${text(a.recommendation)}`;
    case 'revise_theory': return `${text(a.theory_id)} ${text(a.status)}: ${text(a.reason)}`;
    case 'finish': return text(a.recommendation);
    default: return '';
  }
}

const treeState = new Map();  // run key -> indexes of collapsed stage visits, kept across live updates
let runMode = 'tree';
try { runMode = localStorage.getItem('strategy-lab-run-view') || 'tree'; } catch (error) { /* storage may be blocked */ }

function furthestVisit(vs) {
  let best = -1, at = -1;
  vs.forEach((v, i) => { const rank = stageOrder.indexOf(v.stage); if (rank >= best) { best = rank; at = i; } });
  return at;
}

function endMarker(record) {
  if (!record.stop_reason) return { kind: 'warn', icon: '…', label: 'Running' };
  if (record.final) return { kind: 'good', icon: '✓', label: 'Finished' };
  const at = record.stopping_point && record.stopping_point.stage_at_stop;
  return { kind: 'bad', icon: '■', label: `${stopName(record.stop_reason)}${at && at !== 'done' ? `, in ${shortName(at)}` : ''}` };
}

function pathStrip(vs, record, onPick) {
  const top = furthestVisit(vs);
  const end = endMarker(record);
  return el('ol', { class: 'path', 'aria-label': 'Path through the stages' },
    vs.map((v, i) => {
      const refused = v.calls.filter(([c]) => !c.accepted).length;
      return el('li', {}, el('button', { type: 'button', class: `pill${i === top ? ' furthest' : ''}${refused ? ' has-refused' : ''}`, onclick: () => onPick(i),
        title: `${stageName(v.stage)}: ${v.calls.length} ${v.calls.length === 1 ? 'call' : 'calls'}${refused ? `, ${refused} refused` : ''}${i === top ? ' · furthest stage reached' : ''}` },
        el('span', {}, shortName(v.stage)), el('span', { class: 'pill-n' }, String(v.calls.length)),
        refused ? el('span', { class: 'pill-refused' }, `⚠ ${refused}`) : null));
    }),
    el('li', {}, el('span', { class: `pill end ${end.kind}` }, `${end.icon} ${end.label}`)));
}

function runTree(record, key, onlyLast) {
  const vs = visits(record);
  if (!treeState.has(key)) treeState.set(key, { collapsed: new Set(), opened: new Set() });
  const state = treeState.get(key);
  // In the chat only the current stage starts open, so a long run stays readable; whatever the user toggles is kept.
  const isOpen = (i) => (state.opened.has(i) ? true : state.collapsed.has(i) ? false : !onlyLast || i === vs.length - 1);
  const collapsed = { add: (i) => { state.collapsed.add(i); state.opened.delete(i); }, delete: (i) => { state.opened.add(i); state.collapsed.delete(i); } };
  const top = furthestVisit(vs);
  const end = endMarker(record);
  const nodes = vs.map((v, i) => {
    const refused = v.calls.filter(([c]) => !c.accepted).length;
    const id = `visit-${key.replace(/[^a-z0-9]/gi, '-')}-${i}`;
    const open = isOpen(i);
    const list = el('ol', { class: 'leaves', id, hidden: !open },
      v.calls.map(([call, n]) => {
        const ok = call.accepted;
        const reason = call.result && call.result.error;
        return el('li', { class: `leaf${ok ? '' : ' refused'}${call.prefix ? ' replayed' : ''}` },
          el('span', { class: 'leaf-icon', 'aria-hidden': 'true' }, ok ? '✓' : '✕'),
          el('div', { class: 'leaf-body' },
            el('div', { class: 'leaf-head' }, el('span', { class: 'leaf-n' }, String(n)), el('code', { class: 'tool-name' }, text(call.name)),
              el('span', { class: 'visually-hidden' }, ok ? 'accepted' : 'refused'), !ok ? chip('bad', 'Refused') : null,
              call.prefix ? chip('quiet', 'recorded teacher step') : null, call.harness ? chip('quiet', 'by the harness') : null),
            gist(call, record) ? el('p', { class: 'leaf-gist' }, gist(call, record)) : null,
            !ok && reason ? el('p', { class: 'reason' }, `Why refused: ${text(reason)}`) : null));
      }));
    const toggle = el('button', { type: 'button', class: 'visit-toggle', 'aria-expanded': String(open), 'aria-controls': id, onclick: () => {
      const now = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', String(now));
      list.hidden = !now;
      if (now) collapsed.delete(i); else collapsed.add(i);
    } },
      el('span', { class: 'chev', 'aria-hidden': 'true' }, '▸'),
      el('span', { class: 'visit-name' }, stageName(v.stage)),
      el('span', { class: 'muted small' }, `${v.calls.length} ${v.calls.length === 1 ? 'call' : 'calls'}${refused ? `, ${refused} refused` : ''}`),
      i === top ? chip('quiet', 'furthest') : null);
    return el('li', { class: `visit g-${groupOf(v.stage)}${refused ? ' has-refused' : ''}`, 'data-visit': String(i) }, toggle, list);
  });
  const body = el('div', { class: 'tree-wrap' });
  const all = (open) => () => {
    vs.forEach((_, i) => (open ? collapsed.delete(i) : collapsed.add(i)));
    body.querySelectorAll('.visit-toggle').forEach((t) => t.setAttribute('aria-expanded', String(open)));
    body.querySelectorAll('.leaves').forEach((l) => { l.hidden = !open; });
  };
  const pick = (i) => {
    collapsed.delete(i);
    const node = body.querySelector(`[data-visit="${i}"]`);
    if (node) {
      node.querySelector('.visit-toggle').setAttribute('aria-expanded', 'true');
      node.querySelector('.leaves').hidden = false;
      node.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      node.querySelector('.visit-toggle').focus({ preventScroll: true });
    }
  };
  const parts = [
    pathStrip(vs, record, pick),
    el('div', { class: 'row' }, el('button', { type: 'button', class: 'quiet-button', onclick: all(true) }, 'Expand all'), el('button', { type: 'button', class: 'quiet-button', onclick: all(false) }, 'Collapse all')),
    el('ol', { class: 'tree' }, nodes,
      el('li', { class: `visit tree-end ${end.kind}` }, el('span', { class: 'end-mark' }, `${end.icon} ${end.label}`),
        null)),
  ];
  body.replaceChildren(...parts);
  return body;
}

let groupIndex = {};
workflowData().then((w) => { groupIndex = Object.fromEntries(w.stages.map((s) => [s.stage, s.group])); }).catch(() => {});
const groupOf = (stage) => groupIndex[stage] || 'other';

function stepsCard(record, key) {
  const card = el('div', { class: 'card' });
  const draw = () => {
    const button = (mode, label) => el('button', { type: 'button', 'aria-pressed': String(runMode === mode), onclick: () => {
      runMode = mode;
      try { localStorage.setItem('strategy-lab-run-view', mode); } catch (error) { /* storage may be blocked */ }
      draw();
    } }, label);
    card.replaceChildren(
      el('div', { class: 'row spread' }, el('h3', {}, 'What the agent did'), el('div', { class: 'segmented', role: 'group', 'aria-label': 'View' }, button('tree', 'Tree'), button('steps', 'Steps'))),
      runMode === 'steps' ? timeline(record) : runTree(record, key));
  };
  draw();
  return card;
}

function conclusion(final) {
  const rows = [['Recommendation', final.recommendation], ['Next action', final.next_action], ['Favoured theory', final.favoured_theory], ['Customer', final.target_customer],
    ['Proposition', final.value_proposition], ['Uncertainty', final.uncertainty]].filter(([, v]) => v);
  return el('div', { class: 'card conclusion' }, el('h3', {}, 'Conclusion'),
    el('dl', { class: 'pairs' }, rows.flatMap(([k, v]) => [el('dt', {}, k), el('dd', {}, text(v))])),
    Array.isArray(final.would_change_if) && final.would_change_if.length ? [el('p', { class: 'muted' }, 'Would change if'), el('ul', {}, final.would_change_if.map((x) => el('li', {}, text(x))))] : null);
}

function investigation(record, label, key) {
  const point = record.stopping_point || {};
  const shock = record.coverage && record.coverage.shock;
  const running = !record.stop_reason;
  return [
    el('div', { class: 'card' },
      el('div', { class: 'row spread' }, el('h2', {}, record.company), label ? chip('quiet', label) : null),
      el('p', { class: 'lead' }, record.question),
      el('div', { class: 'chips' },
        chip(running ? 'warn' : record.final ? 'good' : 'bad', running ? 'Running' : stopName(record.stop_reason)),
        point.stage_at_stop && !record.final ? chip('quiet', running ? `Now: ${stageName(point.stage_at_stop)}` : `Stopped while ${stageName(point.stage_at_stop).toLowerCase()}`) : null,
        chip('quiet', `${record.calls.length} steps, ${record.calls.filter((c) => !c.accepted).length} refused`),
        shock ? chip('warn', `Case includes ${SHOCK[shock.direction] || 'simulated evidence'}`) : null),
      el('p', { class: 'muted small' }, 'Written by the model. Refused steps were blocked by the harness and changed nothing.')),
    record.final ? conclusion(record.final) : null,
    stepsCard(record, key || `${record.case}/${label}`),
  ].filter(Boolean);
}

// Try it: a chat inside one company workspace. A question runs only on that company's own dossier, and each
// workspace keeps its own history on the server, per user.

const chat = { data: null, spaces: [], ws: null, threads: {}, loaded: {}, busy: false };
let polling = null;
const WS_KEY = 'lexsi.workspace';
const storedWorkspace = () => { try { return localStorage.getItem(WS_KEY); } catch { return null; } };
const storeWorkspace = (id) => { try { localStorage.setItem(WS_KEY, id); } catch { /* private window: the choice is not remembered */ } };
const space = (id = chat.ws) => chat.spaces.find((w) => w.id === id);
const thread = (id = chat.ws) => (chat.threads[id] = chat.threads[id] || []);
const shortCompany = (name) => text(name).replace(/\s*\([^)]*\)/g, '').trim();

function closing(record) {
  if (record.final) {
    const f = record.final;
    const theory = record.theories && record.theories[f.favoured_theory];
    const rows = [['Recommendation', f.recommendation], ['Favoured theory', theory ? `${text(f.favoured_theory)}: ${text(theory.claim)}` : f.favoured_theory],
      ['Next action', f.next_action], ['Uncertainty', f.uncertainty]].filter(([, v]) => v);
    return el('div', { class: 'msg-body closing' },
      el('p', { class: 'closing-head' }, chip('good', '✓ Finished'), ` ${record.company}`),
      el('dl', { class: 'pairs' }, rows.flatMap(([k, v]) => [el('dt', {}, k), el('dd', {}, text(v))])),
      Array.isArray(f.would_change_if) && f.would_change_if.length ? [el('p', { class: 'muted small' }, 'Would change if'), el('ul', {}, f.would_change_if.map((x) => el('li', {}, text(x))))] : null);
  }
  const at = record.stopping_point && record.stopping_point.stage_at_stop;
  const position = record.position;
  return el('div', { class: 'msg-body closing stopped' },
    el('p', { class: 'closing-head' }, chip('bad', `■ ${stopName(record.stop_reason)}`), ` I stopped before finishing${at && at !== 'done' ? `, while ${stageName(at).toLowerCase()}` : ''}, so there is no recommendation.`),
    position ? el('p', {}, `My position so far: I favour ${text(position.favoured_theory)}. ${text(position.recommendation)}`) : null,
    el('p', { class: 'muted small' }, `${record.calls.length} steps, ${record.calls.filter((c) => !c.accepted).length} refused by the harness. The tree above shows where it went wrong.`));
}

function runBody(r, key) {
  const refused = r.calls.filter((c) => !c.accepted).length;
  return el('div', { class: 'msg-body run' },
    el('div', { class: 'row spread' }, el('strong', {}, `Investigating ${r.company}`),
      chip(r.stop_reason ? (r.final ? 'good' : 'bad') : 'warn', r.stop_reason ? stopName(r.stop_reason) : `Working: ${shortName(r.stopping_point && r.stopping_point.stage_at_stop)}`)),
    el('p', { class: 'muted small' }, `${r.calls.length} steps${r.stop_reason ? '' : ' so far'}, ${refused} refused. Open a stage to see its calls.`),
    runTree(r, key, !r.stop_reason));
}

// An earlier investigation from the saved history: a short summary, with the full tree on request.
function pastBody(m) {
  const s = m.entry.summary;
  const status = m.entry.status;
  const head = status === 'running' ? chip('warn', 'Still running') : status === 'interrupted' ? chip('bad', '■ Interrupted by a restart')
    : status === 'failed' ? chip('bad', '■ Failed') : s && s.finished ? chip('good', '✓ Finished') : chip('bad', `■ ${stopName(s && s.stop_reason)}`);
  const lines = [];
  if (s && s.recommendation) lines.push(el('p', {}, el('strong', {}, 'Recommendation: '), text(s.recommendation)));
  else if (s && s.position) lines.push(el('p', {}, el('strong', {}, 'Position before it stopped: '), text(s.position)));
  else if (s && !s.finished) lines.push(el('p', { class: 'muted small' }, `Stopped before a recommendation${s.stage_at_stop && s.stage_at_stop !== 'done' ? `, while ${stageName(s.stage_at_stop).toLowerCase()}` : ''}.`));
  if (m.entry.error) lines.push(el('p', { class: 'small bad-text' }, text(m.entry.error)));
  const open = async () => {
    try {
      const { record } = await api(`/api/workspaces/${m.ws}/history/${m.entry.id}`);
      m.kind = 'opened';
      m.record = record;
      drawChat();
    } catch (error) { showError(error); }
  };
  return el('div', { class: 'msg-body past' },
    el('div', { class: 'row' }, head, m.entry.cached_at ? chip('warn', 'Saved result') : null, s ? el('span', { class: 'muted small' }, `${s.calls} steps, ${s.refused} refused`) : null,
      m.entry.started ? el('span', { class: 'muted small' }, new Date(m.entry.started * 1000).toLocaleString()) : null),
    lines,
    status !== 'running' && s ? el('button', { type: 'button', class: 'link', onclick: open }, 'Show the investigation') : null);
}

function messageNode(m) {
  if (m.who === 'user') return el('div', { class: 'msg user' }, el('div', { class: 'msg-body' }, text(m.text)));
  const body = (() => {
    switch (m.kind) {
      case 'run': return m.record ? runBody(m.record, m.key) : el('div', { class: 'msg-body' }, el('p', { class: 'muted' }, `Starting an investigation of ${m.company}…`));
      case 'past': return pastBody(m);
      case 'opened': return [runBody(m.record, `history/${m.entry.id}`), closing(m.record)];
      case 'closing': return closing(m.record);
      case 'saved': return el('div', { class: 'msg-body' },
        el('p', {}, chip('warn', 'Saved result'), ' ', el('span', { class: 'muted small' }, `from ${new Date(m.at * 1000).toLocaleString()}`)),
        el('p', { class: 'muted small' }, 'The same question, model and code give the same investigation, so it was shown from the saved run instead of running again.'),
        el('button', { type: 'button', class: 'link', disabled: chat.busy, onclick: () => send(m.request[0], m.request[1], m.request[2], true) }, 'Run it again live'));
      case 'error': return el('div', { class: 'msg-body error-msg' }, text(m.text));
      default: return el('div', { class: 'msg-body' }, m.nodes || text(m.text));
    }
  })();
  if (Array.isArray(body)) return el('div', { class: 'stack' }, body.map((b) => el('div', { class: 'msg agent' }, el('span', { class: 'avatar', 'aria-hidden': 'true' }, 'A'), b)));
  return el('div', { class: 'msg agent' }, el('span', { class: 'avatar', 'aria-hidden': 'true' }, 'A'), body);
}

function intro(w) {
  return { who: 'agent', kind: 'text', nodes: [
    el('p', {}, el('strong', {}, w.company), `: ${w.description}`),
    el('p', {}, `I investigate whether ${shortCompany(w.company)} should build a consumer proposition: I frame the problem, build rival theories, weigh quoted evidence from ${shortCompany(w.company)}'s own dossier, challenge my favourite, design a test or say why one is not worth it, and recommend.`),
    el('p', { class: 'muted small' }, 'Each question starts a fresh investigation from this company’s own evidence only. I do not answer follow-ups about an earlier run. A run takes one to three minutes.')] };
}

function drawChat() {
  const list = $('chat-list');
  const w = space();
  if (!list || !w) return;
  const near = list.scrollHeight - list.scrollTop - list.clientHeight < 80;
  const messages = thread();
  const idle = !chat.busy;
  const prompts = idle ? [
    el('p', { class: 'suggest-label' }, 'Ask'),
    el('div', { class: 'suggest', role: 'group', 'aria-label': `Example questions about ${w.company}` },
      w.examples.map((q, i) => el('button', { type: 'button', class: 'suggestion', onclick: () => send(q, w.base_case, i === 0) }, q))),
    w.scenarios.length ? [el('p', { class: 'suggest-label' }, 'Or run a what-if'),
      el('div', { class: 'suggest', role: 'group', 'aria-label': 'What-if scenarios' },
        w.scenarios.map((s) => el('button', { type: 'button', class: 'suggestion small', onclick: () => send(s.label, s.case, true) }, s.label)))] : null] : [];
  list.replaceChildren(messageNode(intro(w)), ...messages.map(messageNode), ...prompts.flat());
  if (near) list.scrollTop = list.scrollHeight;
  const input = $('chat-input'), button = $('chat-send');
  const ready = chat.data && chat.data.model_ready && chat.data.model.available;
  if (input) { input.disabled = chat.busy || !ready; input.placeholder = `Ask about ${shortCompany(w.company)}…`; }
  if (button) button.disabled = chat.busy || !ready;
  for (const b of document.querySelectorAll('.ws-switch button')) b.setAttribute('aria-pressed', String(b.dataset.ws === chat.ws));
  const status = $('chat-status');
  if (status) {
    const elsewhere = chat.busy && !polling;
    status.textContent = elsewhere ? 'Another investigation is running on the model server. This page will be ready when it ends.' : '';
    status.hidden = !elsewhere;
    clearTimeout(drawChat.retry);
    if (elsewhere) drawChat.retry = setTimeout(() => { if (!$('try').hidden) renderTry().catch(showError); }, 5000);
  }
}

async function loadHistory(id) {
  if (chat.loaded[id]) return;
  const { entries } = await api(`/api/workspaces/${id}/history`);
  const live = thread(id).filter((m) => m.live);
  chat.threads[id] = [...entries.flatMap((entry) => [{ who: 'user', text: entry.question }, { who: 'agent', kind: 'past', entry, ws: id }]).filter((m, i, all) => {
    const entry = m.entry || (all[i + 1] && all[i + 1].entry);
    return !live.some((l) => l.id === (entry && entry.id));  // a run watched live in this page is shown live, not twice
  }), ...live];
  chat.loaded[id] = true;
}

async function choose(id) {
  chat.ws = id;
  storeWorkspace(id);
  drawChat();
  try { await loadHistory(id); } catch (error) { showError(error); }
  if (chat.ws === id) drawChat();
}

// question is what the user sees; asCase runs the case's own question, so its date and framing stay as written.
async function send(question, caseId, asCase, fresh = false) {
  question = text(question).trim();
  const w = space();
  if (!question || chat.busy || !w) return;
  const messages = thread(w.id);
  messages.push({ who: 'user', text: question, live: true });
  chat.busy = true;
  const run = { who: 'agent', kind: 'run', company: w.company, record: null, live: true, request: [question, caseId, asCase] };
  messages.push(run);
  drawChat();
  try {
    const body = { workspace: w.id, case: caseId || w.base_case };
    if (asCase) body.shown = question; else body.question = question;
    if (fresh) body.fresh = true;
    const { id } = await api('/api/try', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    run.key = `try/${id}`;
    run.id = id;
    messages[messages.length - 2].id = id;
    watch(id, run, messages);
  } catch (error) {
    chat.busy = false;
    messages.splice(messages.indexOf(run), 1, { who: 'agent', kind: 'error', text: `I could not start: ${error.message}`, live: true });
    drawChat();
  }
}

function watch(id, run, messages) {
  clearInterval(polling);
  let shown = '';
  const tick = async () => {
    try {
      const data = await api(`/api/try/${id}`);
      const now = data.record ? `${data.record.calls.length}|${data.record.stop_reason}|${data.status}` : data.status;
      if (now !== shown) {
        shown = now;
        if (data.record) run.record = data.record;
        if (data.status !== 'running') {
          clearInterval(polling);
          polling = null;
          chat.busy = false;
          if (data.error) messages.push({ who: 'agent', kind: 'error', text: `The run failed: ${data.error}`, live: true });
          else if (data.record) messages.push({ who: 'agent', kind: 'closing', record: data.record, live: true });
          if (data.cached_at) messages.push({ who: 'agent', kind: 'saved', at: data.cached_at, request: run.request, live: true });
        }
        drawChat();
      }
    } catch (error) { clearInterval(polling); polling = null; chat.busy = false; messages.push({ who: 'agent', kind: 'error', text: error.message, live: true }); drawChat(); }
  };
  polling = setInterval(tick, 2000);
  tick();
}

async function renderTry() {
  const [data, spaces] = await Promise.all([api('/api/try'), chat.spaces.length ? null : api('/api/workspaces')]);
  chat.data = data;
  if (spaces) chat.spaces = spaces.workspaces;
  if (!polling) chat.busy = data.busy;  // a run started elsewhere still blocks a new one
  if (!chat.spaces.length) { $('try').replaceChildren(el('div', { class: 'card' }, el('p', {}, 'No company workspaces are configured.'))); return; }
  if (!space()) chat.ws = space(storedWorkspace()) ? storedWorkspace() : chat.spaces[0].id;
  const input = el('textarea', { id: 'chat-input', rows: 1, maxlength: 400, placeholder: 'Ask…', 'aria-label': 'Your question',
    onkeydown: (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); const q = input.value; input.value = ''; send(q); } },
    oninput: () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 160)}px`; } });
  const sendButton = el('button', { id: 'chat-send', type: 'button', class: 'primary', onclick: () => { const q = input.value; input.value = ''; send(q); } }, 'Send');
  const problem = !data.model_ready ? 'The model server is not running: start ./app/run_model.sh.'
    : !data.model.available ? `${data.model.label} is not loaded on the model server yet.` : null;
  $('try').replaceChildren(el('div', { class: 'chat' },
    el('div', { class: 'workspaces' },
      el('div', { class: 'ws-switch', role: 'group', 'aria-label': 'Company workspace' },
        chat.spaces.map((w) => el('button', { type: 'button', 'data-ws': w.id, 'aria-pressed': String(w.id === chat.ws), onclick: () => choose(w.id) }, shortCompany(w.company)))),
      ),
    el('div', { class: 'chat-list', id: 'chat-list', 'aria-live': 'polite' }),
    el('div', { class: 'composer' },
      el('div', { class: 'composer-row' }, input, sendButton),
      problem ? el('p', { class: 'small warn-text' }, problem) : null,
      el('p', { class: 'small warn-text', id: 'chat-status', role: 'status', hidden: true }),
      el('p', { class: 'muted small' }, `${data.model.label}. Development model: it often stops before finishing. Each step is checked, and refused steps are shown.`))));
  await choose(chat.ws);
}

// Results

// 'moldex-new-evidence-favours-looks' reads as 'Simulated evidence: favours looks'; a base case has none.
function variant(id) {
  const rest = id.split('-').slice(1).join(' ');
  return rest === 'base' ? 'No new evidence' : `Simulated evidence: ${rest.replace(/^new evidence /, '')}`;
}

const view = { pilot: null, open: null };

function outcomeCell(o, onOpen, selected) {
  return el('button', { class: `outcome${o.finished ? ' good' : ''}${selected ? ' selected' : ''}`, onclick: onOpen, 'aria-pressed': selected ? 'true' : 'false' },
    el('span', { class: 'outcome-stop' }, stopName(o.stop_reason)),
    el('span', { class: 'muted small' }, `${o.finished ? '' : `Stopped while ${stageName(o.stage_at_stop).toLowerCase()} · `}${o.calls} steps · ${o.refused} refused`));
}

function totalsTable(t, arms) {
  const row = (label, read, words) => el('tr', {}, el('th', { scope: 'row' }, label), el('td', { class: words ? '' : 'num' }, read(t.untrained)), el('td', { class: words ? '' : 'num' }, read(t.trained)));
  return el('table', { class: 'totals' },
    el('thead', {}, el('tr', {}, el('th', {}, ''), el('th', { class: 'num', scope: 'col' }, arms.untrained), el('th', { class: 'num', scope: 'col' }, arms.trained))),
    el('tbody', {},
      row('Finished', (x) => `${x.finished} of ${x.cases}`),
      row('Refused steps', (x) => String(x.refused)),
      row('Steps per run, mean', (x) => x.mean_calls.toFixed(1)),
      row('How runs ended', (x) => Object.entries(x.stop_reasons).map(([k, v]) => `${v} ${stopName(k).toLowerCase()}`).join(', '), true)));
}

async function renderResults() {
  const data = await api('/api/pilots');
  const root = $('results');
  if (!data.pilots.length) { root.replaceChildren(el('div', { class: 'card' }, el('p', {}, 'No paired pilot has finished yet.'))); return; }
  if (!data.pilots.some((p) => p.id === view.pilot)) { view.pilot = data.pilots[data.pilots.length - 1].id; view.open = null; }
  if (view.open && !['untrained', 'trained'].includes(view.open.arm)) view.open = null;
  const pilot = data.pilots.find((p) => p.id === view.pilot);
  const picker = data.pilots.length > 1 ? el('select', { 'aria-label': 'Pilot', onchange: (e) => { view.pilot = e.target.value; view.open = null; renderResults().catch(showError); } },
    data.pilots.map((p) => el('option', { value: p.id, selected: p.id === view.pilot }, p.label))) : null;
  const open = (arm, index) => { view.open = { arm, index }; history.replaceState(null, '', `#results/${pilot.id}/${arm}/${index}`); renderResults().catch(showError); };
  const isOpen = (arm, index) => view.open && view.open.arm === arm && view.open.index === index;
  const parts = [
    el('div', { class: 'card' },
      el('div', { class: 'row spread' }, el('h2', {}, pilot.label), picker),
      el('p', { class: 'lead' }, `The same ${pilot.totals.untrained.cases} cases, controller, prompt and settings for both models. The only difference is the trained adapter. ${pilot.note}`),
      el('p', { class: 'banner' }, data.banner),
      totalsTable(pilot.totals, pilot.arms)),
    el('div', { class: 'card' },
      el('h3', {}, 'Case by case'), el('p', { class: 'muted small' }, 'Open a run to read it step by step.'),
      el('div', { class: 'pairs-grid' },
        el('div', { class: 'pg-head' }, 'Case'), el('div', { class: 'pg-head' }, pilot.arms.untrained), el('div', { class: 'pg-head' }, pilot.arms.trained),
        pilot.cases.map((c) => [
          el('div', { class: 'pg-case' }, el('strong', {}, c.company), el('span', { class: 'muted small' }, variant(c.case))),
          outcomeCell(c.untrained, () => open('untrained', c.untrained.index), isOpen('untrained', c.untrained.index)),
          outcomeCell(c.trained, () => open('trained', c.trained.index), isOpen('trained', c.trained.index)),
        ]))),
  ];
  if (view.open) {
    const detail = await api(`/api/pilots/${pilot.id}/${view.open.arm}/${view.open.index}`);
    parts.push(...investigation(detail.record, pilot.arms[view.open.arm], `${pilot.id}/${view.open.arm}/${view.open.index}`));
  }
  root.replaceChildren(...parts);
}

// How it works: the controller as a diagram, drawn from /api/workflow

const GROUPS = {
  problem: ['Problem', 'Understand the question before looking for answers.'],
  theory: ['Theories and evidence', 'Rival causal explanations, each weighed against quoted evidence and challenged.'],
  experiment: ['Test and position', 'Design a test where the theories predict different results, or say why one is not worth it, then commit to a view.'],
  revision: ['New evidence, a what-if', 'Only in cases with a simulated result. It arrives after the position is stated, and the update loops into concluding. Without one, the agent goes from its position straight to concluding.'],
  conclusion: ['Conclusion', 'Recommend, with uncertainty and what would change the view.'],
};
const OPTIONAL = { challenge_reading: 'Only when the challenge found something not yet read.', new_evidence: 'Only in a what-if case.', update: 'Only in a what-if case.' };

// Tools that every later stage keeps open, so the agent can always look further before moving on.
function lookFurther(stages) {
  const later = stages.filter((s) => (s.group === 'experiment' || s.group === 'conclusion') && !s.optional);
  return later.length ? later[0].tools.filter((t) => later.every((s) => s.tools.includes(t))) : [];
}

function toolChip(name, descriptions, show, kind) {
  const button = el('button', { type: 'button', class: `tool${kind ? ` ${kind}` : ''}`, title: sentence(descriptions[name]), 'aria-expanded': 'false',
    onclick: () => show(name, button) }, name);
  return button;
}

async function renderHow() {
  const w = await workflowData();
  const root = $('how');
  const further = lookFurther(w.stages);
  const opens = {};
  w.stages.forEach((s) => s.tools.forEach((t) => { (opens[t] = opens[t] || []).push(s.stage); }));
  const groups = [];
  w.stages.forEach((s, i) => {
    const last = groups[groups.length - 1];
    if (last && last.group === s.group) last.stages.push([s, i]); else groups.push({ group: s.group, stages: [[s, i]] });
  });
  const box = (s, i) => {
    const own = s.tools.filter((t) => !further.includes(t) || !(s.group === 'experiment' || s.group === 'conclusion'));
    const kept = s.tools.filter((t) => !own.includes(t));
    const desc = el('p', { class: 'tool-desc', hidden: true, 'aria-live': 'polite' });
    let current = null;
    const show = (name, button) => {
      if (current) current.setAttribute('aria-expanded', 'false');
      if (current === button) { current = null; desc.hidden = true; return; }
      current = button; button.setAttribute('aria-expanded', 'true');
      desc.replaceChildren(el('code', {}, name), ` ${sentence(w.tools[name]) || 'No description.'}`);
      desc.hidden = false;
    };
    return el('li', { class: `stage-box${s.optional ? ' optional' : ''}` },
      el('div', { class: 'stage-head' }, el('span', { class: 'stage-n' }, String(i + 1)), el('strong', {}, stageName(s.stage)), el('code', { class: 'muted small' }, s.stage),
        s.optional ? chip('quiet', 'sometimes') : null),
      s.optional && OPTIONAL[s.stage] ? el('p', { class: 'muted small' }, OPTIONAL[s.stage]) : null,
      el('div', { class: 'tools' }, own.map((t) => toolChip(t, w.tools, show))),
      kept.length ? el('div', { class: 'tools kept' }, el('span', { class: 'muted small' }, '↺ still open:'), kept.map((t) => toolChip(t, w.tools, show, 'further'))) : null,
      desc);
  };
  const arrow = (s) => el('li', { class: 'arrow' }, el('span', { class: 'arrow-line', 'aria-hidden': 'true' }), el('span', { class: 'arrow-text' }, `moves on ${s.moves_on}`));
  const flow = el('div', { class: 'flow' }, groups.map((g) => {
    const [label, note] = GROUPS[g.group] || [g.group, ''];
    const optional = g.stages.every(([s]) => s.optional);
    return el('section', { class: `group g-${g.group}${optional ? ' optional' : ''}` },
      el('header', { class: 'group-head' }, el('h3', {}, label), el('p', { class: 'muted small' }, note)),
      el('ol', { class: 'flow-stages' }, g.stages.flatMap(([s, i]) => (s.stage === 'conclude' ? [box(s, i)] : [box(s, i), arrow(s)]))));
  }),
  el('div', { class: 'flow-end' }, '✓ Done: the investigation is finished'));
  const glossary = el('dl', { class: 'glossary' }, Object.entries(w.tools).map(([name, description]) => [
    el('dt', {}, el('code', {}, name)),
    el('dd', {}, sentence(description), el('span', { class: 'muted small' }, ` Open in: ${(opens[name] || []).map(shortName).join(', ') || 'none'}.`))]));
  root.replaceChildren(
    el('div', { class: 'card' },
      el('h2', {}, 'How the agent works'),
      el('p', { class: 'lead' }, 'A stage controller decides which tools are open at each step and what must happen before the investigation moves on. The model decides everything else: what to search, which theories to hold, what to test and what the evidence means. Every arm, trained or not, runs under this same controller.'),
      el('p', { class: 'muted small' }, 'Drawn from the controller’s own table, which a test checks against the code. Select a tool to see what it does. Dashed stages happen only in some cases.')),
    el('div', { class: 'card' }, flow),
    el('div', { class: 'card' }, el('h3', {}, 'Every tool'), further.length ? el('p', { class: 'muted small' }, `From the test onward, ${further.join(', ')} stay open in every stage, so the agent can keep investigating before it moves on.`) : null, glossary));
}

// Training

const SVG = 'http://www.w3.org/2000/svg';
function svg(tag, attrs, ...children) {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  for (const c of children.flat(Infinity)) if (c !== null && c !== undefined) node.append(c);
  return node;
}

// Per-step loss is noisy, so the line drawn is a trailing mean over 25 steps, over the faint raw line.
function smooth(points, window = 25) {
  let sum = 0;
  return points.map((p, i) => {
    sum += p.loss;
    if (i >= window) sum -= points[i - window].loss;
    return { step: p.step, loss: sum / Math.min(i + 1, window) };
  });
}

function lossChart(train, held, best) {
  const W = 680, H = 260, L = 44, R = 16, T = 16, B = 30;
  const maxX = Math.max(1, ...train.map((p) => p.step), ...held.map((p) => p.step));
  const maxY = Math.max(0.1, ...train.map((p) => p.loss), ...held.map((p) => p.eval_loss)) * 1.05;
  const x = (v) => L + (v / maxX) * (W - L - R), y = (v) => T + (1 - v / maxY) * (H - T - B);
  const path = (pts, key) => pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.step).toFixed(1)},${y(p[key]).toFixed(1)}`).join('');
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * maxY);
  return svg('svg', { viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img', 'aria-label': 'Training loss and held-out loss by step' },
    ticks.map((v) => svg('g', {}, svg('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: 'var(--grid)', 'stroke-width': 1 }),
      svg('text', { x: L - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'axis' }, v.toFixed(2)))),
    svg('text', { x: L, y: H - 8, class: 'axis' }, 'step 0'),
    svg('text', { x: W - R, y: H - 8, 'text-anchor': 'end', class: 'axis' }, `step ${maxX}`),
    train.length ? svg('path', { d: path(train, 'loss'), fill: 'none', stroke: 'var(--series-1)', 'stroke-width': 1, opacity: 0.25 }) : null,
    train.length ? svg('path', { d: path(smooth(train), 'loss'), fill: 'none', stroke: 'var(--series-1)', 'stroke-width': 2 }) : null,
    held.length ? svg('path', { d: path(held, 'eval_loss'), fill: 'none', stroke: 'var(--series-2)', 'stroke-width': 2 }) : null,
    held.map((p) => svg('circle', { cx: x(p.step), cy: y(p.eval_loss), r: 8, fill: 'transparent' }, svg('title', {}, `Step ${p.step}: held-out loss ${p.eval_loss.toFixed(3)}`))),
    held.map((p) => svg('circle', { cx: x(p.step), cy: y(p.eval_loss), r: 3, fill: 'var(--series-2)', 'pointer-events': 'none' })),
    best ? svg('g', { 'pointer-events': 'none' },
      svg('line', { x1: x(best.step), x2: x(best.step), y1: T, y2: H - B, stroke: 'var(--ink-2)', 'stroke-width': 1, 'stroke-dasharray': '3 3' }),
      svg('circle', { cx: x(best.step), cy: y(best.eval_loss), r: 5, fill: 'var(--series-2)', stroke: 'var(--surface)', 'stroke-width': 2 }),
      svg('text', { x: x(best.step) + 6, y: T + 10, class: 'axis' }, `best, step ${best.step}`)) : null);
}

let trainingTimer = null;

async function renderTraining() {
  const live = await api('/api/training/live');
  const root = $('training');
  clearTimeout(trainingTimer);
  if (!live.state) {
    root.replaceChildren(el('div', { class: 'card' }, el('h2', {}, 'Training'), el('p', { class: 'lead' }, 'No training run is being followed. Start tooling/training_feed.py with a job id.')));
    return;
  }
  const train = live.train || [], held = live.held_out || [];
  const best = held.reduce((a, p) => (!a || p.eval_loss < a.eval_loss ? p : a), null);
  const last = train[train.length - 1];
  const pg = live.progress;
  const running = live.state.startsWith('RUNNING');
  const key = (cls, label) => el('span', { class: 'key' }, el('span', { class: `swatch ${cls}` }), label);
  root.replaceChildren(el('div', { class: 'card' },
    el('div', { class: 'row spread' }, el('h2', {}, `Training job ${live.job || ''}`.trim()),
      chip(running ? 'warn' : live.state.startsWith('COMPLETED') ? 'good' : 'bad', running ? 'Running' : live.state.charAt(0) + live.state.slice(1).toLowerCase())),
    el('p', { class: 'lead' }, 'Held-out loss is measured on Hellberg, a company the model never trains on: when it stops falling while training loss keeps falling, the model is fitting its training cases rather than learning something that carries over. Loss says how well it predicts the teacher, not how well it investigates.'),
    pg && running ? el('div', { class: 'progress', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': pg.total, 'aria-valuenow': pg.step }, el('div', { style: `width:${(100 * pg.step / pg.total).toFixed(1)}%` })) : null,
    el('div', { class: 'row' }, key('s1', 'Training loss, mean of 25 steps'), key('s2', 'Held-out loss')),
    lossChart(train, held, best),
    el('dl', { class: 'stats' },
      el('div', {}, el('dt', {}, 'Step'), el('dd', {}, pg ? `${pg.step} of ${pg.total}` : '–')),
      el('div', {}, el('dt', {}, 'Training loss'), el('dd', {}, last ? last.loss.toFixed(3) : '–')),
      el('div', {}, el('dt', {}, 'Best held-out loss'), el('dd', {}, best ? `${best.eval_loss.toFixed(3)} at step ${best.step}` : '–')),
      el('div', {}, el('dt', {}, running ? 'Time left' : 'Updated'), el('dd', {}, running && pg ? pg.remaining : text(live.updated)))),
    live.notes && live.notes.length ? el('p', { class: 'muted small' }, live.notes.join(' · ')) : null));
  if (running && !root.hidden) trainingTimer = setTimeout(() => renderTraining().catch(showError), 30000);
}

// Tabs: click, or arrow keys between them, as the ARIA tabs pattern expects.

// The math: the paper's model, an illustrative calculator, how the agent carries it out, and how we assess it

const MML = 'http://www.w3.org/1998/Math/MathML';
function mm(tag, attrs, ...children) {
  const node = document.createElementNS(MML, tag);
  for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, value);
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(typeof child === 'string' ? document.createTextNode(child) : child);
  }
  return node;
}
// Tiny builders: identifiers, operators, numbers, subscripts, rows. Every symbol is set as text, never as markup.
const mi = (x) => mm('mi', {}, x);
const mo = (x) => mm('mo', {}, x);
const mn = (x) => mm('mn', {}, x);
const row = (...xs) => mm('mrow', {}, xs);
const sub = (base, s) => mm('msub', {}, typeof base === 'string' ? mi(base) : base, typeof s === 'string' ? mm('mtext', {}, s) : s);
const th = (s) => sub('θ', s);
const P = (...xs) => row(mi('P'), mo('('), ...xs, mo(')'));
const tilde = (x) => mm('mover', { accent: 'true' }, mi(x), mo('~'));
const prime = (x) => mm('msup', {}, typeof x === 'string' ? mi(x) : x, mo('′'));
function equation(number, ...content) {
  return el('div', { class: 'eq' }, el('div', { class: 'eq-body', tabindex: '0' }, mm('math', { display: 'block' }, row(...content))), number ? el('span', { class: 'eq-n muted' }, `(${number})`) : null);
}

function networkDiagram() {
  const box = (x, label, sub2) => [svg('rect', { x, y: 8, width: 150, height: 54, rx: 10, class: 'net-node' }),
    svg('text', { x: x + 75, y: 32, 'text-anchor': 'middle', class: 'net-label' }, label),
    svg('text', { x: x + 75, y: 50, 'text-anchor': 'middle', class: 'net-sub' }, sub2)];
  return svg('svg', { viewBox: '0 0 400 70', class: 'net', role: 'img', 'aria-label': 'Bayesian network: fashion design Xf causes demand Xd' },
    svg('defs', {}, svg('marker', { id: 'net-arrow', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto' }, svg('path', { d: 'M0,0 L10,5 L0,10 z', class: 'net-head' }))),
    box(10, 'Xf: fashion design', 'Y (yes) or N (no)'), box(240, 'Xd: demand', 'H (high) or L (low)'),
    svg('line', { x1: 160, y1: 35, x2: 236, y2: 35, class: 'net-edge', 'marker-end': 'url(#net-arrow)' }));
}

// Numerical posterior for θHY under the theory: θHY ~ Uniform(θHN, 1), k of n buy. Log scale so large n cannot underflow.
function updateNumbers({ omega, thetaY, thetaHN, n, k }) {
  const loglik = (t) => (k ? k * Math.log(t) : 0) + (n - k ? (n - k) * Math.log(1 - t) : 0);
  const steps = 2000, a = thetaHN, b = 1 - 1e-9, h = (b - a) / steps;
  const xs = Array.from({ length: steps + 1 }, (_, i) => a + i * h);
  const ls = xs.map(loglik);
  const top = Math.max(...ls);
  const w = (i) => (i === 0 || i === steps ? 1 : i % 2 ? 4 : 2);
  let mass = 0, first = 0;
  xs.forEach((x, i) => { const f = Math.exp(ls[i] - top) * w(i); mass += f; first += x * f; });
  mass *= h / 3; first *= h / 3;
  const meanHY = first / mass;
  // Marginal likelihood: the prior density is 1 / (1 − θHN) on (θHN, 1); under the null θHY equals θHN exactly.
  const logTheory = top + Math.log(mass) - Math.log(1 - thetaHN);
  const logNull = loglik(thetaHN);
  const bf = Math.exp(logTheory - logNull);
  const omega2 = Number.isFinite(bf) ? (omega * bf) / (omega * bf + 1 - omega) : 1;
  const vTheory = thetaHN + thetaY * ((thetaHN + 1) / 2 - thetaHN);
  const vTheory2 = thetaHN + thetaY * (meanHY - thetaHN);
  const vNull = thetaHN;
  return { meanHY, bf, omega2, vTheory, vTheory2, vNull, v: omega * vTheory + (1 - omega) * vNull, v2: omega2 * vTheory2 + (1 - omega2) * vNull };
}

function calculator() {
  const state = { omega: 0.5, thetaY: 0.8, thetaHN: 0.5, n: 0, k: 0 };
  const out = el('div', { class: 'calc-out', 'aria-live': 'polite' });
  const fmt = (x, d = 3) => (Number.isFinite(x) ? x.toFixed(d) : '∞');
  const slider = (key, label, min, max, step) => {
    const value = el('output', { class: 'num' }, String(state[key]));
    const input = el('input', { type: 'range', min, max, step, value: state[key], 'aria-label': label, oninput: (e) => {
      state[key] = Number(e.target.value);
      if (key === 'n') { kInput.max = state.n; if (state.k > state.n) { state.k = state.n; kInput.value = state.n; } }
      value.textContent = String(state[key]); draw();
    } });
    if (key === 'k') kInput = input;
    return el('label', { class: 'calc-row' }, el('span', {}, label), input, value);
  };
  let kInput = null;
  const rows = [slider('omega', 'ω, belief that the theory is right', 0.05, 0.95, 0.05), slider('thetaY', 'θY, chance the fashion design works', 0, 1, 0.05),
    slider('thetaHN', 'θHN, demand without fashion design', 0.05, 0.9, 0.05), slider('n', 'n, customers shown the fashion design', 0, 60, 1), slider('k', 'k, of them who buy', 0, 60, 1)];
  kInput.max = state.n;
  const line = (label, a, b) => el('tr', {}, el('th', { scope: 'row' }, label), el('td', { class: 'num' }, a), el('td', { class: 'num' }, b));
  function draw() {
    const r = updateNumbers(state);
    out.replaceChildren(el('table', { class: 'totals' },
      el('thead', {}, el('tr', {}, el('th', {}, ''), el('th', { class: 'num', scope: 'col' }, 'Before'), el('th', { class: 'num', scope: 'col' }, 'After the experiment'))),
      el('tbody', {},
        line('Expected θHY under the theory', fmt((state.thetaHN + 1) / 2), fmt(r.meanHY)),
        line('VΘ, the theory’s P(H)', fmt(r.vTheory), fmt(r.vTheory2)),
        line('VΘ̃, the null’s P(H)', fmt(r.vNull), fmt(r.vNull)),
        line('ω, belief in the theory', fmt(state.omega, 2), fmt(r.omega2)),
        line('V = ωVΘ + (1 − ω)VΘ̃', fmt(r.v), fmt(r.v2)))),
      el('p', { class: 'muted small' }, state.n ? `Bayes factor, theory against null: ${fmt(r.bf, 2)}. Above 1 the observations favour the theory, below 1 the null.` : 'With no customers observed nothing updates. With the defaults this reproduces the paper: VΘ = 0.7, VΘ̃ = 0.5, V = ω·0.7 + (1 − ω)·0.5.'));
  }
  draw();
  return el('div', { class: 'calc' }, el('div', { class: 'calc-in' }, rows), out);
}

const MAPPING = [
  ['Attributes and state space X (eq. 1)', 'frame', 'frame_problem', 'States the objective, the constraints and the alternatives, which fixes what the investigation is about.'],
  ['A causal link and its restriction, θHY > θHN', 'theories', 'add_theory', 'Each theory names a cause, why behaviour changes, how value is captured, its assumptions and its predictions.'],
  ['Null hypothesis and an alternative theory Q', 'theories', 'add_theory', 'At least two rival theories with different causes.'],
  ['Questioning the theory, ω < 1', 'challenge', 'challenge_theory', 'Searches for what could prove the favoured theory wrong, then reads what it found.'],
  ['Pseudo-observations behind μ(θ)', 'assessment', 'assess_evidence', 'Says how a source bears on a theory, quoting its exact words, and what it cannot establish.'],
  ['An experiment that discriminates', 'test', 'propose_test', 'A test where the theories predict different results, with a decision rule that has a threshold.'],
  ['Committing without experimenting', 'test', 'decline_test', 'Says why more information is not worth its cost, as when V or Q already dominates.'],
  ['ω and V before an experiment', 'position', 'state_position', 'Names the favoured theory and rates each theory on a five-point scale.'],
  ['V to V′ (eq. 7)', 'update', 'revise_theory', 'After a simulated what-if: keeps, revises or rejects the theory it bears on, citing it.'],
  ['Commit', 'conclude', 'finish', 'Recommends, with the favoured theory, the uncertainty, what would change it and the final beliefs.'],
];

function verdictChip(v) {
  return v === 'consistent' ? chip('good', '✓ consistent') : v === 'inconsistent' ? chip('bad', '✕ inconsistent') : chip('quiet', v);
}

async function renderMath() {
  const root = $('math');
  const [w, b] = await Promise.all([workflowData(), api('/api/beliefs')]);
  const known = new Set(w.stages.flatMap((s) => s.tools));
  const pair = (a, c) => row(mo('('), mi(a), mo(','), mi(c), mo(')'));  // fresh nodes each time: a DOM node can sit in one place only
  const paper = el('div', { class: 'card' },
    el('h2', {}, 'The math in the paper'),
    el('p', { class: 'lead' }, 'Camuffo, Gambardella and Pignataro (2024), “Theory-driven strategic management decisions”, Strategy Science 9(4): 382–396, sections 3 and 4. Their example is Luxottica deciding whether eyeglasses could be a fashion product.'),
    el('h3', {}, '1. Attributes define a state space'),
    el('p', {}, 'An attribute is a question whose answer is uncertain: can Luxottica design fashion eyewear (Y or N), and will demand be high or low (H or L)? Together they make four states.'),
    equation(1, mi('X'), mo('='), sub('X', 'f'), mo('×'), sub('X', 'd'), mo('='), mo('{'), pair('H', 'Y'), mo(','), pair('H', 'N'), mo(','), pair('L', 'Y'), mo(','), pair('L', 'N'), mo('}')),
    el('p', {}, 'The decision maker cares about high demand, so the target is the probability of H:'),
    equation(2, P(mi('H')), mo('='), P(mi('H'), mo(','), mi('Y')), mo('+'), P(mi('H'), mo(','), mi('N'))),
    el('h3', {}, '2. A theory is a Bayesian network with a restriction'),
    el('p', {}, 'The theory says fashion design causes demand. As a Bayesian network that is one arrow, and the claim is an inequality on its conditional probabilities.'),
    networkDiagram(),
    equation(null, P(mi('H'), mo('|'), mi('Y')), mo('>'), P(mi('H'), mo('|'), mi('N')), mspace(), mo('⇔'), mspace(), th('HY'), mo('>'), th('HN')),
    equation(null, mi('Θ'), mo('='), mo('{'), mi('θ'), mo(':'), th('HY'), mo('>'), th('HN'), mo('}')),
    el('p', {}, 'Writing θY for P(Y), the probability of high demand for one set of parameters is:'),
    equation(3, mi('E'), mi('P'), row(mo('('), mi('H'), mo(')')), mo('≡'), mi('v'), row(mo('('), mi('θ'), mo(')')), mo('='), th('HY'), th('Y'), mo('+'), th('HN'), row(mo('('), mn('1'), mo('−'), th('Y'), mo(')')), mo('='), th('HN'), mo('+'), th('Y'), row(mo('('), th('HY'), mo('−'), th('HN'), mo(')'))),
    el('h3', {}, '3. Beliefs about the parameters, under the theory and under the null'),
    el('p', {}, 'The parameters are not known, so the decision maker holds a distribution μ over them. The theory allows only parameters in Θ; the null hypothesis, here θHY = θHN, allows only Θ̃.'),
    equation(4, sub('V', 'Θ'), mo('≡'), sub(mi('E'), row(mi('θ'), mo('∈'), mi('Θ'))), mi('v'), row(mo('('), mi('θ'), mo(')')), mo('='), mm('msub', {}, mo('∫'), row(mi('θ'), mo('∈'), mi('Θ'))), mi('v'), row(mo('('), mi('θ'), mo(')')), sub('μ', 'Θ'), row(mo('('), mi('θ'), mo(')')), mi('d'), mi('θ')),
    equation(5, sub('V', tilde('Θ')), mo('≡'), mm('msub', {}, mo('∫'), row(mi('θ'), mo('∈'), tilde('Θ'))), mi('v'), row(mo('('), mi('θ'), mo(')')), sub('μ', tilde('Θ')), row(mo('('), mi('θ'), mo(')')), mi('d'), mi('θ')),
    el('p', {}, 'The decision maker is not sure the theory is right, and ω is the prior that it is. The expected value of the theory weighs the two:'),
    equation(6, mi('V'), mo('='), mi('ω'), sub('V', 'Θ'), mo('+'), row(mo('('), mn('1'), mo('−'), mi('ω'), mo(')')), sub('V', tilde('Θ'))),
    el('div', { class: 'worked' },
      el('strong', {}, 'The paper’s numbers'),
      el('p', {}, 'θHN = 0.5 and θY = 0.8, each with probability 1, and θHY uniform. Under the theory θHY is uniform on (0.5, 1), so its expected value is 0.75:'),
      equation(null, sub('V', 'Θ'), mo('='), mn('0.5'), mo('+'), row(mo('('), mn('0.75'), mo('−'), mn('0.5'), mo(')')), mo('·'), mn('0.8'), mo('='), mn('0.7')),
      equation(null, sub('V', tilde('Θ')), mo('='), mn('0.5'), mspace(), mo(','), mspace(), mi('V'), mo('='), mi('ω'), mo('·'), mn('0.7'), mo('+'), row(mo('('), mn('1'), mo('−'), mi('ω'), mo(')')), mo('·'), mn('0.5')),
      el('p', { class: 'muted small' }, 'Without the restriction θHY would average 0.5 and V would be 0.5. The theory raises belief in high demand by ruling parameter values out.')),
    el('h3', {}, '4. Experiments update the theory'),
    el('p', {}, 'An experiment updates μ, and so VΘ and VΘ̃. The prior ω on the theory changes only when the evidence moves μ past a threshold, ‖μ′ − μ‖ > μ*: a small surprise adjusts the parameters, a large one shakes belief in the theory itself.'),
    equation(7, prime('V'), mo('='), prime('ω'), mm('msubsup', {}, mi('V'), mi('Θ'), mo('′')), mo('+'), row(mo('('), mn('1'), mo('−'), prime('ω'), mo(')')), mm('msubsup', {}, mi('V'), tilde('Θ'), mo('′'))),
    el('p', {}, 'An alternative theory, with its own attributes and causal links, has its own value Q, built the same way. The decision maker can commit to either theory or experiment on either. With costly experiments, committing is right once V is far enough above or below Q; in between it pays to experiment (their Appendix A, extending Moscarini and Smith 2001). Experiments are assumed Bayes plausible: before running one there is no reason to expect it to move the value either way.'),
    equation(null, mi('E'), prime('V'), mo('='), mi('V'), mspace(), mo(','), mspace(), mi('E'), prime('ω'), mo('='), mi('ω')));
  const calc = el('div', { class: 'card' },
    el('h2', {}, 'Try the update'),
    el('p', { class: 'note' }, 'An illustration of the paper’s framework with standard Bayesian updating, not something the agent computes.'),
    el('p', { class: 'muted small' }, 'Observe n customers shown the fashion design; k buy. Under the theory θHY is uniform on (θHN, 1); under the null θHY = θHN. The calculator updates μ and ω fully by Bayes’ rule. The paper changes ω only past a threshold, so this overstates how often ω moves.'),
    calculator());
  const mapping = el('div', { class: 'card' },
    el('h2', {}, 'How the agent carries this out'),
    el('p', { class: 'lead' }, 'The agent follows the paper’s steps in words, with tools and evidence, but it does not compute probabilities.'),
    el('table', { class: 'totals mapping' },
      el('thead', {}, el('tr', {}, el('th', { scope: 'col' }, 'In the paper'), el('th', { scope: 'col' }, 'Stage and tool'), el('th', { scope: 'col' }, 'What the agent does'))),
      el('tbody', {}, MAPPING.filter(([, , tool]) => known.has(tool)).map(([concept, stage, tool, does]) =>
        el('tr', {}, el('th', { scope: 'row' }, concept), el('td', {}, el('span', { class: 'muted small' }, `${stageName(stage)} · `), el('code', { class: 'tool-name' }, tool)), el('td', {}, does))))));
  const reached = b.arms.map((a) => ({ ...a, reached: a.cases.filter((c) => c.moves.length && c.moves.some((m) => m.before)) }));
  const assess = el('div', { class: 'card' },
    el('h2', {}, 'How we assess the model'),
    el('p', {}, 'The agent does not compute a Bayesian update, and nor does the harness. Decided on November 2, 2026 with Codex: a computed update would need an invented network and invented numbers, and assumed ratios could create the very revision we want to measure.'),
    el('p', {}, 'Instead, in cases with a simulated what-if, the model rates each theory on a five-point scale (very unlikely, unlikely, uncertain, likely, very likely) when it states its position, and again after the what-if. The evaluation protocol scores whether its response targets the affected theory, cites the what-if, explains its limits, and moves in the direction the packet was written to push. A weak result may rationally change nothing, scripted policies that always keep or always change must not be rewarded, and blind judges score the full rubric. The scale is a within-run signal, not a calibrated probability.'),
    el('h3', {}, 'What the pilots show so far'),
    el('p', { class: 'muted small' }, 'Undermining evidence should not raise the affected theory’s belief, supporting evidence should not lower it, irrelevant evidence should leave it unchanged. A direction check only.'),
    reached.map((a) => el('div', { class: 'belief-arm' },
      el('h4', {}, `${a.pilot_label}, ${a.arm_label}: `, el('span', { class: 'muted' }, `${a.reached.length} of ${a.cases.length} what-if cases reached a stated position with the what-if delivered`)),
      a.reached.length ? el('table', { class: 'totals' },
        el('thead', {}, el('tr', {}, ['Case', 'What-if', 'Theory', 'Before', 'After', 'Direction'].map((h) => el('th', { scope: 'col' }, h)))),
        el('tbody', {}, a.reached.flatMap((c) => c.moves.map((m) => el('tr', {}, el('td', {}, `${sentence(c.case.split('-')[0])} · ${variant(c.case).replace('Simulated evidence: ', '')}`), el('td', {}, c.direction), el('td', {}, m.theory), el('td', {}, m.before || '—'), el('td', {}, m.after || '—'), el('td', {}, verdictChip(m.verdict)))))))
        : null)),
    el('p', { class: 'note' }, 'Very few pilot runs reach the what-if, so these rows say almost nothing yet. The measure becomes informative once runs routinely reach that stage.'));
  root.replaceChildren(paper, calc, mapping, assess);
}

function mspace() { return mm('mspace', { width: '0.6em' }); }

const RENDER = { try: renderTry, how: renderHow, math: renderMath, results: renderResults, training: renderTraining };
const tabs = [...document.querySelectorAll('[role="tab"]')];

function select(tab, focus) {
  for (const button of tabs) {
    const on = button === tab;
    button.setAttribute('aria-selected', String(on));
    button.tabIndex = on ? 0 : -1;
    $(button.getAttribute('aria-controls')).hidden = !on;
  }
  if (focus) tab.focus();
  document.body.classList.toggle('chat-on', tab.getAttribute('aria-controls') === 'try');
  if (!location.hash.startsWith(`#${tab.getAttribute('aria-controls')}`)) history.replaceState(null, '', `#${tab.getAttribute('aria-controls')}`);
  RENDER[tab.getAttribute('aria-controls')]().catch(showError);
}

tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => select(tab));
  tab.addEventListener('keydown', (event) => {
    const move = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (move) { event.preventDefault(); select(tabs[(index + move + tabs.length) % tabs.length], true); }
    if (event.key === 'Home') { event.preventDefault(); select(tabs[0], true); }
    if (event.key === 'End') { event.preventDefault(); select(tabs[tabs.length - 1], true); }
  });
});

// The signed-in user, and signing out
api('/api/me').then((me) => { $('account-name').textContent = me.user; }).catch(() => {});
$('sign-out').addEventListener('click', async () => {
  try { await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' }); } finally { location.replace('/login'); }
});

// A link can open a tab, or one run of a pilot: #results/pilot1/trained/3
const [first, pilotId, arm, index] = location.hash.slice(1).split('/');
if (first === 'results' && pilotId) { view.pilot = pilotId; if (arm) view.open = { arm, index: Number(index) }; }
// The workflow colours the tree by group, so it loads first; the page still works if it fails.
workflowData().catch(() => {}).finally(() => select(tabs.find((t) => t.getAttribute('aria-controls') === first) || tabs[0]));
