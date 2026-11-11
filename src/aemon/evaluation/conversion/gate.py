"""Conversion gate v2 (docs/DECISIONS.md, 2026-11-06) over a conversion_diagnose replay. NOTHING HERE TRAINS.

Pass when, on every replayed point, the converted adapter's effect has cosine at least 0.99 with the PEFT adapter's
effect over the full vocabulary and a probability-weighted residual at most 0.15, and the tensor audit found every
factor pair equal to its expected BF16 cast. Greedy divergences are reported with PEFT's top-1/top-2 margin and with
whether the base alone diverged on the same prompt; they do not by themselves fail the gate.

Usage: python -m aemon.evaluation.conversion.gate --replay X.replay.json --tensors X.tensors.json --output gate.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aemon.common.types import Json

MIN_COSINE, MAX_RESIDUAL = 0.99, 0.15


def gate(replay: Json, tensors: Json) -> Json:
    points, divergences, failures = [], [], []
    for p in replay['prompts']:
        mode = p['modes']['matched_raw_greedy']
        on, off = mode['on']['difference'], mode['off']['difference']
        if on.get('kind') == 'different_token':
            margins = [(x.get('peft_reprefill_margin') or {}).get('margin') for x in p.get('points', [])]
            divergences.append(
                {
                    'case': p['case'],
                    'stage': p['stage'],
                    'offset': on.get('offset'),
                    'peft_margins': margins,
                    'base_alone_diverged': off.get('kind') == 'different_token',
                }
            )
        for x in p.get('points', []):
            summary = x.get('full_available_effect_summary')
            if not summary:
                failures.append(f'{p["case"]} {p["stage"]}: no effect summary')
                continue
            cosine, residual = summary['effect_cosine'], summary['conditional_probability_weighted_residual_rms']
            points.append({'case': p['case'], 'stage': p['stage'], 'cosine': round(cosine, 6), 'residual': round(residual, 4)})
            if cosine < MIN_COSINE or residual > MAX_RESIDUAL:
                failures.append(f'{p["case"]} {p["stage"]}: cosine {cosine:.4f}, residual {residual:.4f}')
    if tensors.get('status') != 'factor_pair_matches_expected_cast':
        failures.append(f'tensor audit: {tensors.get("status")}')
    return {
        'gate': 'conversion-v2',
        'passed': not failures and bool(points),
        'failures': failures,
        'points': len(points),
        'min_cosine': min((x['cosine'] for x in points), default=None),
        'max_residual': max((x['residual'] for x in points), default=None),
        'greedy_divergences': divergences,
        'gguf_sha256': replay.get('gguf_sha256'),
        'thresholds': {'min_cosine': MIN_COSINE, 'max_residual': MAX_RESIDUAL},
    }


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument('--replay', required=True)
    a.add_argument('--tensors', required=True)
    a.add_argument('--output', required=True)
    args = a.parse_args()
    result = gate(json.loads(Path(args.replay).read_text()), json.loads(Path(args.tensors).read_text()))
    Path(args.output).write_text(json.dumps(result, indent=1))
    print(
        json.dumps(
            {k: result[k] for k in ('gate', 'passed', 'points', 'min_cosine', 'max_residual')}
            | {'failures': len(result['failures']), 'divergences': len(result['greedy_divergences'])}
        )
    )


if __name__ == '__main__':
    main()
