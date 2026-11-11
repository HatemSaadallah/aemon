"""Read Tiny Aya's architecture from the ungated GGUF header, pinned to a revision.

Reads only the first 256 KB by HTTP range request, so nothing is stored and the gated
weights are not touched. Shapes only: this does not verify the real config.json, the
attention implementation, or the tokenizer, which are behind the gate.
"""
import json
import struct
import urllib.request
from pathlib import Path

REPO = 'CohereLabs/tiny-aya-global-GGUF'
FILE = 'tiny-aya-global-q4_k_m.gguf'
FORMATS = {0: '<B', 1: '<b', 2: '<H', 3: '<h', 4: '<I', 5: '<i', 6: '<f', 7: '<?', 10: '<Q', 11: '<q', 12: '<d'}


def revision(repo):
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{repo}', timeout=30) as r:
        return json.load(r)['sha']


def main():
    sha = revision(REPO)
    url = f'https://huggingface.co/{REPO}/resolve/{sha}/{FILE}'
    req = urllib.request.Request(url, headers={'Range': 'bytes=0-262143'})
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read()
    if b[:4] != b'GGUF':
        raise SystemExit('not a GGUF file')
    _, _, count = struct.unpack('<IQQ', b[4:24])

    def text(i):
        n = struct.unpack('<Q', b[i:i + 8])[0]
        return b[i + 8:i + 8 + n].decode('utf8', 'replace'), i + 8 + n

    def value(kind, i):
        if kind == 8:
            return text(i)
        if kind == 9:
            element, n = struct.unpack('<IQ', b[i:i + 12])
            i += 12
            items = []
            for _ in range(n):
                v, i = value(element, i)
                items.append(v)
            return items[:3], i
        size = struct.calcsize(FORMATS[kind])
        return struct.unpack(FORMATS[kind], b[i:i + size])[0], i + size

    meta, i = {}, 24
    for _ in range(count):
        key, i = text(i)
        kind = struct.unpack('<I', b[i:i + 4])[0]
        i += 4
        if key.startswith('tokenizer.'):
            break
        meta[key], i = value(kind, i)
    out = {'source': url, 'repo': REPO, 'revision': sha, 'file': FILE,
           'gated_base_repo_revision': revision('CohereLabs/tiny-aya-global'), 'metadata': meta}
    Path(__file__).with_name('gguf_header.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: out[k] for k in ('revision', 'gated_base_repo_revision')}))
    print({k.split('.', 1)[1]: v for k, v in meta.items() if k.startswith('cohere2.') and 'rope' not in k})


if __name__ == '__main__':
    main()
