"""Read-only Cohere2 LoRA GGUF/native-factor audit. No training, merging, or model inference."""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any

import numpy as np

Json = dict[str, Any]
MODULES = {
    'q_proj': 'attn_q',
    'k_proj': 'attn_k',
    'v_proj': 'attn_v',
    'o_proj': 'attn_output',
    'gate_proj': 'ffn_gate',
    'up_proj': 'ffn_up',
    'down_proj': 'ffn_down',
}
FORMATS = {0: '<B', 1: '<b', 2: '<H', 3: '<h', 4: '<I', 5: '<i', 6: '<f', 7: '<?', 10: '<Q', 11: '<q', 12: '<d'}


def sha(path: str | Path) -> str:
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


class GGUF:
    """Unquantized F32/F16/BF16 adapter tensors. GGUF directory dimensions are opposite NumPy order."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        with self.path.open('rb') as f:

            def exact(n: int) -> bytes:
                data = f.read(n)
                if len(data) != n:
                    raise ValueError('truncated GGUF')
                return data

            def number(fmt: str) -> Any:
                return struct.unpack(fmt, exact(struct.calcsize(fmt)))[0]

            def text() -> str:
                n = number('<Q')
                if n > self.path.stat().st_size:
                    raise ValueError('invalid GGUF string length')
                return exact(n).decode('utf8')

            def value(kind: int) -> Any:
                if kind == 8:
                    return text()
                if kind == 9:
                    ty, n = number('<I'), number('<Q')
                    return [value(ty) for _ in range(n)]
                if kind not in FORMATS:
                    raise ValueError('unsupported GGUF metadata type')
                return number(FORMATS[kind])

            magic, version, nt, nk = struct.unpack('<4sIQQ', exact(24))
            if magic != b'GGUF' or version != 3:
                raise ValueError('requires little-endian GGUFv3')
            self.meta: Json = {}
            for _ in range(nk):
                key = text()
                if key in self.meta:
                    raise ValueError('duplicate metadata key')
                self.meta[key] = value(number('<I'))
            self.tensors: Json = {}
            for _ in range(nt):
                name = text()
                ndim = number('<I')
                if ndim < 1 or ndim > 4:
                    raise ValueError('invalid tensor dimensions')
                shape = [number('<Q') for _ in range(ndim)]
                kind, offset = number('<I'), number('<Q')
                if name in self.tensors or any(d <= 0 for d in shape) or kind not in (0, 1, 30):
                    raise ValueError('duplicate/invalid/non-unquantized adapter tensor')
                self.tensors[name] = {'shape': list(reversed(shape)), 'ggml_shape': shape, 'type': kind, 'offset': offset}
            alignment = self.meta.get('general.alignment', 32)
            if type(alignment) is not int or alignment <= 0 or alignment & (alignment - 1):
                raise ValueError('invalid GGUF alignment')
            self.start = (f.tell() + alignment - 1) // alignment * alignment
        end = self.start
        for item in sorted(self.tensors.values(), key=lambda x: x['offset']):
            at = self.start + item['offset']
            size = math.prod(item['shape']) * (4 if item['type'] == 0 else 2)
            if at < end or at + size > self.path.stat().st_size:
                raise ValueError('overlapping or truncated tensor payload')
            end = at + size
        self.data = np.memmap(self.path, dtype=np.uint8, mode='r')

    def tensor(self, name: str) -> np.ndarray:
        item = self.tensors[name]
        n = math.prod(item['shape'])
        at = self.start + item['offset']
        if item['type'] == 30:
            values = (np.frombuffer(self.data, dtype='<u2', count=n, offset=at).astype(np.uint32) << 16).view(np.float32)
        else:
            values = np.frombuffer(self.data, dtype='<f4' if item['type'] == 0 else '<f2', count=n, offset=at).astype(np.float32)
        return values.reshape(item['shape'])


def inventory(path: str | Path) -> Json:
    gguf = GGUF(path)
    entries = []
    for name, item in sorted(gguf.tensors.items()):
        a = gguf.tensor(name)
        entries.append(
            {
                'name': name,
                **item,
                'finite': bool(np.isfinite(a).all()),
                'nonzero_values': int(np.count_nonzero(a)),
                'l2': float(np.linalg.norm(a.astype(np.float64))),
                'values_f32_sha256': hashlib.sha256(a.astype('<f4').tobytes()).hexdigest(),
            }
        )
    payload = {
        'architecture': gguf.meta.get('general.architecture'),
        'alpha': gguf.meta.get('adapter.lora.alpha'),
        'tensors': {t['name']: {k: t[k] for k in ('shape', 'type', 'values_f32_sha256')} for t in entries},
    }
    return {
        'tensor_payload_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
        'artifact': Path(path).name,
        'sha256': sha(path),
        'bytes': Path(path).stat().st_size,
        'metadata': gguf.meta,
        'tensor_count': len(entries),
        'tensors': entries,
        'status': 'structural_only_native_reference_missing',
        'selection_eligible': False,
    }


def native_key(name: str) -> str:
    match = re.fullmatch(r'(?:base_model\.model\.)?model\.layers\.(\d+)\.(?:self_attn|mlp)\.(\w+)\.lora_([AB])(?:\.default)?\.weight', name)
    if not match or match[2] not in MODULES:
        raise ValueError(f'unsupported native adapter tensor: {name}')
    return f'blk.{match[1]}.{MODULES[match[2]]}.weight.lora_{match[3].lower()}'


def audit(adapter: str | Path, gguf_path: str | Path, base_config: str | Path) -> Json:
    import torch
    from safetensors.torch import load_file

    root = Path(adapter)
    config = json.loads((root / 'adapter_config.json').read_text())
    base = json.loads(Path(base_config).read_text())
    g = GGUF(gguf_path)
    result = inventory(gguf_path)
    config_summary = {
        k: config.get(k)
        for k in (
            'r',
            'lora_alpha',
            'target_modules',
            'use_rslora',
            'use_dora',
            'fan_in_fan_out',
            'rank_pattern',
            'alpha_pattern',
            'modules_to_save',
            'layers_to_transform',
            'bias',
        )
    }
    result.update(
        {
            'adapter_config_sha256': sha(root / 'adapter_config.json'),
            'base_config_sha256': sha(base_config),
            'native_config': config_summary,
            'checks': {},
            'factors': [],
            'delta_probes': [],
            'source_tensor_files': {},
        }
    )
    unsupported = []
    if base.get('architectures') != ['Cohere2ForCausalLM'] or g.meta.get('general.architecture') != 'cohere2':
        unsupported.append('requires verified Cohere2 identity mapping')
    for key in ('use_rslora', 'use_dora', 'fan_in_fan_out', 'rank_pattern', 'alpha_pattern', 'modules_to_save', 'layers_to_transform', 'target_parameters'):
        if config.get(key):
            unsupported.append(key)
    if config.get('bias', 'none') != 'none':
        unsupported.append('trained bias')
    targets = config.get('target_modules')
    targets = list(MODULES) if targets == 'all-linear' else targets
    if not isinstance(targets, list) or not targets or any(t not in MODULES for t in targets):
        unsupported.append('target modules')
    if unsupported:
        result.update(status='unsupported_configuration', unsupported=unsupported)
        return result
    native = {}
    for file in sorted(root.glob('adapter_model*.safetensors')):
        result['source_tensor_files'][file.name] = sha(file)
        for name, tensor in load_file(file, device='cpu').items():
            try:
                mapped = native_key(name)
            except ValueError:
                result.setdefault('unmapped_native_keys', []).append(name)
                continue
            if mapped in native:
                raise ValueError('duplicate mapped native tensor')
            native[mapped] = tensor
    if not native:
        raise ValueError('native safetensors missing; never guess factor fidelity')
    rank = int(config['r'])
    alpha = float(config['lora_alpha'])
    layers = int(base['num_hidden_layers'])
    expected = {f'blk.{i}.{MODULES[t]}.weight.lora_{s}' for i in range(layers) for t in targets for s in ('a', 'b')}
    checks = result['checks']
    checks['native_coverage'] = set(native) == expected and not result.get('unmapped_native_keys')
    checks['gguf_coverage'] = set(g.tensors) == expected
    checks['alpha_metadata_matches_expected_f32'] = g.meta.get('adapter.lora.alpha') == float(np.float32(alpha))
    checks['runtime_scale_matches'] = all(
        (float(g.meta.get('adapter.lora.alpha', 0)) / g.tensor(n).shape[0] if g.meta.get('adapter.lora.alpha', 0) else 1.0) == float(np.float32(alpha)) / rank
        for n in g.tensors
        if n.endswith('.lora_a')
    )
    checks['adapter_type'] = g.meta.get('adapter.type') == 'lora' and g.meta.get('general.type') == 'adapter'
    shapes = {}
    hidden = int(base['hidden_size'])
    intermediate = int(base['intermediate_size'])
    heads = int(base['num_attention_heads'])
    kv_heads = int(base.get('num_key_value_heads', heads))
    head = int(base.get('head_dim') or hidden // heads)
    for target in targets:
        out, inp = (
            (heads * head, hidden)
            if target == 'q_proj'
            else (kv_heads * head, hidden)
            if target in ('k_proj', 'v_proj')
            else (hidden, heads * head)
            if target == 'o_proj'
            else (hidden, intermediate)
            if target == 'down_proj'
            else (intermediate, hidden)
        )
        shapes[MODULES[target]] = (out, inp)
    for name in sorted(expected & native.keys() & g.tensors.keys()):
        source = native[name].to(torch.float32).numpy()
        actual = g.tensor(name)
        kind = g.tensors[name]['type']
        dtype = {0: torch.float32, 1: torch.float16, 30: torch.bfloat16}[kind]
        cast = native[name].to(dtype).to(torch.float32).numpy()
        module = name.split('.')[2]
        out, inp = shapes[module]
        expected_shape = (rank, inp) if name.endswith('lora_a') else (out, rank)
        same_shape = source.shape == actual.shape == expected_shape
        exact = bool(same_shape and np.array_equal(actual, cast))
        error = (
            float(np.linalg.norm(actual.astype(np.float64) - source.astype(np.float64)) / max(np.linalg.norm(source.astype(np.float64)), 1e-30))
            if same_shape
            else None
        )
        result['factors'].append(
            {
                'name': name,
                'shape_matches': same_shape,
                'native_dtype': str(native[name].dtype),
                'gguf_type': kind,
                'matches_expected_cast': exact,
                'relative_l2_cast_error': error,
            }
        )
    checks['all_shapes_match'] = len(result['factors']) == len(expected) and all(x['shape_matches'] for x in result['factors'])
    checks['all_factors_match_expected_cast'] = len(result['factors']) == len(expected) and all(x['matches_expected_cast'] for x in result['factors'])
    checks['all_factors_finite'] = all(t['finite'] for t in result['tensors']) and all(bool(torch.isfinite(t).all()) for t in native.values())
    if checks['all_shapes_match'] and checks['all_factors_finite']:
        rng = np.random.default_rng(20261105)
        for i in range(layers):
            for target in targets:
                prefix = f'blk.{i}.{MODULES[target]}.weight'
                a, b = prefix + '.lora_a', prefix + '.lora_b'
                x = rng.choice([-1.0, 1.0], size=(native[a].shape[1], 4))
                reference = (alpha / rank) * (native[b].double().numpy() @ (native[a].double().numpy() @ x))
                actual = (float(g.meta.get('adapter.lora.alpha', 0)) / g.tensor(a).shape[0] if g.meta.get('adapter.lora.alpha', 0) else 1.0) * (
                    g.tensor(b).astype(np.float64) @ (g.tensor(a).astype(np.float64) @ x)
                )
                result['delta_probes'].append(
                    {'module': prefix, 'relative_l2_update_error': float(np.linalg.norm(actual - reference) / max(np.linalg.norm(reference), 1e-30))}
                )
    result['native_scale'] = alpha / rank
    result['gguf_scale_by_factor_pair'] = {
        n.removesuffix('.lora_a'): (float(g.meta.get('adapter.lora.alpha', 0)) / g.tensor(n).shape[0] if g.meta.get('adapter.lora.alpha', 0) else 1.0)
        for n in g.tensors
        if n.endswith('.lora_a')
    }
    result['status'] = 'factor_pair_matches_expected_cast' if all(checks.values()) else 'artifact_pair_mismatch'
    result['limitation'] = (
        'Known Cohere2 identity mapping; verify actual converter/runtime revision. Tensor identity and fixed-vector updates do not establish end-to-end or business quality.'
    )
    return result
