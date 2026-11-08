"""Claude as a positive control for the harness and as a blind judge. NEVER as training data.

Anthropic's commercial terms (section D.4) bar using the service to train competing AI models. Claude may test whether the
workflow can be completed and may score transcripts; nothing it writes or scores reaches a training row, which
strategy_agent.pipeline.provenance.training_source enforces from the manifest. Each request is charged to a ledger on disk
before the next is allowed, and the key is read from .env or the environment and never logged.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from strategy_agent.common.constants.claude import MAX_OUTPUT, MODEL, PRICES, TOTAL_CAP_USD  # noqa: F401
from strategy_agent.common.paths import LEDGER, ROOT
from strategy_agent.common.types import Json, Message, Schema

if TYPE_CHECKING:
    from pathlib import Path

    import anthropic
    from anthropic.types import MessageParam, OutputConfigParam


class BudgetExceeded(RuntimeError):
    pass


def api_key() -> str:
    key = os.environ.get('CLAUDE_API_KEY')
    if key:
        return key
    env = ROOT / '.env'
    for line in env.read_text().splitlines() if env.exists() else ():
        if line.startswith('CLAUDE_API_KEY='):
            return line.split('=', 1)[1].strip().strip('\'"')
    raise SystemExit('CLAUDE_API_KEY is not set')


def spent(ledger: Path = LEDGER) -> float | int:
    if not ledger.exists():
        return 0.0
    return sum(json.loads(line)['usd'] for line in ledger.read_text().splitlines())


def cost(model: str, usage: Json) -> Any:
    price = PRICES[model]
    return (
        usage['input'] * price['input']
        + usage['cache_write'] * price['cache_write']
        + usage['cache_read'] * price['cache_read']
        + usage['output'] * price['output']
    ) / 1e6


def _bare_json(text: str) -> str:
    """The same reply format as the other models, without a code fence if it adds one."""
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0]
    return text.strip()


class Claude:
    """Replies in the same plain JSON turn format as Tiny Aya, from the same prompt and tool results."""

    def __init__(
        self, purpose: str, run_cap_usd: float, effort: str = 'medium', model: str = MODEL, client: anthropic.Anthropic | None = None, ledger: Path = LEDGER
    ) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key(), max_retries=4)
        self.client, self.model, self.effort, self.purpose, self.ledger = client, model, effort, purpose, ledger
        self.run_cap, self.run_spent = run_cap_usd, 0.0

    def _check(self) -> None:
        if self.run_spent >= self.run_cap:
            raise BudgetExceeded(f'run cap of {self.run_cap} dollars reached')
        if spent(self.ledger) >= TOTAL_CAP_USD:
            raise BudgetExceeded(f'total cap of {TOTAL_CAP_USD} dollars reached')

    def _charge(self, usage: anthropic.types.Usage) -> Any:
        tokens = {
            'input': usage.input_tokens,
            'cache_write': usage.cache_creation_input_tokens or 0,
            'cache_read': usage.cache_read_input_tokens or 0,
            'output': usage.output_tokens,
        }
        usd = cost(self.model, tokens)
        self.run_spent += usd
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger, 'a') as log:
            log.write(
                json.dumps(
                    {'time': datetime.now(UTC).isoformat(timespec='seconds'), 'purpose': self.purpose, 'model': self.model, **tokens, 'usd': round(usd, 6)}
                )
                + '\n'
            )
        return usd

    def __call__(self, messages: list[Message], seed: int, max_tokens: int, schema: Schema | None, temperature: float) -> Json:
        """seed, max_tokens, schema and temperature belong to the local server. This API takes none of them."""
        self._check()
        history = [{'role': m['role'], 'content': m.get('raw') or m['content']} for m in messages[1:]]
        started = time.perf_counter()
        # One fixed model: a fallback would silently change what is being measured.
        response = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_OUTPUT,
            system=messages[0]['content'],
            messages=cast('list[MessageParam]', history),
            cache_control={'type': 'ephemeral'},
            output_config=cast('OutputConfigParam', {'effort': self.effort}),
        )
        usd = self._charge(response.usage)
        text = ''.join(block.text for block in response.content if block.type == 'text')
        return {
            'text': _bare_json(text),
            'prompt_tokens': response.usage.input_tokens,
            'completion_tokens': response.usage.output_tokens,
            'seconds': time.perf_counter() - started,
            'usd': round(usd, 5),
            'stop_reason': response.stop_reason,
            'raw': [block.to_dict() for block in response.content],
        }
