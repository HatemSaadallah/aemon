"""CuratorKIT decides which training rows to keep and never rewrites one."""

import json

import pytest

pytest.importorskip('curatorkit')
pytest.importorskip('detect_secrets')

from aemon.rows.curate import curate, key  # noqa: E402

SYSTEM = {'role': 'system', 'content': 'the student prompt'}


def row(state: str, target: str, turn: int) -> dict:
    return {'messages': [SYSTEM, {'role': 'user', 'content': state}, {'role': 'assistant', 'content': target}],
            'target_index': 2, 'stage': 'evidence', 'case': 'x-base', 'episode': f'e{turn}', 'turn': turn}


def test_only_rows_with_the_same_state_and_target_are_dropped_and_kept_rows_are_unchanged(tmp_path):
    call = '{"name": "read_source", "arguments": {"id": "x-report-2025"}}'
    rows = [row('Current state: A', call, 1), row('Current state: A', call, 2),  # same lesson twice
            row('Current state: B', call, 3),  # the same call in another state is another lesson
            row('Current state: A', '{"name": "search_evidence", "arguments": {"query": "x demand"}}', 4)]
    before = json.dumps(rows, sort_keys=True)
    kept, summary = curate(rows, tmp_path / 'record')
    assert [r['turn'] for r in kept] == [1, 3, 4] and summary['dropped'] == 1
    assert json.dumps(rows, sort_keys=True) == before and all(k is r for k, r in zip(kept, [rows[0], rows[2], rows[3]]))
    decisions = json.loads((tmp_path / 'record/aemon_decisions.json').read_text())
    assert decisions['dropped'][0]['duplicate_of'] == 0
    assert {'manifest.json', 'lexsi_provenance.json', 'dataset_card.md'} <= {p.name for p in (tmp_path / 'record').iterdir()}
    assert key(rows[0]) == key(rows[1]) != key(rows[2])
