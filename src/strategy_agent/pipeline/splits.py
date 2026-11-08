from __future__ import annotations

from strategy_agent.common.constants.pipeline import VALIDATION_COMPANIES  # noqa: F401

"""Which companies each part of the work may use. Splits are by company, never by row: rows from one investigation
are near copies of each other, so a row split would leak.

Training: every development company not listed here. Validation: companies never trained on, used for held-out loss,
checkpoint choice and every development evaluation, so a result there says something about unseen companies.
Final test: cases_heldout.json, frozen in docs/final_test_freeze.json, opened once at the end.
"""


def is_validation(case_id: str) -> bool:
    return case_id.split('-')[0] in VALIDATION_COMPANIES


if __name__ == '__main__':  # the shell jobs read the split from here
    print(' '.join(VALIDATION_COMPANIES))
