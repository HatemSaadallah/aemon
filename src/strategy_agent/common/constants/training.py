"""Training settings fixed in code."""

from __future__ import annotations

GATE_FAILED = 3

TARGETS = 'all-linear'  # LoRA on every linear layer, which beats attention-only in published comparisons
