"""Training settings fixed in code."""

from __future__ import annotations

GATE_FAILED = 3

TARGETS = 'all-linear'  # LoRA on every linear layer, which beats attention-only in published comparisons
# The same layers by name, for Unsloth, which takes no 'all-linear': every linear layer of a Cohere2 block (not lm_head)
UNSLOTH_TARGETS = ('q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj')
