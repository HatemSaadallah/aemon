"""The Claude control backend: model, spending cap and prices. Claude output is never training data."""

from __future__ import annotations

MODEL = 'claude-opus-5-5'

TOTAL_CAP_USD = 60.0  # of the 100 Hatem provided, leaving the rest unspent unless he says otherwise

MAX_OUTPUT = 8000  # includes thinking, which cannot be turned off on this model

# dollars per million tokens. Haiku 5.5 has two rate cards by prompt length: these up to 100K prompt tokens, and
# LONG_PROMPT above it (cache reads 0.1x and 5-minute cache writes 1.25x of the input rate).
PRICES = {
    'claude-opus-5-5': {'input': 4, 'cache_write': 5, 'cache_read': 0.2, 'output': 20},
    'claude-haiku-5-5': {'input': 0.10, 'cache_write': 0.125, 'cache_read': 0.01, 'output': 0.50},
}
LONG_PROMPT = {'claude-haiku-5-5': (100_000, {'input': 0.50, 'cache_write': 0.625, 'cache_read': 0.05, 'output': 2.50})}
