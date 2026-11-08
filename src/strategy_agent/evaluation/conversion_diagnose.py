"""Diagnostic evidence only: saved checker summaries, tensor audits, common-prefix replay. No qualification thresholds."""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import math
import os
import traceback
import urllib.request
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import numpy as np

from strategy_agent.evaluation.conversion_tensor_audit import audit, inventory, sha
from strategy_agent.pipeline.splits import is_validation

Json = dict[str, Any]


def save(path: str | Path, value: Json) -> None:
    with open(path, 'x') as out:
        json.dump(value, out, indent=1, allow_nan=False)
        out.write('\n')


def summarize(paths: list[str]) -> Json:
    reports = []
    for name in paths:
        p = Path(name)
        data = json.loads(p.read_text())
        rows = []
        for i, row in enumerate(data.get('results', [])):
            on, off = row['adapter_on'], row['adapter_off']
            prefix, of = on.get('greedy_tokens_agreeing'), on.get('of')
            rows.append(
                {
                    'index': i,
                    'case': row.get('case'),
                    'stage': row.get('stage'),
                    'prompt_tokens': row.get('prompt_tokens'),
                    'on_max_loggap': on.get('max_logprob_gap_on_shared'),
                    'off_max_loggap': off.get('max_logprob_gap_on_shared'),
                    'on_overlap': on.get('top10_overlap'),
                    'off_overlap': off.get('top10_overlap'),
                    'greedy_prefix': prefix,
                    'observed_common_length': of,
                    'divergence_observed': bool(prefix is not None and of is not None and prefix < of),
                    'prefix_exhausted_without_observed_split': bool(prefix is not None and prefix == of),
                    'actual_divergence_margin': None,
                    'adapter_effect_difference_of_differences': None,
                    'missing_reason': 'Saved aggregate maxima do not retain token IDs, actual divergence margins or four aligned distributions.',
                }
            )
        reports.append({'file': p.name, 'sha256': sha(p), 'reported_summary': data.get('summary'), 'reported_gate': data.get('gate'), 'prompts': rows})
    return {
        'kind': 'conversion_diagnosis_saved',
        'selection_eligible': False,
        'reports': reports,
        'conclusion': 'Aggregate reports describe observed discrepancies; they cannot prove a near-tie, tensor fidelity or harmlessness.',
    }


def first_difference(a: list[int], b: list[int]) -> Json:
    for k, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return {'kind': 'different_token', 'offset': k, 'native_token': x, 'gguf_token': y}
    return {'kind': 'same_recorded_tokens' if a == b else 'one_trace_ended_without_a_different_token', 'common_length': min(len(a), len(b))}


def log_softmax(x: np.ndarray) -> np.ndarray:
    y = x.astype(np.float64)
    if y.ndim != 1 or np.isnan(y).any() or np.isposinf(y).any() or not np.isfinite(y).any():
        raise ValueError('invalid logit vector')
    maximum = float(y.max())
    return y - maximum - math.log(float(np.exp(y - maximum).sum()))


def top_margin(lp: np.ndarray) -> Json:
    ids = np.argsort(lp)[-2:][::-1]
    margin = float(lp[ids[0]] - lp[ids[1]])
    return {
        'top1': int(ids[0]),
        'top2': int(ids[1]),
        'logprob1': float(lp[ids[0]]) if math.isfinite(float(lp[ids[0]])) else None,
        'logprob2': float(lp[ids[1]]) if math.isfinite(float(lp[ids[1]])) else None,
        'margin': margin if math.isfinite(margin) else None,
    }


def aligned_effect(po: np.ndarray, go: np.ndarray, pb: np.ndarray, gb: np.ndarray, tokens: list[int]) -> Json:
    """Same fixed token IDs in all four captures. Missing IDs are censored, never assigned zero."""
    rows = []
    for token in tokens:
        values = [float(v[token]) for v in (po, go, pb, gb)]
        if not all(math.isfinite(v) for v in values):
            rows.append({'token_id': token, 'status': 'missing_or_zero_probability'})
            continue
        a, b, c, d = values
        rows.append(
            {
                'token_id': token,
                'status': 'observed',
                'peft_on': a,
                'gguf_on': b,
                'peft_off': c,
                'gguf_off': d,
                'peft_effect': a - c,
                'gguf_effect': b - d,
                'effect_difference': (b - d) - (a - c),
                'on_error': b - a,
                'off_error': d - c,
            }
        )
    good = [r for r in rows if r['status'] == 'observed']
    return {
        'tokens': rows,
        'observed': len(good),
        'requested': len(tokens),
        'max_abs_on_error': max((abs(r['on_error']) for r in good), default=None),
        'max_abs_off_error': max((abs(r['off_error']) for r in good), default=None),
        'max_abs_effect_difference': max((abs(r['effect_difference']) for r in good), default=None),
        'note': 'Diagnostic on this fixed support, not a maximum over different token sets or a qualification score.',
    }


def effect_summary(po: np.ndarray, go: np.ndarray, pb: np.ndarray, gb: np.ndarray) -> Json:
    valid = np.isfinite(po) & np.isfinite(go) & np.isfinite(pb) & np.isfinite(gb)
    native, remote = po[valid] - pb[valid], go[valid] - gb[valid]
    residual = remote - native
    a, b = float(np.linalg.norm(native)), float(np.linalg.norm(remote))
    mass = float(np.exp(po[valid]).sum())
    return {
        'finite_common_tokens': int(valid.sum()),
        'vocab': len(po),
        'native_adapted_mass_on_evaluable_support': mass,
        'native_effect_l2': a,
        'gguf_effect_l2': b,
        'effect_cosine': float(np.dot(native, remote) / (a * b)) if a and b else None,
        'max_abs_effect_residual': float(np.abs(residual).max()) if len(residual) else None,
        'conditional_probability_weighted_residual_rms': float(np.sqrt(np.sum(np.exp(po[valid]) * residual**2) / mass)) if mass else None,
        'native_mass_where_gguf_on_has_zero_probability': float(np.exp(po[np.isfinite(po) & np.isneginf(go)]).sum()),
        'note': 'Common finite vocabulary support, with coverage reported. These are diagnostic measurements, not acceptance thresholds.',
    }


def api(url: str, path: str, body: Json | None = None) -> Json | list[Any]:
    headers = {'Content-Type': 'application/json'}
    if os.environ.get('LLAMA_API_KEY'):
        headers['Authorization'] = 'Bearer ' + os.environ['LLAMA_API_KEY']
    req = urllib.request.Request(url.rstrip('/') + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    with urllib.request.urlopen(req, timeout=1200) as response:
        return json.load(response)


def activation(settings: Any, requested: float) -> Json:
    if not isinstance(settings, dict):
        return {'status': 'unknown', 'reason': 'effective server settings absent'}
    params = settings.get('params', settings)
    declared = params.get('lora')
    if not isinstance(declared, list):
        return {'status': 'unknown', 'reason': 'effective LoRA scales absent'}
    actual = {a.get('id'): a.get('scale') for a in declared if a.get('scale') != 0}
    expected = {0: requested} if requested else {}
    return {'status': 'matches' if actual == expected else 'mismatch', 'requested': requested, 'declared': declared}


def server_trace(url: str, ids: list[int], scale: float, mode: str, n: int) -> Json:
    body = {
        'prompt': ids,
        'n_predict': n,
        'temperature': 0,
        'top_k': 1,
        'top_p': 1.0,
        'min_p': 0.0,
        'n_probs': 10 if mode == 'legacy_like' else 32,
        'cache_prompt': False,
        'lora': [{'id': 0, 'scale': scale}],
    }
    body.update(post_sampling_probs=False, repeat_penalty=1.0, presence_penalty=0.0, frequency_penalty=0.0)
    data = api(url, '/completion', body)
    if not isinstance(data, dict):
        raise ValueError('malformed server trace')
    steps = data['completion_probabilities']
    return {
        'tokens': [int(s['id']) for s in steps],
        'steps': steps,
        'generation_settings': data.get('generation_settings'),
        'stop_type': data.get('stop_type'),
        'stop': data.get('stop'),
        'request': body,
    }


def server_distribution(url: str, ids: list[int], scale: float, vocab: int, full: bool) -> tuple[np.ndarray, Json]:
    body = {
        'prompt': ids,
        'n_predict': 1,
        'temperature': 0,
        'top_k': 1,
        'top_p': 1.0,
        'min_p': 0.0,
        'n_probs': vocab if full else 2048,
        'post_sampling_probs': False,
        'repeat_penalty': 1.0,
        'presence_penalty': 0.0,
        'frequency_penalty': 0.0,
        'cache_prompt': False,
        'lora': [{'id': 0, 'scale': scale}],
    }
    data = api(url, '/completion', body)
    if not isinstance(data, dict) or data.get('truncated'):
        raise ValueError('invalid/truncated numerical replay')
    steps = data['completion_probabilities']
    if len(steps) != 1:
        raise ValueError('missing next-token distribution')
    lp = np.full(vocab, np.nan, dtype=np.float64)
    seen = set()
    for t in steps[0]['top_logprobs']:
        token = int(t['id'])
        value = float(t['logprob'])
        if token in seen or token < 0 or token >= vocab or math.isnan(value) or value > 1e-6:
            raise ValueError('bad token probability capture')
        seen.add(token)
        lp[token] = value
    return lp, {
        'request': body,
        'request_sha256': hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
        'returned': len(seen),
        'vocab': vocab,
        'full_vocabulary_observed': len(seen) == vocab,
        'generation_settings': data.get('generation_settings'),
        'requested_adapter_scale': scale,
        'adapter_activation': activation(data.get('generation_settings'), scale),
    }


def raw_native(model: Any, ids: list[int], last_logits_only: bool = False) -> np.ndarray:
    import torch

    with torch.inference_mode():
        # Match the historical raw-forward path; no last-logit optimization or precision recast is introduced here.
        options = {'logits_to_keep': 1} if last_logits_only else {}
        logits = model(torch.tensor([ids], device=model.device), **options).logits[0, -1].float().cpu().numpy()
    return log_softmax(logits)


@contextlib.contextmanager
def rounded_factor_values(model: Any) -> Iterator[list[str]]:
    """Separate treatment: BF16-rounded factor values in the ORIGINAL dtype/math. Always restore memory."""
    import torch

    names = []
    originals = []
    with torch.no_grad():
        for name, param in model.named_parameters():
            if '.lora_A.' in name or '.lora_B.' in name or name.startswith(('lora_A.', 'lora_B.')):
                names.append(name)
                originals.append((param, param.detach().clone()))
        if not originals:
            raise ValueError('no LoRA A/B factors to round in the declared reference')
        try:
            for param, _ in originals:
                param.copy_(param.to(torch.bfloat16).to(param.dtype))
            yield names
        finally:
            for param, value in originals:
                param.copy_(value)


def explicit_greedy_config(inherited: Any) -> Any:
    """Preserve inherited input; explicitly fix greedy controls and resolve remaining unset defaults."""
    result = copy.deepcopy(inherited)
    result.update(num_beams=1, do_sample=False, repetition_penalty=1.0, temperature=1.0, top_k=0, top_p=1.0)
    result.update(**result._get_default_generation_params(), defaults_only=True)
    return result


def greedy_beam_count(config: Any) -> int:
    """HF5 leaves unset fields as None; generate() fills num_beams from its global default (1)."""
    beams = getattr(config, 'num_beams', None)
    if beams is None:
        beams = config._get_default_generation_params()['num_beams']
    if beams != 1:
        raise ValueError('legacy beam-search margin requires beam ancestry, not greedy assumptions')
    return int(beams)


def replay(args: argparse.Namespace) -> None:
    if not os.environ.get('SLURM_JOB_ID'):
        raise ValueError('model replay must run inside an owner-submitted Slurm job')
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if Path(args.output).exists():
        raise FileExistsError('never overwrite diagnostic evidence')
    ref = json.loads(Path(args.reference_report).read_text())
    rows = [json.loads(s) for s in Path(args.rows).read_text().splitlines()]
    picked = [r for r in rows if is_validation(r['case'])] or rows
    n = len(ref['results'])
    if not n:
        raise ValueError('reference report has no numerical prompts')
    picked = picked[:: max(len(picked) // n, 1)][:n]
    if len(picked) != n:
        raise ValueError('historical prompt count cannot be reconstructed')
    tok = AutoTokenizer.from_pretrained(args.model)
    endpoint = urlsplit(args.url)
    words = [os.fsdecode(v) for v in Path(f'/proc/{int(args.server_pid)}/cmdline').read_bytes().split(b'\0') if v]
    if endpoint.hostname != '127.0.0.1' or endpoint.scheme != 'http' or '--port' not in words or endpoint.port != int(words[words.index('--port') + 1]):
        raise ValueError('server URL/PID mismatch')
    if '-m' not in words or Path(words[words.index('-m') + 1]).resolve() != Path(args.base_gguf).resolve():
        raise ValueError('served base path mismatch')
    props = api(args.url, '/props')
    adapters = api(args.url, '/lora-adapters')
    if not isinstance(adapters, list) or len(adapters) != 1 or Path(adapters[0]['path']).resolve() != Path(args.gguf).resolve():
        raise ValueError('declared GGUF adapter is not the sole loaded artifact')
    model = PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16, device_map={'': 0}), args.adapter).eval()
    scaling = {
        name: {'scale': dict(module.scaling), 'active_adapters': list(module.active_adapters), 'merged': bool(module.merged)}
        for name, module in model.named_modules()
        if hasattr(module, 'scaling') and hasattr(module, 'merged')
    }
    if any(v['merged'] for v in scaling.values()):
        raise ValueError('native reference has merged adapters; a clean unmerged comparison is required')
    config = model.generation_config.to_dict()
    decoded_fields = (
        'eos_token_id',
        'bos_token_id',
        'pad_token_id',
        'repetition_penalty',
        'no_repeat_ngram_size',
        'forced_bos_token_id',
        'forced_eos_token_id',
        'suppress_tokens',
        'begin_suppress_tokens',
        'bad_words_ids',
        'num_beams',
        'do_sample',
        'temperature',
        'top_k',
        'top_p',
        'cache_implementation',
        'cache_config',
        'use_cache',
        'renormalize_logits',
        'forced_decoder_ids',
    )
    out = {
        'kind': 'conversion_replay_diagnostic',
        'selection_eligible': False,
        'reference_report_sha256': sha(args.reference_report),
        'rows_sha256': sha(args.rows),
        'gguf_sha256': sha(args.gguf),
        'adapter_config_sha256': sha(Path(args.adapter) / 'adapter_config.json'),
        'native_tensor_hashes': {p.name: sha(p) for p in Path(args.adapter).glob('adapter_model*.safetensors')},
        'base_hf_hashes': {p.name: sha(p) for p in Path(args.model).iterdir() if p.suffix in ('.safetensors', '.json', '.bin', '.model')},
        'base_gguf_sha256': sha(args.base_gguf),
        'server_binary_sha256': sha(f'/proc/{int(args.server_pid)}/exe'),
        'server_kernel_args': {
            flag: words[j + 1]
            for j, flag in enumerate(words[:-1])
            if flag in ('-c', '-ngl', '-b', '-ub', '--flash-attn', '-fa', '--cache-type-k', '--cache-type-v')
        },
        'native_model_config': {
            k: model.config.to_dict().get(k)
            for k in (
                'architectures',
                'hidden_size',
                'num_hidden_layers',
                'sliding_window',
                'sliding_window_pattern',
                'rope_parameters',
                'rope_scaling',
                'max_position_embeddings',
                'logit_scale',
                'torch_dtype',
                'dtype',
            )
        },
        'native_attention_implementation': getattr(model.config, '_attn_implementation', None),
        'native_generation_config': {k: config.get(k) for k in decoded_fields},
        'native_effective_scaling': scaling,
        'native_parameter_dtypes': sorted({str(p.dtype) for p in model.parameters()}),
        'native_lora_dtypes': sorted({str(p.dtype) for name, p in model.named_parameters() if 'lora_' in name}),
        'torch': torch.__version__,
        'server_properties': props,
        'prompts': [],
        'normalization': 'FP64 log_softmax of HF raw logits; server returns raw softmax log probabilities. Token margins are invariant to log normalization.',
        'source_identity_note': 'Historical JSON often lacks token IDs. Reconstructions are labelled and are not cryptographic recovery of the old prompt.',
    }
    raw_dir = Path(args.output + '.arrays')
    raw_dir.mkdir(exist_ok=False)
    save(args.output + '.header.json', {k: v for k, v in out.items() if k != 'prompts'})
    for i, (item, row) in enumerate(zip(ref['results'], picked, strict=True)):
        if item.get('input_ids') is not None:
            ids = item['input_ids']
            identity = 'recorded_token_ids'
        else:
            if not args.ack_reconstructed:
                raise ValueError('historical token IDs absent; explicitly acknowledge reconstructed prompts')
            text = tok.apply_chat_template(row['messages'][: row['target_index']], tokenize=False, add_generation_prompt=True)
            ids = tok(text, add_special_tokens=False)['input_ids']
            identity = 'reconstructed_case_stage_length_only'
            if (item.get('case'), item.get('stage'), item.get('prompt_tokens')) != (row['case'], row.get('stage'), len(ids)):
                raise ValueError('reconstruction does not even match historical case/stage/length')
        entry = {
            'index': i,
            'selection_eligible': False,
            'case': item.get('case'),
            'stage': item.get('stage'),
            'input_ids': ids,
            'input_ids_sha256': hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            'prompt_identity': identity,
            'modes': {},
            'points': [],
        }
        for mode in ('matched_raw_greedy',):
            traces = {}
            for state in ('off', 'on'):
                ctx = model.disable_adapter() if state == 'off' else contextlib.nullcontext()
                remote = server_trace(args.url, ids, float(state == 'on'), mode, args.tokens)
                gcfg = explicit_greedy_config(model.generation_config)
                effective_beams = greedy_beam_count(gcfg)
                with ctx, torch.inference_mode():
                    modules = [m for m in model.modules() if hasattr(m, 'scaling') and hasattr(m, 'merged')]
                    native_controls = {
                        'modules': len(modules),
                        'disabled': sum(bool(m.disable_adapters) for m in modules),
                        'merged': sum(bool(m.merged) for m in modules),
                    }
                    tensor = torch.tensor([ids], device=model.device)
                    generated = model.generate(
                        tensor,
                        attention_mask=torch.ones_like(tensor),
                        generation_config=gcfg,
                        max_new_tokens=args.tokens,
                        do_sample=False,
                        return_dict_in_generate=True,
                        output_logits=True,
                        output_scores=True,
                    )
                native = generated.sequences[0, len(ids) :].tolist()
                difference = first_difference(native, remote['tokens'])
                trace = {
                    'native_tokens': native,
                    'gguf_tokens': remote['tokens'],
                    'difference': difference,
                    'server_generation_settings': remote['generation_settings'],
                    'server_stop_type': remote['stop_type'],
                    'native_generation_config': {k: gcfg.to_dict().get(k) for k in decoded_fields},
                    'native_inherited_generation_config': {k: config.get(k) for k in decoded_fields},
                    'server_request': remote['request'],
                    'server_adapter_activation': activation(remote['generation_settings'], float(state == 'on')),
                    'native_adapter_controls': native_controls,
                    'native_effective_num_beams': effective_beams,
                }
                if difference['kind'] == 'different_token':
                    t = difference['offset']
                    lp = log_softmax(generated.logits[t][0].float().cpu().numpy())
                    processed = log_softmax(generated.scores[t][0].float().cpu().numpy())
                    trace['actual_native_incremental_raw_margin'] = top_margin(lp)
                    trace['actual_native_incremental_processed_margin'] = top_margin(processed)
                    trace['native_selected_logprob'] = float(lp[native[t]])
                    trace['gguf_selected_under_native_logprob'] = float(lp[remote['tokens'][t]])
                    trace['native_selected_is_raw_top1'] = native[t] == int(np.argmax(lp))
                    trace['gguf_incremental_top_logprobs'] = remote['steps'][t]['top_logprobs']
                    np.savez_compressed(raw_dir / f'{i}_{mode}_{state}_incremental.npz', native_logprobs=lp, processed_native_logprobs=processed)
                traces[state] = trace
                del generated
            entry['modes'][mode] = traces
            save(
                args.output + f'.prompt{i}.{mode}.traces.json',
                {'selection_eligible': False, 'input_ids_sha256': entry['input_ids_sha256'], 'case': entry['case'], 'mode': mode, 'traces': traces},
            )
        points_to_replay = {hashlib.sha256(json.dumps(ids).encode()).hexdigest(): (0, 'matched_raw_greedy', 'on', ids)}
        for mode, traces in entry['modes'].items():
            for state in ('off', 'on'):
                difference = traces[state]['difference']
                if difference['kind'] == 'different_token':
                    offset = difference['offset']
                    prefix = ids + traces[state]['native_tokens'][:offset]
                    points_to_replay.setdefault(hashlib.sha256(json.dumps(prefix).encode()).hexdigest(), (offset, mode, state, prefix))
        for point_hash, (offset, mode, origin_state, prefix) in sorted(points_to_replay.items()):
            with model.disable_adapter():
                pb = raw_native(model, prefix)
                pb_last = raw_native(model, prefix, last_logits_only=True)
            po = raw_native(model, prefix)
            po_last = raw_native(model, prefix, last_logits_only=True)
            with rounded_factor_values(model) as rounded_names:
                po_rounded = raw_native(model, prefix)
            gb, mb = server_distribution(args.url, prefix, 0.0, len(po), args.full_logprobs)
            go, mo = server_distribution(args.url, prefix, 1.0, len(po), args.full_logprobs)
            arrays = raw_dir / f'{i}_{offset}_{point_hash}.npz'
            np.savez_compressed(
                arrays,
                peft_on=po,
                gguf_on=go,
                peft_off=pb,
                gguf_off=gb,
                peft_on_last_projection=po_last,
                peft_off_last_projection=pb_last,
                peft_on_bf16_rounded_values_original_math=po_rounded,
            )
            chosen = set()
            for vector in (po, go, pb, gb):
                chosen.update(int(t) for t in np.argsort(np.nan_to_num(vector, nan=-np.inf))[-32:])
            difference = entry['modes'][mode][origin_state]['difference']
            if difference['kind'] == 'different_token':
                chosen.update([difference['native_token'], difference['gguf_token']])
            support = sorted(chosen)
            effect = aligned_effect(po, go, pb, gb, support)
            projection_control = aligned_effect(po, po_last, pb, pb_last, support)
            cache_control = []
            if difference['kind'] == 'different_token' and difference['offset'] == offset:
                inc = np.load(raw_dir / f'{i}_{mode}_{origin_state}_incremental.npz')['native_logprobs']
                remote_inc = {int(x['id']): float(x['logprob']) for x in entry['modes'][mode][origin_state]['gguf_incremental_top_logprobs']}
                local_reprefill = po_last if origin_state == 'on' else pb_last
                remote_reprefill = go if origin_state == 'on' else gb
                for token in (difference['native_token'], difference['gguf_token']):
                    values = [float(inc[token]), float(local_reprefill[token]), remote_inc.get(token), float(remote_reprefill[token])]
                    cache_control.append(
                        {
                            'token_id': token,
                            'hf_incremental': values[0] if math.isfinite(values[0]) else None,
                            'hf_last_projection_reprefill': values[1] if math.isfinite(values[1]) else None,
                            'gguf_incremental': values[2] if values[2] is not None and math.isfinite(values[2]) else None,
                            'gguf_reprefill': values[3] if math.isfinite(values[3]) else None,
                        }
                    )
            for token in effect['tokens']:
                token['piece'] = tok.decode([token['token_id']])
            entry['points'].append(
                {
                    'offset': offset,
                    'prefix_mode': mode,
                    'origin_state': origin_state,
                    'incremental_vs_reprefill': cache_control,
                    'hf_full_vs_last_projection': projection_control,
                    'factor_rounding_control': {
                        'description': 'Only A/B values rounded to BF16 then restored to original dtype; base/math unchanged; original weights restored after query.',
                        'factor_count': len(rounded_names),
                        'effect': aligned_effect(po, po_rounded, pb, pb, support),
                    },
                    'remaining_effect_disagreement_after_factor_rounding': effect_summary(po_rounded, go, pb, gb),
                    'common_input_ids': prefix,
                    'common_input_ids_sha256': hashlib.sha256(json.dumps(prefix).encode()).hexdigest(),
                    'array_file': arrays.name,
                    'array_sha256': sha(arrays),
                    'peft_reprefill_margin': top_margin(po),
                    'server_on_capture': mo,
                    'server_off_capture': mb,
                    'full_available_effect_summary': effect_summary(po, go, pb, gb),
                    'effect': effect,
                }
            )
        out['prompts'].append(entry)
        save(args.output + f'.prompt{i}.json', entry)
    save(args.output, out)


def serve(args: argparse.Namespace) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == '/api/diagnosis':
                data = {
                    name: json.loads(Path(path).read_text()) if path and Path(path).exists() else {'status': 'not_available'}
                    for name, path in [('tensor_audit', args.tensor_audit), ('summary', args.summary), ('replay', args.replay)]
                }
                body = json.dumps(data, allow_nan=False).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)
            elif self.path == '/':
                page = """<!doctype html><meta charset="utf-8"><title>Conversion diagnosis</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Conversion diagnosis</h1><p>Diagnostic evidence only. Missing margins and tensor comparisons are unknown, not passed checks. A small token margin does not establish harmless behaviour.</p><h2>Artifact audit</h2><p id="artifact"></p><h2>Saved prompts</h2><table><thead><tr><th>Report / case</th><th>On / off max gap</th><th>Greedy prefix / overlap</th><th>Actual margin</th></tr></thead><tbody id="rows"></tbody></table><h2>Replay</h2><p id="replay"></p><details><summary>Full evidence and hashes</summary><pre id="raw"></pre></details><script>fetch('/api/diagnosis').then(r=>r.json()).then(d=>{document.getElementById('artifact').textContent=d.tensor_audit.status||'not_available';document.getElementById('replay').textContent=d.replay.prompts?d.replay.prompts.length+' prompts replayed; diagnostic, not qualification':'not_available';for(const r of d.summary.reports||[])for(const p of r.prompts){const tr=document.createElement('tr');for(const x of [r.file+' / '+p.case,String(p.on_max_loggap)+' / '+p.off_max_loggap,p.greedy_prefix+' / '+p.observed_common_length,p.actual_divergence_margin??'not recorded; replay needed']){const td=document.createElement('td');td.textContent=x;tr.append(td)}document.getElementById('rows').append(tr)}document.getElementById('raw').textContent=JSON.stringify(d,null,2)}).catch(e=>{document.getElementById('artifact').textContent=String(e)})</script>"""
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(page.encode())
            else:
                self.send_error(404)

        def log_message(self, format: str, *values: Any) -> None:
            pass

    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='step', required=True)
    p = commands.add_parser('inventory')
    p.add_argument('--gguf', required=True)
    p.add_argument('--output', required=True)
    p = commands.add_parser('audit-tensors')
    for arg in ('adapter', 'gguf', 'base-config', 'output'):
        p.add_argument('--' + arg, required=True)
    p = commands.add_parser('summarize')
    p.add_argument('--reports', nargs='+', required=True)
    p.add_argument('--output', required=True)
    p = commands.add_parser('replay')
    for arg in ('model', 'adapter', 'gguf', 'base-gguf', 'server-pid', 'rows', 'reference-report', 'url', 'output'):
        p.add_argument('--' + arg, required=True)
    p.add_argument('--tokens', type=int, default=32)
    p.add_argument('--ack-reconstructed', action='store_true')
    p.add_argument('--full-logprobs', action='store_true')
    p = commands.add_parser('serve')
    p.add_argument('--port', type=int, default=8015)
    for arg in ('tensor-audit', 'summary', 'replay'):
        p.add_argument('--' + arg)
    args = parser.parse_args()
    if args.step == 'inventory':
        save(args.output, inventory(args.gguf))
    elif args.step == 'audit-tensors':
        save(args.output, audit(args.adapter, args.gguf, args.base_config))
    elif args.step == 'summarize':
        save(args.output, summarize(args.reports))
    elif args.step == 'replay':
        try:
            replay(args)
        except Exception as error:
            save(
                args.output + '.failure.json',
                {
                    'selection_eligible': False,
                    'status': 'diagnostic_failed',
                    'error_type': type(error).__name__,
                    'message': str(error),
                    'traceback': traceback.format_exc(),
                },
            )
            raise
    else:
        serve(args)


if __name__ == '__main__':
    main()
