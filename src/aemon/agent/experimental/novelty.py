"""V1-r, experimental: novelty-first search (docs/RETRIEVAL_PROPOSAL.md, approved 2026-11-10).

search_evidence and challenge_theory keep the same keyword ranking and budget. Each returns up to 3 of the
highest-ranked records the run has not yet been shown, and when fewer than 3 remain it fills with the next-best records
already shown, as today. The query checks, the repeat refusal, the budget, the prompt, the state, the schemas, the
guards and the limits are those of the evaluated environment, because the original _run_search still runs: only the
dossier ranking it calls is wrapped, for this process.

    python -m aemon.agent.experimental.novelty [the runner's arguments]  # development split only
"""

from __future__ import annotations

import contextvars
import sys
from typing import Any

from aemon.agent import run_investigations
from aemon.environment.dossier import Dossier, words
from aemon.environment.tools import Investigation

VERSION = 'novelty-v1'
_RUN: contextvars.ContextVar[Any] = contextvars.ContextVar('run', default=None)
_SEARCH = Dossier.search
_RUN_SEARCH = Investigation._run_search


def ranked(dossier: Dossier, query: str) -> list[str]:
    """The original ranking (shared rare words, then id), every match."""
    wanted = set(words(query))
    scored = [(sum(dossier._idf[t] for t in wanted & set(terms)), i) for i, terms in dossier._terms.items() if wanted & set(terms)]
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [i for _, i in scored]


def search(self: Dossier, query: str, k: int = 3) -> list[Any]:
    run = _RUN.get()
    if run is None or run.case.dossier is not self:
        return _SEARCH(self, query, k)
    order = ranked(self, query)
    new = [i for i in order if i not in run.surfaced]
    seen = [i for i in order if i in run.surfaced]
    return [self.records[i] for i in (new + seen)[:k]]


def run_search(self: Investigation, query: str, target: str | None) -> Any:
    token = _RUN.set(self)
    try:
        return _RUN_SEARCH(self, query, target)
    finally:
        _RUN.reset(token)


def install() -> None:
    Dossier.search = search
    Investigation._run_search = run_search


def main() -> None:
    if '--split' in sys.argv and sys.argv[sys.argv.index('--split') + 1] != 'development':
        raise SystemExit('V1-r is experimental: development split only until it passes its evaluation')
    install()  # this process only
    run_investigations.main()


if __name__ == '__main__':
    main()
