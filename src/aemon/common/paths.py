"""Every location the code reads or writes, relative to the repository root."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'data'
DOSSIER = DATA / 'dossier'
REPORTS = ROOT / 'reports'
RUNS = REPORTS / 'strategy'
PROVENANCE = RUNS / 'provenance.jsonl'
LEDGER = RUNS / 'claude_ledger.jsonl'
DOCS = ROOT / 'docs'
FREEZE = DOCS / 'final_test_freeze.json'
REVIEW = DATA / 'review' / 'excluded_episodes.json'  # episodes excluded from training after a substantive review, with reasons
