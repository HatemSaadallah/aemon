"""Type aliases shared across the package. Records on disk are JSON, so they are typed as JSON objects."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

Json = dict[str, Any]
"""A JSON object as read from or written to disk: a record, a tool result, a tool call's arguments."""
Message = dict[str, Any]
"""One chat message: role and content, and for a backend's own reply form, raw."""
Schema = dict[str, Any]
"""A JSON schema the model server enforces while generating."""
LoraSetting = float | list[dict[str, float]] | None
"""The scale of the one adapter, or every adapter with its scale, as a route gives it."""
Respond = Callable[..., Json]
"""The model: messages, seed, max tokens, schema and temperature in, a reply out."""
Direction = Literal['supports', 'contradicts', 'neutral']
Status = Literal['passed', 'failed', 'not_evaluated', 'not_applicable']
Verdict = tuple[bool | None, str]
"""A check's result: passed, failed or not evaluated (None), with the reason."""
