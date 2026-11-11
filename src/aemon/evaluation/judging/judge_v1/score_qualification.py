"""Qualification of a judge for evaluation scoring: the rule in docs/DECISIONS.md, 2026-11-06. Evaluation only.

Reads one backend's qualification results (judge_backends.run_packets output on qualification_blind.jsonl). An output
is valid for scoring if its response parses and its dimension block passes the dimension checks; the screening fields
are ignored. Invalid outputs are retried once with --retry (the retry goes to <results>_retry1, the original is kept).
After the retry at most 4 of 40 may be invalid, and the sound version of each of the 20 clusters must score strictly
higher than the flawed one in at least 17. The frozen config_v1 screener rule is not touched.

The receipt is bound to the backend configuration the results were produced under: every result must carry the digest of
--manifest (default: the current backends_v1.json), and the receipt records that digest and the digest of this judge's
own section, which run_campaign.py checks against the configuration it runs with.

Usage: python src/aemon/evaluation/judging/judge_v1/score_qualification.py --backend claude --results results/claude [--retry] [--manifest M] --output out.json
"""

import argparse
import json
import statistics
from pathlib import Path

import judge
import judge_backends as b

ROOT = Path(__file__).resolve().parent
MAX_INVALID, MIN_ORDERED = 4, 17


def scoring_validity(response_text, packet):
    """The judgment's dimension scores if they are valid for scoring, else the reason they are not."""
    try:
        v = json.loads(response_text)
    except (TypeError, ValueError):
        return None, 'response is not JSON'
    if not isinstance(v, dict) or v.get('packet_id') != packet['packet_id']:
        return None, 'packet identity mismatch'
    dims = v.get('dimensions')
    names = judge.config()['dimensions']
    if not isinstance(dims, dict) or set(dims) != set(names):
        return None, 'dimension set differs'
    known = {e['id'] for e in packet['events']} | {s['id'] for s in packet.get('sources', [])}
    applicable = packet.get('applicable_dimensions')
    for d, x in dims.items():
        if not isinstance(x, dict) or x.get('status') not in ('scored', 'not_reached', 'not_applicable'):
            return None, f'{d}: invalid status'
        if applicable is not None and ((d not in applicable) != (x['status'] == 'not_applicable')):
            return None, f'{d}: applicability mismatch'
        if x['status'] == 'scored' and (type(x.get('score')) is not int or not 0 <= x['score'] <= 3):
            return None, f'{d}: invalid score'
        if x['status'] != 'scored' and x.get('score') is not None:
            return None, f'{d}: unscored dimension has a score'
        if not isinstance(x.get('event_ids'), list) or not isinstance(x.get('reason'), str) or not set(x['event_ids']) <= known:
            return None, f'{d}: missing or unknown evidence'
    return dims, 'valid'


def packet_score(dims):
    vals = [float(x['score']) if x['status'] == 'scored' else 0.0 for x in dims.values() if x['status'] != 'not_applicable']
    return statistics.mean(vals) if vals else None


def read_results(folder, packets):
    out = {}
    for p in packets:
        r = Path(folder) / p['packet_id'] / 'result.json'
        if not r.exists():
            out[p['packet_id']] = (None, 'no result')
            continue
        res = json.loads(r.read_text())
        text = (res.get('response') or {}).get('text')
        out[p['packet_id']] = scoring_validity(text, p) if text is not None else (None, 'no response: ' + str(res.get('error'))[:200])
    return out


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--backend', choices=('claude', 'codex', 'codexsol', 'claudecode'), required=True)
    a.add_argument('--results', required=True)
    a.add_argument('--retry', action='store_true', help='retry invalid outputs once, into <results>_retry1')
    a.add_argument('--run-cap', type=float, default=8.0)
    a.add_argument('--manifest', help='the backends file the results were produced under (default: the current one)')
    a.add_argument('--output', required=True)
    args = a.parse_args()
    m = json.loads(Path(args.manifest).read_text()) if args.manifest else b.manifest()
    packets = judge.read(ROOT / 'qualification_blind.jsonl')
    by_id = {p['packet_id']: p for p in packets}
    key = {k['packet_id']: k for k in judge.read(ROOT / 'qualification_key_v1.jsonl')}
    first = read_results(args.results, packets)
    retry_dir = Path(str(Path(args.results)) + '_retry1')
    invalid = [pid for pid, (d, _) in first.items() if d is None]
    if args.retry and invalid:
        retry_packets = retry_dir.parent / (retry_dir.name + '_packets.jsonl')
        if not retry_packets.exists():
            retry_packets.write_text(''.join(json.dumps(by_id[pid]) + '\n' for pid in invalid))
        b.run_packets(args.backend, retry_packets, retry_dir, str(ROOT.parents[4]), run_cap=args.run_cap, workers=2)
    identities = set()
    for folder in [Path(args.results)] + ([retry_dir] if retry_dir.exists() else []):
        for r in folder.glob('*/result.json'):
            identities.add(json.loads(r.read_text()).get('instrument_sha256'))
    if identities != {b.digest(m)}:
        raise SystemExit(f'results were not all produced under this backend configuration: {sorted(map(str, identities))}')
    final, attempts = {}, {}
    second = read_results(retry_dir, [by_id[pid] for pid in invalid]) if retry_dir.exists() else {}
    for pid in by_id:
        dims, why = first[pid]
        attempts[pid] = {'first': why}
        if dims is None and pid in second:
            dims, why2 = second[pid]
            attempts[pid]['retry'] = why2
        final[pid] = dims
    clusters = {}
    for pid, k in key.items():
        clusters.setdefault(k['cluster_id'], {})['sound' if k['expected_suitable'] else 'flawed'] = pid
    ordered, cluster_rows = 0, []
    for cid, pair in sorted(clusters.items()):
        s, f = final.get(pair.get('sound')), final.get(pair.get('flawed'))
        ss, fs = (packet_score(s) if s else None), (packet_score(f) if f else None)
        ok = ss is not None and fs is not None and ss > fs
        ordered += ok
        cluster_rows.append({'cluster': cid, 'sound': ss, 'flawed': fs, 'ordered': ok})
    n_invalid = sum(d is None for d in final.values())
    passed = n_invalid <= MAX_INVALID and ordered >= MIN_ORDERED and len(clusters) == 20
    result = {
        'judge': args.backend,
        'rule': 'docs/DECISIONS.md 2026-11-06: evaluation-scoring qualification',
        'status': 'qualified_for_scoring' if passed else 'not_qualified_for_scoring',
        'clusters': len(clusters),
        'sound_scores_higher': ordered,
        'needed': MIN_ORDERED,
        'invalid_after_retry': n_invalid,
        'max_invalid': MAX_INVALID,
        'retried': len(invalid) if args.retry else 0,
        'manifest_version': m.get('version'),
        'instrument_sha256': b.digest(m),
        'judge_config_sha256': b.digest(m['judges'][args.backend]),
        'judge_config': m['judges'][args.backend],
        'prompt_sha256': judge.config()['artifact_sha256']['judge_prompt_v1.txt'],
        'packets_sha256': judge.config()['artifact_sha256']['qualification_blind.jsonl'],
        'per_cluster': cluster_rows,
        'attempts': attempts,
        'evaluation_only': True,
    }
    Path(args.output).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ('judge', 'status', 'sound_scores_higher', 'needed', 'invalid_after_retry', 'retried')}))


if __name__ == '__main__':
    main()
