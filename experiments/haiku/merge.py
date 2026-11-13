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
