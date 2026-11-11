"""A hosted teacher (DeepSeek's API) behind the same chat() signature as model_client.chat. NO TRAINING.

Development only: used by pipeline/hosted_teacher.py, never by the evaluated runner, Aemon or the judges.
The llama.cpp server constrains a reply with a JSON schema. DeepSeek offers strict tool calling instead, which rejects
maxLength, minItems and maxItems and needs every property required. So the schema is converted for the request, the reply
is checked against the ORIGINAL schema here, a repair turn names what broke, and a reply that still breaks it is
returned as non-JSON so every gate refuses it, as a reply cut by the grammar would be refused. Up to HOSTED_REPAIRS (2) repair turns.

Every request is logged (model, fingerprint, usage, cost) to HOSTED_LOG, and a run stops before its spend passes
HOSTED_BUDGET_USD. The API key is read from DEEPSEEK_API_KEY and never written anywhere.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Any

import jsonschema
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_incrementing

from aemon.common.types import Json, LoraSetting, Message, Schema

BASE = 'https://api.deepseek.com/beta'  # strict tool calling is a beta feature
UNSUPPORTED = ('maxLength', 'minLength', 'minItems', 'maxItems')
# USD per million tokens (cache hit, cache miss, output), peak; off-peak is half. api-docs.deepseek.com, read 2026-11-10.
PRICES = {'deepseek-flash': (0.006, 0.3, 1.2), 'deepseek-v4-pro': (0.044, 1.32, 3.96)}
_lock = threading.Lock()
_spent = [0.0]
_balance: list[float] = [float('inf'), 0.0]  # last balance read from the API, and when


def balance_floor_reached() -> bool:
    """True when DeepSeek's actual balance is below HOSTED_MIN_BALANCE (Hatem, 2026-11-10: keep $5 at the end). Read from
    the API at most once a minute; a failed read keeps the last value."""
    floor = float(os.environ.get('HOSTED_MIN_BALANCE', '0'))
    if floor <= 0:
        return False
    with _lock:
        if time.time() - _balance[1] > 20:
            try:
                request = urllib.request.Request('https://api.deepseek.com/user/balance', headers={'Authorization': 'Bearer ' + os.environ['DEEPSEEK_API_KEY']})
                with urllib.request.urlopen(request, timeout=20) as response:
                    data = json.load(response)
                _balance[0] = sum(float(b['total_balance']) for b in data.get('balance_infos', []) if b.get('currency') == 'USD')
            except Exception:  # noqa: BLE001
                pass
            _balance[1] = time.time()
        # requests already in flight keep billing after the check (2026-11-11: 16 at once overshot a $5 floor by $0.48),
        # so new work stops HOSTED_FLOOR_MARGIN above the floor
        return _balance[0] < floor + float(os.environ.get('HOSTED_FLOOR_MARGIN', '1.5'))


def model() -> str:
    return os.environ.get('HOSTED_MODEL', 'deepseek-flash')


def peak(now: dt.datetime | None = None) -> bool:
    """01:00-04:00 and 06:00-10:00 UTC, Monday to Friday (Chinese public holidays, also off-peak, are not modelled: this
    can only overestimate the cost)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    return now.weekday() < 5 and (1 <= now.hour < 4 or 6 <= now.hour < 10)


def cost(usage: Json, name: str, at_peak: bool) -> float:
    hit_price, miss_price, out_price = PRICES[name]
    factor = 1.0 if at_peak else 0.5
    hit = usage.get('prompt_cache_hit_tokens', 0) or 0
    miss = usage.get('prompt_cache_miss_tokens', usage.get('prompt_tokens', 0) - hit) or 0
    return factor * (hit * hit_price + miss * miss_price + usage.get('completion_tokens', 0) * out_price) / 1e6


def strict(schema: Any) -> Any:
    """The schema DeepSeek's strict mode accepts: unsupported keywords dropped, const as a one-value enum, every object
    closed with all properties required (an optional property becomes nullable, and a null is removed from the reply)."""
    if isinstance(schema, list):
        return [strict(x) for x in schema]
    if not isinstance(schema, dict):
        return schema
    out = {k: strict(v) for k, v in schema.items() if k not in UNSUPPORTED}
    if 'const' in out:
        out['enum'] = [out.pop('const')]
    if 'type' not in out and 'anyOf' not in out and '$ref' not in out:  # DeepSeek needs one of them on every schema
        if 'properties' in out:
            out['type'] = 'object'
        elif 'items' in out:
            out['type'] = 'array'
        elif 'enum' in out:
            kinds = {type(v) for v in out['enum']}
            out['type'] = {str: 'string', int: 'integer', float: 'number', bool: 'boolean'}.get(kinds.pop(), 'string') if len(kinds) == 1 else 'string'
    if (out.get('type') == 'object' or 'properties' in out) and not out.get('properties'):
        extra = schema.get('additionalProperties') if isinstance(schema, dict) else None
        if isinstance(extra, dict):  # a map keyed by ids: strict mode has no such object, so a list of key/value pairs
            return {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['key', 'value'],
                                               'properties': {'key': {'type': 'string'}, 'value': strict(extra)}}}
        out['properties'] = {'_none': {'type': 'null'}}  # strict mode refuses an object with no properties
    if out.get('type') == 'object' or 'properties' in out:
        props = out.get('properties', {})
        required = set(out.get('required', []))
        for name in props:
            if name not in required:
                props[name] = {'anyOf': [props[name], {'type': 'null'}]}
        out['required'] = list(props)
        out['additionalProperties'] = False
    return out


def drop_nulls(value: Any, schema: Any) -> Any:
    """Removes the nulls strict() allowed for optional properties, so the reply has the original shape."""
    if isinstance(schema, dict) and not schema.get('properties') and isinstance(schema.get('additionalProperties'), dict) and isinstance(value, list):
        return {str(i.get('key')): drop_nulls(i.get('value'), schema['additionalProperties']) for i in value if isinstance(i, dict)}
    if isinstance(value, dict):
        props = schema.get('properties', {}) if isinstance(schema, dict) else {}
        required = set(schema.get('required', [])) if isinstance(schema, dict) else set()
        return {k: drop_nulls(v, props.get(k, {})) for k, v in value.items() if not (v is None and k not in required)}
    if isinstance(value, list):
        return [drop_nulls(v, schema.get('items', {}) if isinstance(schema, dict) else {}) for v in value]
    return value


def problems(value: Any, schema: Schema) -> list[str]:
    """What the reply breaks in the original schema, in words the model can act on."""
    out = []
    for error in jsonschema.Draft202012Validator(schema).iter_errors(value):
        where = '.'.join(str(p) for p in error.absolute_path) or 'the answer'
        if error.validator == 'maxLength':
            out.append(f'{where}: {len(error.instance)} characters, at most {error.validator_value}')
        elif error.validator in ('maxItems', 'minItems'):
            out.append(f'{where}: {len(error.instance)} items, {"at most" if error.validator == "maxItems" else "at least"} {error.validator_value}')
        elif error.validator != 'anyOf':
            out.append(f'{where}: {error.message[:200]}')
    if not out and not jsonschema.Draft202012Validator(schema).is_valid(value):
        # an anyOf failure: report the closest branch, the one with the fewest errors
        best = min(error_branches(value, schema), key=len, default=['does not match the required shape'])
        out = best
    return out


def error_branches(value: Any, schema: Schema) -> list[list[str]]:
    branches = []
    for error in jsonschema.Draft202012Validator(schema).iter_errors(value):
        for sub in error.context or []:
            branches.append([f'{".".join(str(p) for p in sub.absolute_path) or "the call"}: {sub.message[:200]}'])
    return branches


def _retryable(error: BaseException) -> bool:
    """Rate limits, server errors, dropped connections and timeouts are retried; any other HTTP error is not."""
    if isinstance(error, urllib.error.HTTPError):
        return error.code in (429, 500, 502, 503)
    return isinstance(error, (urllib.error.URLError, TimeoutError))


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


@retry(stop=stop_after_attempt(4), wait=wait_incrementing(start=10, increment=10), retry=retry_if_exception(_retryable), reraise=True,
       sleep=lambda seconds: _sleep(seconds))
def _send(request: urllib.request.Request) -> Json:
    """At most 4 attempts, 10, 20 and 30 seconds apart."""
    with urllib.request.urlopen(request, timeout=int(os.environ.get('CHAT_TIMEOUT', 600))) as response:
        return json.load(response)


def _post(body: Json) -> Json:
    request = urllib.request.Request(BASE + '/chat/completions', data=json.dumps(body).encode(), headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ['DEEPSEEK_API_KEY']})
    try:
        return _send(request)
    except urllib.error.HTTPError as error:  # not retryable, or still failing after the last attempt
        raise RuntimeError(f'DeepSeek HTTP {error.code}: {error.read()[:300]!r}') from None


def _log(entry: Json) -> None:
    path = os.environ.get('HOSTED_LOG')
    if path:
        with _lock, open(path, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def _one(messages: list[Message], max_tokens: int, schema: Schema | None, temperature: float) -> tuple[str, str | None, Json, Json]:
    name = model()
    budget = float(os.environ.get('HOSTED_BUDGET_USD', '5'))
    with _lock:
        if _spent[0] >= budget:
            raise RuntimeError(f'hosted budget of ${budget} reached')
    if balance_floor_reached():
        raise RuntimeError(f'DeepSeek balance below the ${os.environ.get("HOSTED_MIN_BALANCE")} floor')
    body: Json = {'model': name, 'messages': messages, 'max_tokens': max(max_tokens, int(os.environ.get('HOSTED_MAX_TOKENS', 16000))),
                  'temperature': temperature, 'stream': False}
    if schema:
        body['tools'] = [{'type': 'function', 'function': {
            'name': 'answer', 'strict': True, 'parameters': strict(schema),
            'description': 'Give your answer. Every text field has a character limit: ' + limits(schema)}}]
        if os.environ.get('HOSTED_TOOL_CHOICE'):  # thinking mode (the default) refuses a forced call; one tool is offered
            body['tool_choice'] = os.environ['HOSTED_TOOL_CHOICE']
    started = time.perf_counter()
    at_peak = peak()
    data = _post(body)
    message = data['choices'][0]['message']
    usage = data.get('usage', {})
    spend = cost(usage, name, at_peak)
    with _lock:
        _spent[0] += spend
    calls = message.get('tool_calls') or []
    text = calls[0]['function']['arguments'] if calls else (message.get('content') or '')
    _log({'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'model': data.get('model'), 'requested': name,
          'fingerprint': data.get('system_fingerprint'), 'finish': data['choices'][0].get('finish_reason'), 'usage': usage,
          'usd': round(spend, 6), 'peak': at_peak, 'seconds': round(time.perf_counter() - started, 1), 'tool_call': bool(calls)})
    return text, message.get('reasoning_content'), usage, message


def as_json(text: str) -> Any:
    """The tool call's arguments, or, if the model answered in text, the JSON object in it (a fenced block or the outermost braces)."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find('{'), text.rfind('}')
        if start < 0 or end <= start:
            raise
        return json.loads(text[start:end + 1])


def limits(schema: Any, path: str = '') -> str:
    found = []

    def walk(o: Any, where: str) -> None:
        if isinstance(o, dict):
            if 'maxLength' in o:
                found.append(f'{where or "text"} {o["maxLength"]}')
            for k, v in o.get('properties', {}).items():
                walk(v, k)
            for v in o.get('anyOf', []):
                walk(v, where)
            if 'items' in o:
                walk(o['items'], where)
    walk(schema, path)
    return ', '.join(dict.fromkeys(found)) + '.' if found else 'none.'


def chat(url: str, messages: list[Message], seed: int, max_tokens: int, schema: Schema | None = None, temperature: float = 0, lora: LoraSetting = None) -> Json:
    """Same contract as model_client.chat. url, seed and lora are ignored: the API has no adapters and no seed."""
    started = time.perf_counter()
    original = schema
    if schema and schema.get('type') != 'object':  # the API needs an object at the top: the call is wrapped, then unwrapped
        schema = {'type': 'object', 'additionalProperties': False, 'required': ['call'], 'properties': {'call': schema}}
    text, thinking, usage, message = _one(messages, max_tokens, schema, temperature)
    prompt_tokens, completion_tokens = usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0)
    if schema:
        value, broken = _check(text, schema)
        history = list(messages)
        for _ in range(int(os.environ.get('HOSTED_REPAIRS', 2))):  # repair turns with the exact problems; the model's own text, never ours
            if not broken:
                break
            note = ('That answer breaks the tool limits:\n' + '\n'.join('- ' + b for b in broken[:12]) +
                    '\nCall the answer tool again with the same answer and only those parts fixed. Shorten a long field to about 85% '
                    'of its limit, keeping its meaning and every id, number and theory it names. Change nothing else.')
            calls = message.get('tool_calls') or []
            if calls:  # the refusal goes back as the tool's result, so the model answers with the tool again
                turn = {'role': 'assistant', 'content': message.get('content') or '', 'tool_calls': calls}
                if message.get('reasoning_content'):
                    turn['reasoning_content'] = message['reasoning_content']
                history += [turn, {'role': 'tool', 'tool_call_id': calls[0]['id'], 'content': note}]
                history += [{'role': 'tool', 'tool_call_id': c['id'], 'content': 'Ignored: give one answer only.'} for c in calls[1:]]
            else:
                history += [{'role': 'assistant', 'content': text}, {'role': 'user', 'content': note}]
            text, more, usage2, message = _one(history, max_tokens, schema, temperature)
            thinking = '\n\n[repair turn]\n'.join(x for x in (thinking, more) if x)
            prompt_tokens += usage2.get('prompt_tokens', 0)
            completion_tokens += usage2.get('completion_tokens', 0)
            value, broken = _check(text, schema)
        if not broken and schema is not original:
            value = value['call']
        text = json.dumps(value, ensure_ascii=False) if not broken else 'SCHEMA VIOLATION after the repair turns: ' + '; '.join(broken[:5])
    return {'text': text, 'thinking': thinking, 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens,
            'seconds': time.perf_counter() - started}


def _check(text: str, schema: Schema) -> tuple[Any, list[str]]:
    try:
        value = drop_nulls(as_json(text), schema)
    except json.JSONDecodeError:
        return None, ['not valid JSON']
    return value, problems(value, schema)


def spent() -> float:
    return _spent[0]

