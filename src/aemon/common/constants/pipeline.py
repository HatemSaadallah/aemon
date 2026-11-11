"""Data pipeline settings: the correction protocol, permitted teacher weights, splits and case fields."""

from __future__ import annotations

PROTOCOL = 'correction-v1'

MAX_PER_RUN = 3

ASK = (
    'You are shown the current state of an investigation another analyst was running. Their last calls went in a loop. '
    'Decide the single best next call. First say, briefly and specifically, what has already been learned, what uncertainty '
    'remains, and why your next call helps resolve it, naming the source, theory or result it acts on. Do not repeat a call '
    'listed as already tried, and do not move to a later step before the evidence for it is in place.'
)

# Permission is recorded in docs/DECISIONS.md. These hashes only bind it to the exact weights, so a label cannot launder a run.
TEACHER_WEIGHTS = {
    '47eed19801ed865fabad06f7c0eb4b079b874281a8caac486f99300c7bf525f9': 'aya-expanse-32b-Q4_K_M',
    # first part of bartowski's split GGUF at revision a26ba92, Apache 2.0, confirmed eligible by Lexsi on 2026-11-02
    '03cf0669f0a6f338a064f264b7c54df1bb882d16860ea513727b199c1ff05b8f': 'command-a-plus-05-2026-Q4_K_M',
    # DeepSeek V4-Pro through its API (DECISIONS 2026-11-10 22:55 UTC): MIT weights, and DeepSeek's terms allow training other
    # models on its outputs (copy in docs/terms/). There are no weights to hash, so this is the sha256 of the model label.
    '28d028636d6b35cb67cc1afd3409512147cefa2b57f7a709826e971b0ef23b70': 'deepseek-api deepseek-v4-pro DeepSeek-V4-Pro-0813',
}

# Six industries and eras, including one case where no test is warranted (Jotun). Hellberg chose earlier checkpoints.
VALIDATION_COMPANIES = ('hellberg', 'neumann', 'jotun', 'tanita', 'deere', 'acr')

LATE = ('test', 'position', 'new_evidence', 'update', 'conclude')

ANNOTATIONS = ('kind', 'geography', 'population', 'does_not_establish')

CASE_KEYS = ('company', 'question', 'brief', 'scope', 'search_budget', 'test_budget', 'max_test_weeks', 'id', 'premise_records', 'test_warranted')
