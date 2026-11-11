"""Final test breakdown by evidence kind, per judge and mean of judges, with the frozen bootstrap. Evaluation only."""
import json, sys, collections, statistics
from aemon.evaluation.judging.report import episode_scores, load, bootstrap
key = [json.loads(l) for l in open(sys.argv[1])]
judges = dict(a.split('=', 1) for a in sys.argv[2:])
def kind(c):
    return 'base' if c.endswith('-base') else 'irrelevant' if 'irrelevant' in c else 'undermines' if 'undermines' in c else 'supports'
scores = {}
for j, path in judges.items():
    pred = load(path)
    scores[j] = {}
    for i, k in enumerate(key):
        p = pred.get(k['packet_id'])
        if p and 'judgment' in p:
            scores[j][i] = episode_scores(p['judgment'])[0]
both = set(scores['claude']) & set(scores['codex'])
scores['mean'] = {i: (scores['claude'][i] + scores['codex'][i]) / 2 for i in both}
out = {}
for j, s in scores.items():
    cell = collections.defaultdict(dict)
    for i, k in enumerate(key):
        if i in s:
            cell[(k['case'], k['attempt'])][k['arm']] = s[i]
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for (c, a), v in cell.items():
        if 'trained' in v and 'base' in v:
            by[kind(c)][c].append(v['trained'] - v['base'])
    out[j] = {kd: {'pairs': sum(len(x) for x in pairs.values()), 'mean_and_95_interval': bootstrap(pairs)} for kd, pairs in sorted(by.items())}
print(json.dumps(out, indent=1))
