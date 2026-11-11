"""Evidence records and search over them. Nothing here is generated: every record has a source.

Records keep their class, so a company's own claim or a proposed hypothesis is never treated as a
verified fact, and synthetic content cannot pass as real evidence.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from aemon.common.constants.env import CLASSES  # noqa: F401

WORD = re.compile(r'[a-z0-9]+')
STOP = frozenset(
    'a an and are as at be but by for from has have if in into is it its not of on or our that the their this to was we what when which who why will with would'.split()
)


def stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith('s') and not word.endswith('ss') else word


def words(text: str) -> list[str]:
    return [stem(w) for w in WORD.findall(text.lower()) if w not in STOP]


def normalise(text: str) -> str:
    """For quote checks: curly quotes, dashes and spacing are not what makes a quote false."""
    text = text.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    text = text.replace('–', '-').replace('—', '-').replace(' ', ' ')
    return re.sub(r'\s+', ' ', text).strip().lower()


@dataclass(frozen=True)
class Record:
    id: str
    type: str
    title: str
    url: str
    date: str
    excerpt: str
    access_limitation: str = 'none'
    topic: str = ''
    bears_on: tuple = field(default=())
    scope: str = 'market'  # 'market', or the one company this record is about
    kind: str = ''  # analyst annotation: what sort of evidence this is
    geography: str = 'unknown'
    population: str = 'unknown'
    does_not_establish: str = ''  # analyst annotation, never shown to the agent

    def __post_init__(self) -> None:
        if self.type not in CLASSES:
            raise ValueError(f'{self.id}: unknown class {self.type}')
        if not self.excerpt.strip():
            raise ValueError(f'{self.id}: empty excerpt')
        if self.type == 'synthetic' and not self.excerpt.startswith('SIMULATED'):
            raise ValueError(f'{self.id}: synthetic records must say SIMULATED')
        if self.type != 'synthetic' and not self.url.startswith('http') and self.type in ('verified_observation', 'company_claim'):
            raise ValueError(f'{self.id}: a sourced record needs a URL')


class Dossier:
    def __init__(self, records: Sequence[Record]) -> None:
        self.records = {r.id: r for r in records}
        if len(self.records) != len(records):
            raise ValueError('duplicate record ids')
        self._terms = {r.id: words(' '.join((r.title, r.excerpt))) for r in records}
        total = len(records) or 1
        counts = {}
        for terms in self._terms.values():
            for term in set(terms):
                counts[term] = counts.get(term, 0) + 1
        self._idf = {term: math.log(1 + total / n) for term, n in counts.items()}

    def search(self, query: str, k: int = 3) -> list[Record]:
        """Plain keyword search. It ranks by shared rare words, and knows nothing about theories."""
        wanted = set(words(query))
        scored = []
        for identifier, terms in self._terms.items():
            present = wanted & set(terms)
            if present:
                scored.append((sum(self._idf[t] for t in present), identifier))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [self.records[identifier] for _, identifier in scored[:k]]

    @staticmethod
    def load(path: str | Path) -> list[Record]:
        data = json.loads(Path(path).read_text())
        return [Record(**{**r, 'bears_on': tuple(json.dumps(b, sort_keys=True) for b in r.get('bears_on', ()))}) for r in data['records']]
