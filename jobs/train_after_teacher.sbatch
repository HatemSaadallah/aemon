#!/bin/bash
#SBATCH --job-name=train-after
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH --output=%x-%j.out
# Runs unattended after the teacher queue: builds rows from every teacher stage that finished, then the overfit gate on 10
# rows, then a first feasibility training run only if at least 8 of 10 are reproduced. Development only, never a final result.
set -euo pipefail
L=$HOME/lexsi
export PYTHONPATH=$L/code_${REVISION:-unset}/src  # the package, from this job's own copy of the code
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh  # a job submitted with env -i has no module function
module load cuda/12.8
cd $L/code_$REVISION
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CODE_REVISION=$REVISION
mkdir -p $L/rows
# REPORT_LIST, a file of report paths, freezes a dataset; otherwise every finished stage report is used
if [ -n "${REPORT_LIST:-}" ]; then REPORTS=$(cat $REPORT_LIST); else
REPORTS=$(ls $L/runs/teacher/${PREFIX:-cap}[0-9]_*.json 2>/dev/null | grep -v episodes | grep -v '_correct' || true)  # corrections are not episodes
fi
echo "teacher stage reports: $(echo $REPORTS | wc -w)"
[ -n "$REPORTS" ] || { echo "no teacher stages finished, nothing to train on"; exit 1; }
ROWS=$L/rows/${NAME}.jsonl
rm -f $ROWS $L/rows/${NAME}.decisions.json
# ROW_PROMPT and COMPACT=1 build the rows as the student will run: compact keeps late stages inside the length limit
$L/env/bin/python -W ignore -m strategy_agent.pipeline.rows --reports $REPORTS --manifest $L/runs/teacher/provenance.jsonl --prompt ${ROW_PROMPT:-staged} ${COMPACT:+--compact} --output $ROWS
N=$(wc -l < $ROWS)
echo "rows built: $N"
# Recovery corrections (docs/RECOVERY_PILOT.md): kept ones become rows only if the manifest holds that exact reply
EXTRA=
CORRECTIONS=$(ls $L/runs/teacher/${PREFIX:-cap}[0-9]_correct*.json 2>/dev/null || true)
if [ -n "$CORRECTIONS" ]; then
  $L/env/bin/python - $CORRECTIONS > $L/rows/${NAME}_corrections_in.json <<'PY2'
import json, sys
print(json.dumps([c for path in sys.argv[1:] for c in json.load(open(path)) if c.get('kept')]))
PY2
  rm -f $L/rows/${NAME}_corrections.jsonl
  $L/env/bin/python -W ignore -m strategy_agent.pipeline.corrections rows --corrections $L/rows/${NAME}_corrections_in.json --manifest $L/runs/teacher/provenance.jsonl --output $L/rows/${NAME}_corrections.jsonl
  EXTRA="--extra-rows $L/rows/${NAME}_corrections.jsonl --extra-token-share ${CORRECTION_SHARE:-0.2}"
  echo "correction rows: $(wc -l < $L/rows/${NAME}_corrections.jsonl)"
fi
[ "$N" -ge "${MIN_ROWS:-40}" ] || { echo "only $N rows, under the minimum of ${MIN_ROWS:-40}, so no training"; exit 1; }
# Before training (docs/FINAL_EVAL_PLAN.md): row coverage on the same reports. Any length refusal or any target naming
# something missing from its context stops the run, in the format the rows were built in.
$L/env/bin/python -W ignore -m strategy_agent.pipeline.row_coverage --reports $REPORTS --manifest $L/runs/teacher/provenance.jsonl --tokenizer $L/models/tiny-aya-global \
  --output $L/rows/${NAME}_coverage.json > /dev/null
$L/env/bin/python - $L/rows/${NAME}_coverage.json ${COMPACT:+compact} <<'PY2' || { echo "row coverage gate failed, no training"; exit 1; }
import json, sys
mode = 'compact' if len(sys.argv) > 2 else 'full_history'
stages = json.load(open(sys.argv[1]))[mode]['by_stage']
refused = sum(v['refused'] for v in stages.values()); ungrounded = sum(v['ungrounded_ids'] for v in stages.values())
print(f'row coverage ({mode}): {refused} refused for length, {ungrounded} targets naming something missing from their context')
sys.exit(1 if refused or ungrounded else 0)
PY2
head -n 10 $ROWS > $L/rows/${NAME}_overfit10.jsonl
set +e
$L/env/bin/python -W ignore -m strategy_agent.training.train --model $L/models/tiny-aya-global --rows $L/rows/${NAME}_overfit10.jsonl --out $L/runs/${NAME}_overfit \
  --max-steps 60 --save-steps 20 --check 10 --require 8 --minutes 120
RC=$?
set -e
[ $RC = 3 ] && { echo "overfit gate failed, no training run"; exit 1; }
[ $RC != 0 ] && { echo "overfit run crashed with exit $RC, no training run"; exit 1; }
echo "overfit gate passed $(date +%T)"
$L/env/bin/python -W ignore -m strategy_agent.training.train --model $L/models/tiny-aya-global --rows $ROWS --out $L/runs/${NAME}_pilot \
  --epochs ${EPOCHS:-3} --save-steps ${SAVE:-25} --minutes 560 $EXTRA --validation-cases ${VALIDATION:-$($L/env/bin/python -m strategy_agent.pipeline.splits)}
echo "training run finished $(date +%T)"
# Conversion gate v2 (DECISIONS 2026-11-06) on the final adapter, on this job's GPU, before any evaluation. The old
# checker picks the prompts and records its own result; the diagnosis replays them; the gate reads the diagnosis. A
# failure here is recorded and reported but never stops the evaluations below from being submitted.
conversion_gate() {
  local GATE_REV=${GATE_REVISION:?} OUTC=$L/runs/eval G=$L/models/tiny-aya-global-bf16.gguf GG=$L/runs/eval/${NAME}_gate_adapter.gguf
  local PORT=$((20000 + SLURM_JOB_ID % 20000)) SERVER
  PYTHONPATH=$L/llama.cpp/gguf-py $L/env/bin/python $L/llama.cpp/convert_lora_to_gguf.py --base $L/models/tiny-aya-global --outtype bf16 --outfile $GG $L/runs/${NAME}_pilot/adapter 2>&1 | tail -1
  $L/llama.cpp/build/bin/llama-server -m $G --lora $GG --lora-init-without-apply -ngl 99 -c 12288 --parallel 1 --host 127.0.0.1 --port $PORT --no-webui > $OUTC/${NAME}_gate_check.server.log 2>&1 &
  SERVER=$!
  for i in $(seq 1 120); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && break; sleep 5; done
  (cd $L/code_$GATE_REV && PYTHONPATH=$L/code_$GATE_REV/src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $L/env/bin/python -W ignore -m strategy_agent.evaluation.conversion_check \
    --model $L/models/tiny-aya-global --adapter $L/runs/${NAME}_pilot/adapter --url http://127.0.0.1:$PORT --rows $L/rows/${NAME}.jsonl --output $OUTC/${NAME}_gate_check.json 2>&1 | tail -1) || true
  kill $SERVER 2>/dev/null; sleep 5
  # paths first: in a prefix assignment, the ones after NAME=... would already see the new NAME
  local REF=$OUTC/${NAME}_gate_check.json AD=$L/runs/${NAME}_pilot/adapter RW=$L/rows/${NAME}.jsonl
  REVISION=$GATE_REV ACK_RECONSTRUCTED=1 ADAPTER=$AD GGUF=$GG REFERENCE_REPORT=$REF ROWS=$RW NAME=${NAME}_final \
    bash $L/code_$GATE_REV/jobs/diagnose_conversion.sbatch > $OUTC/${NAME}_gate_diagnosis.log 2>&1 || true
  local DX=$L/runs/conversion_diagnosis/${NAME}_final_${SLURM_JOB_ID}.replay.json
  [ -f $DX ] || { echo "no diagnosis replay, see $OUTC/${NAME}_gate_diagnosis.log"; return 1; }
  PYTHONPATH=$L/code_$GATE_REV/src $L/env/bin/python -m strategy_agent.evaluation.conversion_gate --replay $DX \
    --tensors $L/runs/conversion_diagnosis/${NAME}_final_${SLURM_JOB_ID}.tensors.json --output $OUTC/${NAME}_gate_v2.json
}
set +e
[ -n "${GATE_REVISION:-}" ] && { echo "conversion gate v2: $(conversion_gate 2>&1 | tail -1)"; }
set -e
# DEV_EVAL=1: the development evaluation on the validation companies (FINAL_EVAL_PLAN step 4), submitted from here so it
# never waits on a person. Every arm uses the same code, cases and compact state; the base also runs the staged prompt,
# so the base prompt can be chosen on development data. The conversion check runs and is recorded; DIAGNOSTIC=1 lets
# the arms run if it fails, with every output marked, because conversion is diagnosed separately.
if [ -n "${DEV_EVAL:-}" ] || [ "$NAME" = final ]; then  # on by default for the final run
  V=$(cat $L/queue/validation_cases.txt)
  cd $L/logs
  for spec in "dev_${NAME}:compact:$L/runs/${NAME}_pilot/adapter:$L/rows/${NAME}.jsonl:" "dev_second_newstate:compact:$L/runs/second_pilot/adapter:$L/rows/second.jsonl:1" "dev_base_staged:staged:::"; do
    IFS=: read -r EN EP EA ER ES <<< "$spec"
    DG=; SA=; if [ -n "$EA" ]; then DG=1; else SA=1; fi
    J=$(env -i HOME=$HOME PATH=$PATH USER=$USER NAME=$EN REVISION=$REVISION PROMPT=$EP ADAPTER=$EA ROWS=$ER SKIP_BASE=$ES DIAGNOSTIC=$DG SKIP_ADAPTER=$SA CASES=$V \
      sbatch --parsable --exclude=gnode04 --export=ALL ../eval_adapter.sbatch) && echo "development evaluation $EN submitted as $J"
  done
fi
