"""The Track 3 metrics by name, per company and per test: task success (finished investigations), tool-call accuracy
(accepted calls over all calls) and calls per run, for the base model, version 1 and the final system, from the saved
run reports. Latency exists only as the version 1 aggregate in reports/cost/roi.json (66 s per investigation), so it
is reported once, not per company.

Usage: python scripts/release/track3_metrics.py  -> reports/track3_metrics.json, and the markdown tables on stdout.
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARMS = {
    'final': {'Base model': 'reports/judge/final/final_test_base_base.json',
              'Version 1': 'reports/judge/final/final_test_trained_adapter.json',
              'Final system': 'experiments/grounded/final/D.json'},
    'test2': {'Base model': 'reports/judge/test2/test2_base_base.json',
              'Version 1': 'reports/judge/test2/test2_trained_adapter.json',
              'Final system': 'experiments/grounded/test2/D.json'},
}
NAMES = {'final': 'First test', 'test2': 'Second test'}


def stats(records: list[dict]) -> dict:
    n = len(records)
    finished = sum(r['stop_reason'] == 'finished' for r in records)
    calls = sum(len(r['calls']) for r in records)
    accepted = sum(sum(1 for c in r['calls'] if c['accepted']) for r in records)
    return {'runs': n, 'finished': finished, 'task_success': finished / n, 'calls': calls, 'accepted': accepted,
            'tool_call_accuracy': accepted / calls if calls else None, 'calls_per_run': calls / n}


def main() -> None:
    out: dict = {'latency_seconds_per_investigation': {'Version 1': 66, 'source': 'reports/cost/roi.json; the other arms were not timed'}}
    lines: list[str] = []
    for split, arms in ARMS.items():
        out[split] = {}
        by_company: dict[str, dict[str, dict]] = defaultdict(dict)
        for arm, path in arms.items():
            records = json.load(open(ROOT / path))['records']
            out[split][arm] = {'all': stats(records), 'by_company': {}}
            groups: dict[str, list] = defaultdict(list)
            for r in records:
                groups[r['company']].append(r)
            for company, recs in sorted(groups.items()):
                s = stats(recs)
                out[split][arm]['by_company'][company] = s
                by_company[company][arm] = s
        arm_names = list(arms)
        lines.append(f'\n**{NAMES[split]}** (task success = finished investigations; tool-call accuracy = accepted calls over all calls)\n')
        lines.append('| Company | ' + ' | '.join(f'{a}: task success' for a in arm_names) + ' | ' + ' | '.join(f'{a}: tool-call accuracy' for a in arm_names) + ' |')
        lines.append('|---|' + '---|' * (2 * len(arm_names)))
        for company, per in by_company.items():
            lines.append(f'| {company} | ' + ' | '.join(f"{per[a]['finished']} of {per[a]['runs']}" for a in arm_names) + ' | '
                         + ' | '.join(f"{100 * per[a]['tool_call_accuracy']:.0f}%" for a in arm_names) + ' |')
        tot = {a: out[split][a]['all'] for a in arm_names}
        lines.append('| **All** | ' + ' | '.join(f"**{tot[a]['finished']} of {tot[a]['runs']}**" for a in arm_names) + ' | '
                     + ' | '.join(f"**{100 * tot[a]['tool_call_accuracy']:.0f}%**" for a in arm_names) + ' |')
    (ROOT / 'reports/track3_metrics.json').write_text(json.dumps(out, indent=1))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
