#!/bin/bash
# Version 4, recovery distillation, steps 1 to 3 (docs/DECISIONS.md, "2026-11-12 01:10: version 4, recovery
# distillation for the reasoner"). Unattended, from this laptop, over the one SSH master only:
#   1. harvest: dig then reason without the status check (v1 for brief, frame and evidence, v3 after) on the training
#      cases, one attempt, in four eval_switch jobs of 48 cases (about an hour each on a 4g.40gb slice);
#   2. states: loops that start in the stages version 3 writes, built here from the fetched reports;
#   3. teacher: Command A+ answers each state (command_a_plus*.sbatch queue mode, batches of 20 states, MIN_KEPT=0 so
#      low acceptance does not stop a worker), then `corrections rows` builds rows/v4_corrections.jsonl, copied to
#      ~/lexsi/rows/ on the cluster.
# Training (jobs/train_v4.sbatch) is NOT submitted here. Every step writes a marker under state/, so rerunning this
# script resumes where it stopped. Job state is read at most every 5 minutes, through scripts/cluster/cluster.py.
# Usage: nohup experiments/v4_recovery/driver.sh REVISION >> experiments/v4_recovery/driver.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/../.."
D=experiments/v4_recovery
S=$D/state
mkdir -p $S $D/harvest $D/teacher $D/batches
[ -s $S/REVISION ] || { [ -n "${1:-}" ] || { echo "give the code revision"; exit 2; }; echo "$1" > $S/REVISION; }
REV=$(cat $S/REVISION)
R=CLUSTER_ACCOUNT@CLUSTER_HOST
L=/home/CLUSTER_ACCOUNT/lexsi
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
ROUTE=default=1,brief=0,frame=0,evidence=0
# The stage names (aemon.environment.stages; the 'stage' field of each call) after evidence, so the ones version 3 writes
# under this route. aemon.agent.records.STAGES lists tool names, not stages. status and status_reading are absent
# without the status check.
STAGES="theories assessment challenge challenge_reading test position new_evidence update conclude"
QUEUE=$L/queue/recovery_v4.txt
BATCH=20
log() { echo "$(date '+%F %T') $*"; }
remote() {  # one command over the master, through cluster.py (stdin closed, so a read loop keeps its input); if the master is gone, wait 20 minutes and try again
  local out
  until out=$(.venv/bin/python -c "import sys; sys.path.insert(0, 'scripts/cluster'); import cluster; print(cluster.remote(sys.argv[1]), end='')" "$1" 2>$S/remote.err </dev/null); do
    log "cluster unreachable: $(tail -1 $S/remote.err | cut -c1-200); waiting 20 minutes"; sleep 1200
  done
  printf '%s' "$out"
}
live() { remote "squeue -u \$USER -h -o '%i %j %T %R'"; }  # my queued and running jobs: id name state reason
submit() {  # script, then KEY=VALUE pairs; prints the job id
  local out
  for attempt in 1 2 3 4 5 6; do
    out=$(python3 scripts/cluster/cluster.py submit "$@" 2>&1 </dev/null) && { echo "$out" | grep -o 'job [0-9]*' | cut -d' ' -f2; return 0; }
    log "submit failed ($attempt): $(echo "$out" | tail -1 | cut -c1-200)" >&2; sleep 600
  done
  return 1
}

log "driver start, code $REV"
# Code copy, as earlier jobs did (experiments/hosted_investigations/chain_v3.sh)
if [ ! -e $S/code_uploaded ]; then
  git archive $REV src jobs scripts data/dossier | gzip | $SSHO $R "mkdir -p ~/lexsi/code_$REV && tar -xz -C ~/lexsi/code_$REV" || { log "code upload failed"; exit 1; }
  touch $S/code_uploaded; log "code $REV copied to $L/code_$REV"
fi

# 1. Harvest
if [ ! -s $D/harvest_cases.json ]; then
  PYTHONPATH=src .venv/bin/python - $D/harvest_cases.json <<'PY' || { log "harvest case check failed"; exit 1; }
import json, sys
from aemon.environment.cases import load_cases
from aemon.data.splits import is_validation
company = lambda case: case.split('-')[0]
dev = [c.id for c in load_cases()]
train = [c for c in dev if not is_validation(c)]
final = {company(c.id) for c in load_cases(split='heldout')}
second = {company(c.id) for c in load_cases(split='heldout2')}
clash = sorted({company(c) for c in train} & (final | second))
assert not clash, clash
chunks = [train[i::4] for i in range(4)]  # interleaved, so the four jobs take about as long
json.dump({'cases': len(train), 'companies': len({company(c) for c in train}), 'development_cases': len(dev),
           'excluded_validation_cases': len(dev) - len(train), 'final_test_companies': sorted(final),
           'test_set_2_companies': sorted(second), 'overlap_with_either_test_set': clash, 'chunks': chunks}, open(sys.argv[1], 'w'), indent=1)
print(f'{len(train)} training cases from {len({company(c) for c in train})} companies; none from a validation, final-test or test-set-2 company')
PY
fi
for i in 1 2 3 4; do
  [ -s $S/harvest_$i.job ] && continue
  until [ "$(live | grep -c .)" -lt 4 ]; do sleep 300; done
  CASES=$(.venv/bin/python -c "import json; print(','.join(json.load(open('$D/harvest_cases.json'))['chunks'][$i - 1]))")
  J=$(submit jobs/eval_switch.sbatch --env NAME=v4_harvest_$i ROUTE=$ROUTE CASES=$CASES ATTEMPTS=1 SPLIT=development REVISION=$REV) || { log "harvest $i not submitted"; exit 1; }
  echo $J > $S/harvest_$i.job; log "harvest $i submitted as job $J ($(echo $CASES | tr ',' '\n' | wc -l) cases)"
  sleep 30
done
until [ -e $S/harvest_done ]; do
  sleep 300
  Q=$(live)
  waiting=0
  for i in 1 2 3 4; do
    J=$(cat $S/harvest_$i.job)
    echo "$Q" | grep -q "^$J " && { waiting=1; continue; }
    [ -s $D/harvest/v4_harvest_$i.json ] && continue
    rsync -az -e "$SSHO" $R:lexsi/runs/eval/v4_harvest_$i.json $R:lexsi/runs/eval/v4_harvest_$i.log $D/harvest/ 2>/dev/null
    if [ -s $D/harvest/v4_harvest_$i.json ]; then
      log "harvest $i: $(.venv/bin/python -c "import json; s=json.load(open('$D/harvest/v4_harvest_$i.json'))['summary']; print(json.dumps({k: s[k] for k in ('episodes', 'finished', 'stop_reasons', 'refused_calls')}))")"
    elif [ ! -e $S/harvest_$i.retried ]; then  # one resubmission of a chunk that ended without a report
      log "harvest $i (job $J) ended without a report: $(remote "tail -3 $L/eval-switch-$J.out 2>&1; true" | tr '\n' ' ' | cut -c1-300); resubmitting once"
      CASES=$(.venv/bin/python -c "import json; print(','.join(json.load(open('$D/harvest_cases.json'))['chunks'][$i - 1]))")
      J=$(submit jobs/eval_switch.sbatch --env NAME=v4_harvest_$i ROUTE=$ROUTE CASES=$CASES ATTEMPTS=1 SPLIT=development REVISION=$REV) || exit 1
      echo $J > $S/harvest_$i.job; touch $S/harvest_$i.retried; waiting=1; log "harvest $i resubmitted as job $J"
    else
      log "harvest $i failed twice; stopping"; exit 1
    fi
  done
  [ $waiting = 0 ] && touch $S/harvest_done
done
log "harvest done: $(ls $D/harvest/*.json | wc -l) reports"

# 2. States
if [ ! -s $D/states.json ]; then
  IDENTITY=$(.venv/bin/python -c "
import json
print(json.dumps({'system': 'dig then reason without the status check', 'route': '$ROUTE', 'route_meaning': 'adapter 1 (version 3) everywhere except brief, frame and evidence, which adapter 0 (version 1) writes',
  'adapters': {'0': {'name': 'version 1', 'file': 'runs/eval/final_test_trained_adapter.gguf', 'sha256': '41794b5756b9e0f87c58dd14e451756d15c897d595886dee9921181298fdb9d1'},
               '1': {'name': 'version 3', 'file': 'runs/eval/final_test_v3_adapter.gguf', 'sha256': 'ea9193807fe9d5132878021bdf73de40ee84e2486f6688db9b3c3e29e04e1443'}},
  'harvest_jobs': [open('$S/harvest_%d.job' % i).read().strip() for i in (1, 2, 3, 4)], 'code_revision': '$REV'}))")
  PYTHONPATH=src .venv/bin/python -W ignore -m aemon.teacher.corrections states --reports $D/harvest/v4_harvest_{1,2,3,4}.json --stages $STAGES \
    --student-identity "$IDENTITY" --output $D/states.json > $D/states.log 2>&1 || { log "states failed: $(tail -3 $D/states.log)"; exit 1; }
  log "states: $(tail -1 $D/states.log) $(.venv/bin/python -c "import json, collections; print(dict(collections.Counter(s['refused_next'].get('stage') for s in json.load(open('$D/states.json')))))")"
fi
if [ ! -e $S/queue_uploaded ]; then
  .venv/bin/python - $D/states.json $D/batches $BATCH $L/queue/recovery_v4 > $D/batches/queue.txt <<'PY'
import json, sys
from pathlib import Path
states, folder, size, remote = json.load(open(sys.argv[1])), Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
for n in range(0, len(states), size):
    name = f'correct_v4_{n // size:02d}'
    (folder / f'{name}.json').write_text(json.dumps(states[n:n + size]))
    print(f'{name} {remote}/{name}.json 0 0')
PY
  [ -s $D/batches/queue.txt ] || { log "no states, nothing to ask"; exit 1; }
  $SSHO $R "mkdir -p $L/queue/recovery_v4" && rsync -az --partial -e "$SSHO" $D/batches/correct_v4_*.json $R:lexsi/queue/recovery_v4/ \
    && $SSHO $R "test ! -e $QUEUE && cat > $QUEUE" < $D/batches/queue.txt || { log "queue upload failed"; exit 1; }
  touch $S/queue_uploaded; log "queue: $(wc -l < $D/batches/queue.txt) batches of up to $BATCH states in $QUEUE"
fi

# 3. Teacher
variant() {  # the 80 GB job if its slice can start within the hour or no later than a 40 GB slice, else the 40 GB job
  remote "cd $L && for g in 7g.80gb:1,200G 4g.40gb:1,400G; do sbatch --test-only --partition=stud --qos=stud --account=CLUSTER_ACCOUNT --gres=gpu:\${g%,*} --cpus-per-task=6 --mem=\${g#*,} --time=23:30:00 --exclude=gnode04 --wrap true 2>&1 | grep -o 'start at [0-9T:-]*' | cut -c10- ; done; true" \
    | .venv/bin/python -c "
import sys, datetime
t = [datetime.datetime.fromisoformat(x.strip()) for x in sys.stdin if x.strip()]
soon = datetime.datetime.now() + datetime.timedelta(hours=1)
print('80' if len(t) == 2 and (t[0] <= soon or t[0] <= t[1]) else '40')"
}
touch $S/teacher_jobs.txt
until [ -e $S/teacher_done ]; do
  OUT=$(remote "squeue -u \$USER -h -o '%i %j %T %R'; echo @@; cat $QUEUE 2>/dev/null | wc -l; echo @@; ls $L/runs/teacher | grep -E '^v4t[0-9]+_correct_v4_[0-9]+\.json\$' || true")
  Q=$(echo "$OUT" | awk '/^@@/{n++; next} n==0'); LEFT=$(echo "$OUT" | awk '/^@@/{n++; next} n==1'); DONE=$(echo "$OUT" | awk '/^@@/{n++; next} n==2')
  MISSING=$(while read b _; do echo "$DONE" | grep -q "_${b}.json$" || echo $b; done < $D/batches/queue.txt)
  ACTIVE=$(while read j _; do echo "$Q" | grep "^$j " ; done < $S/teacher_jobs.txt)
  NA=$(echo "$ACTIVE" | grep -c .)
  if [ -z "$MISSING" ]; then
    while read j _; do echo "$Q" | grep -q "^$j " && remote "scancel $j || true" && log "cancelled idle teacher $j"; done < $S/teacher_jobs.txt
    touch $S/teacher_done; break
  fi
  if [ "$NA" -eq 0 ] && [ "${LEFT:-0}" -eq 0 ]; then  # nothing queued, nothing running, batches missing: a worker died mid-batch
    ROUNDS=$(cat $S/requeued 2>/dev/null || echo 0)
    [ "$ROUNDS" -ge 2 ] && { log "batches still missing after two requeues: $(echo $MISSING); stopping"; exit 1; }
    echo $((ROUNDS + 1)) > $S/requeued
    grep -E "^($(echo $MISSING | tr ' ' '|')) " $D/batches/queue.txt | $SSHO $R "cat >> $QUEUE"; LEFT=$(echo "$MISSING" | wc -w)
    log "requeued $(echo $MISSING)"
  fi
  WANT=$([ "${LEFT:-0}" -ge 3 ] && echo 2 || echo 1)
  if [ "$NA" -lt "$WANT" ] && [ "${LEFT:-0}" -gt 0 ] && [ "$(echo "$Q" | grep -c .)" -lt 4 ]; then
    N=$(( $(grep -c . $S/teacher_jobs.txt) + 1 ))
    if [ $N -le 8 ]; then
      V=$(variant); [ $V = 80 ] && JOB=jobs/command_a_plus.sbatch || JOB=jobs/command_a_plus_40gb.sbatch
      J=$(submit $JOB --env NAME=v4t$N QUEUE=$QUEUE REBUILD=1 HOURS=20 MIN_KEPT=0 REVISION=$REV) && { echo "$J $V" >> $S/teacher_jobs.txt; log "teacher worker v4t$N submitted as job $J ($V GB slice); $LEFT batches queued"; }
    else
      [ "$NA" -eq 0 ] && { log "eight teacher workers used and batches remain: $(echo $MISSING); stopping"; exit 1; }
    fi
  fi
  [ -n "$ACTIVE" ] && log "teacher: $(echo "$ACTIVE" | tr '\n' ';') $LEFT queued, $(echo "$MISSING" | wc -w) batches without output"
  sleep 600
done
log "teacher done"

# Corrections and rows
rsync -az -e "$SSHO" --include='v4t*_correct_v4_*' --include='v4t*.server.log' --include='v4t*.build.log' --exclude='*' $R:lexsi/runs/teacher/ $D/teacher/
rsync -az -e "$SSHO" $R:lexsi/runs/teacher/provenance.jsonl $D/teacher/provenance.jsonl
.venv/bin/python - $D <<'PY' > $D/corrections_summary.json || { log "merge failed"; exit 1; }
import collections, glob, json, sys
from pathlib import Path
d = Path(sys.argv[1])
batches = [line.split()[0] for line in (d / 'batches' / 'queue.txt').read_text().splitlines()]
merged, seen = [], set()
for b in batches:
    for f in sorted(glob.glob(str(d / 'teacher' / f'v4t*_{b}.json'))):
        for item in json.load(open(f)):
            key = (item['state']['student_run'], item['state']['turn'])
            if key not in seen:
                seen.add(key); merged.append(item)
(d / 'corrections.json').write_text(json.dumps(merged, indent=1))
states = json.load(open(d / 'states.json'))
decisions = collections.Counter(x['decision'] for x in merged)
print(json.dumps({'states': len(states), 'answered': len(merged), 'kept': sum(bool(x.get('kept')) for x in merged),
                  'kept_by_stage': dict(collections.Counter(x['kept']['stage'] for x in merged if x.get('kept'))),
                  'decisions': dict(decisions.most_common())}, indent=1))
PY
PYTHONPATH=src .venv/bin/python -W ignore -m aemon.teacher.corrections rows --corrections $D/corrections.json --manifest $D/teacher/provenance.jsonl \
  --output rows/v4_corrections.jsonl > $D/rows.log 2>&1 || { log "rows failed: $(tail -3 $D/rows.log)"; exit 1; }
log "corrections: $(.venv/bin/python -c "import json; s=json.load(open('$D/corrections_summary.json')); print(json.dumps({k: s[k] for k in ('states', 'answered', 'kept')}))"); rows $(tail -1 $D/rows.log)"
rsync -az -e "$SSHO" rows/v4_corrections.jsonl $R:lexsi/rows/v4_corrections.jsonl
log "rows/v4_corrections.jsonl local $(sha256sum rows/v4_corrections.jsonl | cut -c1-16), cluster $($SSHO $R "sha256sum $L/rows/v4_corrections.jsonl" | cut -c1-16)"
log "step 3 done; training (jobs/train_v4.sbatch) is not submitted"
