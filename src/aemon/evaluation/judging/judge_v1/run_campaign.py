"""Judge an evaluation campaign with one backend: blinded packets in, one result per packet out. Evaluation only.

Packets come from aemon.evaluation.judging.packets; their key stays apart and is never read here. A judge runs
only if its qualification result in --qualification says qualified, unless --unqualified-diagnostic is given, in which
case the output folder is marked as a diagnostic that cannot support a quality claim. Resuming reuses finished packets
and refuses a changed instrument, exactly as in judge_backends.run_packets (written by Codex). Judge output never
selects or filters training data.

Usage: python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claude --packets P.jsonl --output results/dev/claude \
           --qualification reports/judge/claude_score_qualification.json [--run-cap 12] [--unqualified-diagnostic]
"""

import argparse
import json
from pathlib import Path

import judge_backends as b

REPO = Path(__file__).resolve().parents[5]  # the repository root


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--backend', choices=('claude', 'codex', 'codexsol', 'claudecode'), required=True)
    p.add_argument('--packets', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--qualification', required=True)
    p.add_argument('--run-cap', type=float, default=12.0, help='USD cap for this run (Claude); the ledger cap still applies')
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--unqualified-diagnostic', action='store_true')
    a = p.parse_args()
    q = json.loads(Path(a.qualification).read_text())
    # qualified_for_scoring: the evaluation-scoring rule (score_qualification.py, DECISIONS 2026-11-06), which is what a
    # campaign uses the judge for; qualified_on_synthetic_controls: the stricter frozen screener rule
    qualified = q.get('status') in ('qualified_for_scoring', 'qualified_on_synthetic_controls') and q.get('judge') == a.backend
    # and only for the configuration it was qualified under: the receipt names the digest of this judge's settings
    if qualified and q.get('judge_config_sha256') != b.digest(b.manifest()['judges'][a.backend]):
        raise SystemExit(f'{a.backend} was qualified under different settings than backends_v1.json now has; requalify')
    if not qualified and not a.unqualified_diagnostic:
        raise SystemExit(f'{a.backend} is not qualified ({q.get("status")}); pass --unqualified-diagnostic to run it as a labelled diagnostic')
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'judge_status.json').write_text(json.dumps({'backend': a.backend, 'qualification': a.qualification, 'qualification_status': q.get('status'),
                                                      'diagnostic_only': not qualified}, indent=1))
    path = b.run_packets(a.backend, Path(a.packets), out, str(REPO), run_cap=a.run_cap, workers=a.workers)
    print(json.dumps({'predictions': str(path), 'diagnostic_only': not qualified}))


if __name__ == '__main__':
    main()
