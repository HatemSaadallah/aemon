#!/bin/bash
# Rerun only the Haiku episodes the harness lost to Anthropic API errors (HTTP 500 after the SDK's retries), one
# episode per file, two at a time, then merge them into NAME_merged.json. A server error is not the model's behaviour.
# Usage: rerun.sh NAME SPLIT
set -uo pipefail
cd "$(dirname "$0")/../.."
NAME=$1 SPLIT=$2 O=experiments/haiku
.venv/bin/python -c "
import json
for e in json.load(open('$O/$NAME.json')).get('harness_errors') or []:
    print(e['case'], e['attempt'])" > $O/${NAME}_lost.txt
echo "$NAME: $(grep -c . $O/${NAME}_lost.txt) lost episodes"
mkdir -p $O/${NAME}_reruns
xargs -P 2 -L 1 bash -c '.venv/bin/python -m aemon.agent.run_investigations --backend claude --claude-model claude-haiku-5-5 \
  --prompt staged --split '$SPLIT' --cases $0 --first-attempt $1 --attempts 1 --run-cap-usd 1 \
  --output '$O'/'$NAME'_reruns/$0_$1.json > '$O'/'$NAME'_reruns/$0_$1.log 2>&1' < $O/${NAME}_lost.txt
.venv/bin/python - $O $NAME <<'PY'
import glob, json, sys
O, name = sys.argv[1:]
d = json.load(open(f'{O}/{name}.json'))
lost = {(e['case'], e['attempt']) for e in d.get('harness_errors') or []}
reruns, still = [], []
for f in sorted(glob.glob(f'{O}/{name}_reruns/*.json')):
    r = json.load(open(f))
    reruns += r['records']
    still += r.get('harness_errors') or []
got = {(r['case'], r['attempt']) for r in reruns}
assert got <= lost, got - lost
still = [e for e in still if (e['case'], e['attempt']) not in got]  # a later try of the same episode resolves it
d['records'] = sorted(d['records'] + reruns, key=lambda r: (r['case'], r['attempt']))
d['harness_errors'] = still
d['reruns'] = {'why': 'episodes lost to Anthropic API errors (HTTP 500 after retries), rerun once each',
               'episodes': sorted([list(x) for x in got]), 'files': f'{O}/{name}_reruns/'}
json.dump(d, open(f'{O}/{name}_merged.json', 'w'), indent=1)
print(json.dumps({'name': name, 'records': len(d['records']), 'rerun': len(got), 'still_lost': len(still)}))
PY
