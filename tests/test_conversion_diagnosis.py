"""Synthetic artifact/number tests; no model inference, qualification evidence or training data."""

import json
import struct
from typing import Any

import numpy as np
import pytest
import torch
from safetensors.torch import save_file
from strategy_agent.evaluation.conversion_diagnose import aligned_effect, first_difference, log_softmax, summarize, top_margin
from strategy_agent.evaluation.conversion_tensor_audit import GGUF, audit, inventory, native_key


def string(s: Any) -> Any:
    b = s.encode()
    return struct.pack('<Q', len(b)) + b


def write_gguf(path: Any, factors: Any, alpha: Any = 4, kind: Any = 30, duplicate: Any = False) -> Any:
    meta = b''
    for k, value in [('general.architecture', 'cohere2'), ('general.type', 'adapter'), ('adapter.type', 'lora')]:
        meta += string(k) + struct.pack('<I', 8) + string(value)
    meta += string('adapter.lora.alpha') + struct.pack('<If', 6, alpha)
    directory = b''
    payload = bytearray()
    for i, (name, a) in enumerate(factors.items()):
        while len(payload) % 32:
            payload.append(0)
        offset = len(payload)
        data = np.asarray(a, dtype='<f4')
        if kind == 30:
            u = data.view(np.uint32)
            bits = ((u + 0x7FFF + ((u >> 16) & 1)) >> 16).astype('<u2')
            raw = bits.tobytes()
        else:
            raw = data.tobytes()
        directory += (
            string(list(factors)[0] if duplicate and i == 1 else name)
            + struct.pack('<I', 2)
            + struct.pack('<QQ', *reversed(a.shape))
            + struct.pack('<IQ', kind, offset)
        )
        payload.extend(raw)
    header = struct.pack('<4sIQQ', b'GGUF', 3, len(factors), 4) + meta + directory
    while len(header) % 32:
        header += b'\0'
    path.write_bytes(header + payload)


@pytest.fixture
def artifacts(tmp_path: Any) -> Any:
    native = tmp_path / 'native'
    native.mkdir()
    a = np.array([[0.123456, -0.513, 0.789, 1.001], [0.45, 0.2345, -0.2, 0.00002]], dtype=np.float32)
    b = np.arange(8, dtype=np.float32).reshape(4, 2) / 9
    state = {
        'base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight': torch.from_numpy(a),
        'base_model.model.model.layers.0.self_attn.q_proj.lora_B.weight': torch.from_numpy(b),
    }
    save_file(state, native / 'adapter_model.safetensors')
    config = {'r': 2, 'lora_alpha': 4, 'target_modules': ['q_proj'], 'bias': 'none'}
    (native / 'adapter_config.json').write_text(json.dumps(config))
    base = tmp_path / 'config.json'
    base.write_text(
        json.dumps(
            {
                'architectures': ['Cohere2ForCausalLM'],
                'num_hidden_layers': 1,
                'hidden_size': 4,
                'intermediate_size': 8,
                'num_attention_heads': 2,
                'num_key_value_heads': 1,
                'head_dim': 2,
            }
        )
    )
    factors = {'blk.0.attn_q.weight.lora_a': a, 'blk.0.attn_q.weight.lora_b': b}
    gguf = tmp_path / 'adapter.gguf'
    write_gguf(gguf, factors)
    return native, base, gguf, factors, state


def test_bf16_expected_rounding_is_distinct_from_a_mapping_defect(artifacts: Any) -> None:
    native, base, g, _, _ = artifacts
    result = audit(native, g, base)
    assert result['status'] == 'factor_pair_matches_expected_cast'
    assert all(result['checks'].values()) and result['selection_eligible'] is False
    assert result['native_scale'] == 2 and set(result['gguf_scale_by_factor_pair'].values()) == {2}
    assert max(f['relative_l2_cast_error'] for f in result['factors']) > 0


def test_f32_factors_can_match_native_without_a_base_merge(artifacts: Any) -> None:
    native, base, g, factors, _ = artifacts
    write_gguf(g, factors, kind=0)
    r = audit(native, g, base)
    assert r['status'] == 'factor_pair_matches_expected_cast'
    assert all(f['relative_l2_cast_error'] == 0 for f in r['factors'])
    assert all(x['relative_l2_update_error'] == 0 for x in r['delta_probes'])


@pytest.mark.parametrize('change', ['alpha', 'value', 'shape', 'extra_native', 'missing_native'])
def test_real_pair_mismatches_are_detected(artifacts: Any, change: Any) -> None:
    native, base, g, factors, state = artifacts
    if change == 'alpha':
        write_gguf(g, factors, alpha=8)
    elif change == 'value':
        factors['blk.0.attn_q.weight.lora_b'] = factors['blk.0.attn_q.weight.lora_b'] + 1
        write_gguf(g, factors)
    elif change == 'shape':
        factors['blk.0.attn_q.weight.lora_b'] = np.ones((4, 3), dtype=np.float32)
        write_gguf(g, factors)
    elif change == 'extra_native':
        state['unexpected.weight'] = torch.ones(1)
        save_file(state, native / 'adapter_model.safetensors')
    else:
        state.pop(next(iter(state)))
        save_file(state, native / 'adapter_model.safetensors')
    assert audit(native, g, base)['status'] == 'artifact_pair_mismatch'


def test_zero_alpha_runtime_fallback_is_not_the_native_zero_update(artifacts: Any) -> None:
    native, base, g, factors, _ = artifacts
    cfg = json.loads((native / 'adapter_config.json').read_text())
    cfg['lora_alpha'] = 0
    (native / 'adapter_config.json').write_text(json.dumps(cfg))
    write_gguf(g, factors, alpha=0)
    r = audit(native, g, base)
    assert r['checks']['runtime_scale_matches'] is False
    assert r['status'] == 'artifact_pair_mismatch'


def test_unsupported_rslora_is_not_falsely_cleared(artifacts: Any) -> None:
    native, base, g, _, _ = artifacts
    cfg = json.loads((native / 'adapter_config.json').read_text())
    cfg['use_rslora'] = True
    (native / 'adapter_config.json').write_text(json.dumps(cfg))
    assert audit(native, g, base)['status'] == 'unsupported_configuration'


def test_reader_rejects_duplicate_or_truncated_payload(artifacts: Any) -> None:
    _, _, g, factors, _ = artifacts
    write_gguf(g, factors, duplicate=True)
    with pytest.raises(ValueError, match='duplicate'):
        GGUF(g)
    write_gguf(g, factors)
    g.write_bytes(g.read_bytes()[:-2])
    with pytest.raises(ValueError, match='truncated'):
        GGUF(g)


def test_layout_and_metadata_only_is_not_value_fidelity(artifacts: Any) -> None:
    r = inventory(artifacts[2])
    assert r['tensor_count'] == 2 and r['status'] == 'structural_only_native_reference_missing' and not r['selection_eligible']
    assert native_key('base_model.model.model.layers.35.mlp.down_proj.lora_B.weight') == 'blk.35.ffn_down.weight.lora_b'


def test_exhausted_prefix_is_not_invented_as_a_divergence() -> None:
    assert first_difference([1, 2], [1, 2, 3])['kind'] == 'one_trace_ended_without_a_different_token'
    assert first_difference([1, 2], [1, 3])['offset'] == 1
    assert first_difference([1], [1])['kind'] == 'same_recorded_tokens'


def test_log_softmax_margin_and_masked_processed_scores() -> None:
    lp = log_softmax(np.array([3.0, 3.0001, -5.0]))
    r = top_margin(lp)
    assert r['top1'] == 1 and abs(r['margin'] - 0.0001) < 1e-10
    masked = top_margin(log_softmax(np.array([0.0, -np.inf])))
    assert masked['margin'] is None and masked['logprob2'] is None


def test_effects_use_same_ids_and_missing_values_are_censored() -> None:
    pb = np.array([-1.0, -2.0, -3.0])
    po = np.array([-0.5, -2.5, -3.0])
    gb = pb + 0.01
    go = po + 0.01
    r = aligned_effect(po, go, pb, gb, [0, 1, 2])
    assert r['max_abs_effect_difference'] < 1e-12
    go[1] = np.nan
    r = aligned_effect(po, go, pb, gb, [0, 1, 2])
    assert r['observed'] == 2 and r['tokens'][1]['status'] == 'missing_or_zero_probability'


def test_saved_aggregate_reports_cannot_fabricate_margins(tmp_path: Any) -> None:
    p = tmp_path / 'saved.json'
    p.write_text(
        json.dumps(
            {
                'results': [
                    {
                        'case': 'fixture',
                        'adapter_on': {'max_logprob_gap_on_shared': 0.2, 'greedy_tokens_agreeing': 12, 'of': 12},
                        'adapter_off': {'max_logprob_gap_on_shared': 0.1},
                    }
                ]
            }
        )
    )
    r = summarize([str(p)])['reports'][0]['prompts'][0]
    assert not r['divergence_observed'] and r['prefix_exhausted_without_observed_split']
    assert r['actual_divergence_margin'] is None and r['adapter_effect_difference_of_differences'] is None


def test_subtracting_max_errors_does_not_bound_adapter_effect_error() -> None:
    po, pb = np.log([0.8, 0.2]), np.log([0.6, 0.4])
    go, gb = np.log([0.78, 0.22]), np.log([0.64, 0.36])
    legacy_added = float(np.max(np.abs(go - po)) - np.max(np.abs(gb - pb)))
    assert legacy_added < 0
    assert np.argmax(po) == np.argmax(go) == 0
    result = aligned_effect(po, go, pb, gb, [0, 1])
    assert result['max_abs_effect_difference'] > 0.20


def test_actual_peft_all_linear_expansion_excludes_the_output_head() -> None:
    from peft import LoraConfig, get_peft_model
    from peft.tuners.lora.layer import LoraLayer
    from transformers import Cohere2Config, Cohere2ForCausalLM

    # Architecture/configuration fixture, no pretrained weights, forward pass or training.
    model = Cohere2ForCausalLM(
        Cohere2Config(
            vocab_size=16,
            eos_token_id=15,
            bos_token_id=0,
            pad_token_id=0,
            hidden_size=8,
            intermediate_size=16,
            num_hidden_layers=1,
            num_attention_heads=2,
            num_key_value_heads=1,
            head_dim=4,
            max_position_embeddings=64,
            sliding_window=8,
        )
    )
    model = get_peft_model(model, LoraConfig(r=2, lora_alpha=4, target_modules='all-linear', task_type='CAUSAL_LM'))
    names = [name.split('.')[-1] for name, module in model.named_modules() if isinstance(module, LoraLayer)]
    assert set(names) == {'q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'} and len(names) == 7


def test_unknown_or_ignored_activation_is_not_claimed_correct() -> None:
    from strategy_agent.evaluation.conversion_diagnose import activation

    assert activation({}, 1)['status'] == 'unknown'
    assert activation({'lora': []}, 1)['status'] == 'mismatch'
    assert activation({'lora': [{'id': 0, 'scale': 1.0}]}, 1)['status'] == 'matches'
    assert activation({'lora': [{'id': 0, 'scale': 0.0}]}, 0)['status'] == 'matches'


def test_factor_rounding_control_changes_only_values_and_restores_on_error() -> None:
    from strategy_agent.evaluation.conversion_diagnose import rounded_factor_values

    class Toy(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.base = torch.nn.Linear(2, 2, bias=False)
            self.lora_A = torch.nn.Linear(2, 2, bias=False)
            self.lora_B = torch.nn.Linear(2, 2, bias=False)

    model = Toy()
    with torch.no_grad():
        for param in model.parameters():
            param.fill_(0.10001)
    original = {n: p.detach().clone() for n, p in model.named_parameters()}
    with pytest.raises(RuntimeError, match='fixture'):
        with rounded_factor_values(model) as names:
            assert len(names) == 2
            assert torch.equal(model.base.weight, original['base.weight'])
            assert model.lora_A.weight.dtype == torch.float32
            assert not torch.equal(model.lora_A.weight, original['lora_A.weight'])
            raise RuntimeError('fixture')
    assert all(torch.equal(param, original[name]) for name, param in model.named_parameters())


def test_hf_unset_beam_count_uses_real_global_default_without_mutating_config() -> None:
    from strategy_agent.evaluation.conversion_diagnose import greedy_beam_count
    from transformers import GenerationConfig

    config = GenerationConfig(eos_token_id=3, bos_token_id=2, pad_token_id=0)
    assert config.num_beams is None
    assert greedy_beam_count(config) == 1
    assert config.num_beams is None
    assert greedy_beam_count(GenerationConfig(num_beams=1)) == 1
    with pytest.raises(ValueError, match='beam ancestry'):
        greedy_beam_count(GenerationConfig(num_beams=2))


def test_replay_cli_preserves_full_failure_evidence(tmp_path: Any, monkeypatch: Any) -> None:
    import sys

    from strategy_agent.evaluation import conversion_diagnose as module

    output = str(tmp_path / 'unexecuted-fixture.json')
    values = ['fixture', 'replay']
    for name in ('model', 'adapter', 'gguf', 'base-gguf', 'server-pid', 'rows', 'reference-report', 'url'):
        values += ['--' + name, 'synthetic-not-opened']
    values += ['--output', output]

    def refuse(args: Any) -> None:
        raise ValueError('synthetic failure after header')

    monkeypatch.setattr(module, 'replay', refuse)
    monkeypatch.setattr(sys, 'argv', values)
    with pytest.raises(ValueError, match='synthetic failure'):
        module.main()
    evidence = json.loads(open(output + '.failure.json').read())
    assert evidence['status'] == 'diagnostic_failed' and evidence['selection_eligible'] is False
    assert 'ValueError: synthetic failure after header' in evidence['traceback']


def test_explicit_greedy_overrides_inherited_sampling_and_records_requests(monkeypatch: Any) -> None:
    from transformers import GenerationConfig

    from strategy_agent.evaluation import conversion_diagnose as module

    inherited = GenerationConfig(num_beams=3, do_sample=True, temperature=0.7, top_k=40, top_p=0.9, repetition_penalty=1.2)
    effective = module.explicit_greedy_config(inherited)
    assert (effective.num_beams, effective.do_sample, effective.repetition_penalty, effective.temperature, effective.top_k, effective.top_p) == (
        1,
        False,
        1.0,
        1.0,
        0,
        1.0,
    )
    assert inherited.num_beams == 3 and inherited.temperature == 0.7
    requests = []

    def response(url: Any, path: Any, body: Any) -> Any:
        requests.append(body)
        return {'completion_probabilities': [{'id': 0, 'top_logprobs': [{'id': 0, 'logprob': 0.0}]}]}

    monkeypatch.setattr(module, 'api', response)
    module.server_trace('unused', [1], 1.0, 'matched_raw_greedy', 1)
    module.server_distribution('unused', [1], 1.0, 1, True)
    for body in requests:
        assert body['temperature'] == 0 and body['top_k'] == 1
        assert body['repeat_penalty'] == 1 and body['presence_penalty'] == body['frequency_penalty'] == 0
        assert body['post_sampling_probs'] is False
