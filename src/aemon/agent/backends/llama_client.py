"""The model client: one chat request to a llama.cpp server, and parsing the tool call out of the reply.

Used by strategy/, aemon and the evaluation tools. NO TRAINING.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request

from aemon.common.constants.prompts import STOP, THINK_END, THINK_START  # noqa: F401
from aemon.common.types import Json, LoraSetting, Message, Schema

TOOL_CALL = re.compile(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', re.DOTALL)


def headers() -> dict[str, str]:
    """A server on another node listens on the cluster network, so it is started with a key, given here as LLAMA_API_KEY."""
    out = {'Content-Type': 'application/json'}
    if os.environ.get('LLAMA_API_KEY'):
        out['Authorization'] = 'Bearer ' + os.environ['LLAMA_API_KEY']
    return out


def split_thinking(text: str) -> tuple[str, None] | tuple[str, str]:
    """Reasoning models write a thinking block before the call. It is kept on record, and only the call is parsed."""
    if THINK_END not in text:
        return text, None
    thinking, call = text.rsplit(THINK_END, 1)
    return call.strip(), thinking.replace(THINK_START, '').strip()


def lora_body(lora: LoraSetting) -> list[dict[str, float]]:
    """A number is the scale of the one adapter. A list names every adapter with its scale, as a route gives it.
    Anything else is refused here, because the server silently falls back to its default, which applies the adapters."""
    if isinstance(lora, (int, float)) and not isinstance(lora, bool):
        return [{'id': 0, 'scale': float(lora)}]
    if isinstance(lora, list) and all(isinstance(a, dict) and set(a) == {'id', 'scale'} for a in lora):
        return lora
    raise ValueError(f'not an adapter setting: {lora!r}')


def chat(url: str, messages: list[Message], seed: int, max_tokens: int, schema: Schema | None = None, temperature: float = 0, lora: LoraSetting = None) -> Json:
    # Older Cohere GGUFs do not mark this as an end token, so it arrives as text and breaks the server's reply parser.
    body = {'messages': messages, 'temperature': temperature, 'seed': seed, 'max_tokens': max_tokens, 'stream': False, 'stop': [STOP, '<|END_OF_TURN_TOKEN|>']}
    if schema:
        body['response_format'] = {'type': 'json_schema', 'json_schema': {'name': 'tool_call', 'schema': schema}}
    if lora is not None:  # one server, one base model: adapters are switched on or off per request
        body['lora'] = lora_body(lora)
    request = urllib.request.Request(url + '/v1/chat/completions', data=json.dumps(body).encode(), headers=headers())
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=int(os.environ.get('CHAT_TIMEOUT', 300))) as response:
        data = json.load(response)
    text, thinking = split_thinking(data['choices'][0]['message'].get('content') or '')
    if '<tool_call>' in text and STOP not in text:
        text += STOP  # the stop string is removed from the reply, so put it back
    return {
        'text': text,
        'thinking': thinking,
        'prompt_tokens': data['usage']['prompt_tokens'],
        'completion_tokens': data['usage']['completion_tokens'],
        'seconds': time.perf_counter() - started,
    }


def parse_call(text: str, bare: bool = False) -> tuple[Json | None, str | None]:
    if bare:
        try:
            call = json.loads(text)
        except json.JSONDecodeError as error:
            return None, f'That was not valid JSON: {error.msg}.'  # only when the reply was cut off by the token limit
        if type(call) is not dict or type(call.get('name')) is not str or type(call.get('arguments')) is not dict:
            return None, 'A call needs a name and an arguments object.'
        return call, None
    match = TOOL_CALL.search(text)
    if not match:
        return None, 'Reply with one <tool_call>...</tool_call> block.'
    try:
        call = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        return None, f'That was not valid JSON: {error.msg}.'
    if type(call) is not dict or type(call.get('name')) is not str or type(call.get('arguments')) is not dict:
        return None, 'A call needs a name and an arguments object.'
    return call, None
