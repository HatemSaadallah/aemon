"""Provenance: the append-only manifest of what the permitted teacher wrote, and the check that a training row came from it.

Anthropic's commercial terms (section D.4) bar using the service to train competing AI models. So
Claude may test whether the workflow can be completed, and may score transcripts, but nothing it
writes or scores may reach a training row or decide which rows are kept. training_source enforces
that from the provenance manifest, whatever a report's labels say.

Each request is charged to a ledger on disk before the next one is allowed, and the key is read
from .env or the environment and never logged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from aemon.common.constants.pipeline import TEACHER_WEIGHTS
from aemon.common.paths import PROVENANCE
from aemon.common.types import Json

if TYPE_CHECKING:
    from aemon.environment.tools import Case


class GenerationSettings(BaseModel):
    """How the teacher server was started, which the server does not report. Only the keys given are written back."""

    model_config = ConfigDict(extra='allow', frozen=True)

    reasoning_budget: int | None = None
    context_per_slot: int | None = None
    slots: int | None = None


class InvestigationEntry(BaseModel):
    """One episode the runner finished. Early entries have no case, turns, generation or slots."""

    model_config = ConfigDict(frozen=True)

    episode: str
    case: str | None = None
    turns: int | None = None
    backend: str
    weights_sha256: str | None
    model_id: str
    protocol: str | None
    generation: GenerationSettings | None = None
    slots: int | None = None


class CorrectionEntry(BaseModel):
    """One teacher reply to a student state, hashed before it is judged. Early entries have no generation."""

    model_config = ConfigDict(frozen=True)

    protocol: Literal['correction-v1']
    case: str
    case_digest: str
    student_run: str
    turn: int
    weights_sha256: str
    generation: GenerationSettings | None = None
    reply_sha256: str


ManifestEntry = InvestigationEntry | CorrectionEntry


def parse_entry(line: str) -> ManifestEntry:
    """Corrections share the manifest and have no episode."""
    raw = json.loads(line)
    return InvestigationEntry.model_validate(raw) if 'episode' in raw else CorrectionEntry.model_validate(raw)


def read_manifest(path: str | Path) -> list[ManifestEntry]:
    path = Path(path)
    return [parse_entry(line) for line in path.read_text().splitlines()] if path.exists() else []


def append_entry(entry: ManifestEntry, path: str | Path) -> None:
    """Entries are only ever added. Writers set every field, so excluding unset ones only keeps generation as given."""
    with open(path, 'a') as log:
        log.write(json.dumps(entry.model_dump(mode='json', exclude_unset=True)) + '\n')


def case_digest(case: Case) -> str:
    """The case and every record it can see, so a row cannot be moved to other evidence."""
    shown = [[r.id, r.type, r.excerpt] for r in sorted(case.dossier.records.values(), key=lambda r: r.id)]
    shock = [case.shock.id, case.shock.excerpt, case.shock_direction] if case.shock else None
    return hashlib.sha256(json.dumps([case.id, case.question, case.brief, shock, shown], sort_keys=True).encode()).hexdigest()


def episode_id(turns: list[Json], case: Case, protocol_id: str | None) -> str:
    """Binds everything a row is built from: each reply's exact text and its tool result, in order, the case
    and its evidence, and the protocol. Changing a target, cutting the stream or moving it changes the id."""
    stream = [[t['text'], t['tool_result']] for t in turns]
    return hashlib.sha256(json.dumps([stream, case_digest(case), protocol_id], sort_keys=True).encode()).hexdigest()


def record_provenance(turns: list[Json], case: Case, model: Json, protocol_id: str | None, path: str | Path = PROVENANCE) -> str:
    """Written by the runner as each episode ends. Entries are only ever added."""
    episode = episode_id(turns, case, protocol_id)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = InvestigationEntry(
        episode=episode,
        case=case.id,
        turns=len(turns),
        backend=model['backend'],
        weights_sha256=model['weights_sha256'],
        model_id=model['id'],
        protocol=protocol_id,
        generation=GenerationSettings.model_validate(model.get('generation') or {}),
        slots=model.get('slots'),
    )
    append_entry(entry, path)
    return episode


def training_source(turns: list[Json], case: Case, protocol_id: str | None, path: str | Path = PROVENANCE) -> InvestigationEntry:
    """Refuses an episode unless the manifest shows a permitted teacher wrote exactly this stream.
    An episode any other source produced is refused, whatever a report now says."""
    episode = episode_id(turns, case, protocol_id)
    entries = [e for e in read_manifest(path) if isinstance(e, InvestigationEntry) and e.episode == episode]
    if not entries:
        raise ValueError('this exact episode is not in the provenance manifest, so it cannot become training data')
    if any(e.backend != 'llama' or e.weights_sha256 not in TEACHER_WEIGHTS for e in entries):
        raise ValueError('this episode did not come from a permitted teacher, so it cannot become training data')
    return entries[0]
