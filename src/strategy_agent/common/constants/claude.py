"""The Claude control backend: model, spending cap and prices. Claude output is never training data."""

from __future__ import annotations

MODEL = 'claude-opus-5-5'

TOTAL_CAP_USD = 60.0  # of the 100 Hatem provided, leaving the rest unspent unless he says otherwise

MAX_OUTPUT = 8000  # includes thinking, which cannot be turned off on this model

PRICES = {'claude-opus-5-5': {'input': 4, 'cache_write': 5, 'cache_read': 0.2, 'output': 20}}  # dollars per million tokens
