"""Full teacher investigations by a hosted teacher (DeepSeek), through the unchanged runner. NO TRAINING.

The runner's chat is pointed at agent.backends.hosted_client.chat for this process only. Everything else is the runner's own:
the teacher prompt, tools, stages, guards, provenance manifest and output, exactly as for the Command A+ investigations
(jobs/command_a_plus.sbatch). The rows are built afterwards by the same pipeline (replay-exact, gates), then reviewed.

    DEEPSEEK_API_KEY=... HOSTED_MODEL=deepseek-v4-pro python -m aemon.teacher.hosted_investigations \
        --cases a,b,c --first-attempt 10 --workers 8 --manifest M.jsonl --output O.json

Runner flags not given here are added with the teacher's settings: prompt teacher, context 16384, 2,000 tokens per
turn, 45 turns, temperature 0. The model label, a weights hash of the label and the server settings record what ran.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

from aemon.agent import run_investigations
from aemon.agent.backends import hosted_client
from aemon.teacher.hosted_teacher import label


def main() -> None:
    if 'DEEPSEEK_API_KEY' not in os.environ:
        sys.exit('DEEPSEEK_API_KEY is not set')
    run_investigations.chat = hosted_client.chat  # this process only
    run_investigations.server_props = lambda url: {'hosted': label(), 'endpoint': hosted_client.BASE}  # no llama server to ask
    argv = sys.argv[1:]
    given = {a.split('=')[0] for a in argv if a.startswith('--')}
    defaults = {'--url': 'hosted', '--prompt': 'teacher', '--attempts': '1', '--temperature': '0', '--context': '16384',
                '--max-tokens': '2000', '--max-turns': '45', '--model-label': label(),
                '--weights-sha256': hashlib.sha256(label().encode()).hexdigest(),
                '--server-settings': json.dumps({'endpoint': hosted_client.BASE, 'hosted_model': hosted_client.model(), 'model_label': label(),
                                                 'thinking': True, 'max_tokens': int(os.environ.get('HOSTED_MAX_TOKENS', 16000)),
                                                 'repair_turns': int(os.environ.get('HOSTED_REPAIRS', 2)), 'seed': 'not supported by the API',
                                                 'strict_tool_schema': True, 'prompt_version': 'teacher (unchanged)'})}
    for flag, value in defaults.items():
        if flag not in given:
            argv += [flag, value]
    sys.argv = [sys.argv[0], *argv]
    run_investigations.main()
    print(json.dumps({'spent_usd_estimate': round(hosted_client.spent(), 4)}))


if __name__ == '__main__':
    main()
