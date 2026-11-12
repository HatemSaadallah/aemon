"""Replay recorded development runs under the masks: which recorded calls would the schema still allow?"""
import json, sys, collections
import jsonschema
from aemon.environment.cases import load_cases
from aemon.environment.tools import Investigation
from aemon.agent.tool_schemas import schema_for
rep = json.load(open(sys.argv[1])); feats = frozenset(sys.argv[2].split(','))
cases = {c.id: c for c in load_cases('all', 'development')}
st = collections.Counter()
for r in rep['records']:
    s = r['settings']; case = cases[r['case']]
    run = Investigation(case, s.get('complete_workflow', False), s.get('staged', True), s.get('quote_marks', False), s.get('reread_limit'), s.get('source_dates', False), s.get('min_assessed', 1), s.get('status_check', False))
    run.stuck_help = False; run.recovery = feats
    for c in r['calls']:
        if c.get('harness') or c.get('prefix'):
            run.call(c['name'], c['arguments']); continue
        sch = schema_for(run)
        ok = jsonschema.Draft202012Validator(sch).is_valid({'name': c['name'], 'arguments': c['arguments']})
        kind = 'accepted' if c.get('accepted') else c.get('category')
        st[(kind, 'allowed' if ok else 'BLOCKED')] += 1
        res = run.call(c['name'], c['arguments'])
        if ('error' in res) == bool(c.get('accepted')):
            st['replay mismatch'] += 1
for k, v in sorted(st.items(), key=str): print(v, k)
