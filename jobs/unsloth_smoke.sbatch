#!/bin/bash
#SBATCH --job-name=unsloth-smoke
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=02:30:00
#SBATCH --output=%x-%j.out
# Unsloth smoke test (DECISIONS 2026-11-11): the same 50 training rows, the same LoRA (rank 16, alpha 32, every linear
# layer), seed and steps, trained twice through AgentTune's trainer, once as now and once with the model and LoRA built
# by Unsloth. Unsloth 2026.11.3 needs transformers <= 5.17, TRL 1.15 and torch 2.14.1, so it gets its own environment
# ($L/env_unsloth, built here on the compute node); the project environment ($L/env) is not touched.
# Reported: loss per step for both, seconds per step, peak GPU memory, and whether the Unsloth adapter converts to GGUF.
# Set REVISION and ROWS (a rows file on the cluster).
set -euo pipefail
L=$HOME/lexsi
OUT=$L/runs/unsloth_smoke
mkdir -p $OUT
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh
module load cuda/12.8
CODE=$L/code_$REVISION
export PYTHONPATH=$CODE/src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
head -n ${N_ROWS:-50} $ROWS > $OUT/rows50.jsonl
COMMON="--model $L/models/tiny-aya-global --rows $OUT/rows50.jsonl --max-steps ${STEPS:-12} --batch 1 --accumulate 4 --save-steps 1000 --seed 7 --minutes 60"
if [ ! -f $L/env_unsloth/.installed ]; then  # the marker is written only after a complete install
  rm -rf $L/env_unsloth
  $L/env/bin/python -m venv $L/env_unsloth
  $L/env_unsloth/bin/pip install -q --upgrade pip
  HF_HUB_OFFLINE=0 $L/env_unsloth/bin/pip install --prefer-binary --only-binary pandas,numpy "unsloth==2026.11.3" "agenttune==1.1.3" "pandas==3.1.0" "numpy==2.5.4" datasets tenacity scipy jsonschema python-dotenv tabulate > $OUT/pip.log 2>&1 \
    || { echo "install failed; the error:"; grep -iE "error|failed|requires|conflict|no matching|incompatible" $OUT/pip.log | grep -v "^ *Requirement already" | tail -25 | cut -c1-240; exit 1; }
  touch $L/env_unsloth/.installed
fi
# AgentTune and AuditKIT at the exact commits the project environment uses (requirements.lock.txt), without their
# dependencies, which the install above already resolved for this environment
HF_HUB_OFFLINE=0 $L/env_unsloth/bin/pip install -q --no-deps --force-reinstall \
  "agenttune @ git+https://github.com/Lexsi-Labs/AgentTune@d4db4c12d52342227c4113a70183d0f64aa2f345" \
  "auditkit @ git+https://github.com/Lexsi-Labs/AuditKIT@71316da345784ff220d5ed59337441a59ab31526" > $OUT/pip_lexsi.log 2>&1 || { echo "AgentTune/AuditKIT install failed"; tail -5 $OUT/pip_lexsi.log; exit 1; }
$L/env_unsloth/bin/python -c "import torch, transformers, trl, peft, unsloth, agenttune; print('unsloth env', torch.__version__, transformers.__version__, trl.__version__, peft.__version__, unsloth.__version__)"
run() {  # name, python, extra
  local T0=$(date +%s)
  cd $CODE && $2 -W ignore -m aemon.training.train $COMMON --out $OUT/$1 $3 > $OUT/$1.log 2>&1 || { echo "$1 failed"; tail -15 $OUT/$1.log | cut -c1-200; return 1; }
  echo "$1 done in $(( $(date +%s) - T0 )) s"
}
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
[ -n "${SKIP_CURRENT:-}" ] || run current $L/env/bin/python "" || true  # SKIP_CURRENT=1 keeps the earlier current run
AEMON_UNSLOTH=1 AEMON_UNSLOTH_CHECKPOINTING=unsloth run unsloth $L/env_unsloth/bin/python "--unsloth" || true  # its offloading checkpointing
AEMON_UNSLOTH=1 AEMON_UNSLOTH_CHECKPOINTING=true run unsloth_std $L/env_unsloth/bin/python "--unsloth" || true  # standard, as TRL's default
$L/env/bin/python - $OUT <<'PY'
import glob, json, sys
out = sys.argv[1]
for name in ('current', 'unsloth', 'unsloth_std'):
    states = sorted(glob.glob(f'{out}/{name}/checkpoints/*/trainer_state.json')) or sorted(glob.glob(f'{out}/{name}/**/trainer_state.json', recursive=True))
    reports = sorted(glob.glob(f'{out}/{name}/report-step*.json'))
    if not reports:
        print(name, 'no report'); continue
    r = json.load(open(reports[-1]))
    steady = sorted(r.get('step_seconds', [])[10:])  # after the first 10 steps, so start-up and compilation drop out
    median = steady[len(steady) // 2] if steady else None
    print(name, json.dumps({'losses_first_last': (r.get('losses') or [None])[:3] + (r.get('losses') or [None])[-3:], 'seconds': r.get('seconds'),
                            'median_step_seconds_after_10': median, 'peak_gpu_gb': r.get('peak_gpu_gb'), 'steps': r.get('global_step')}))
PY
# does the Unsloth adapter convert like the current one?
for name in current unsloth unsloth_std; do
  [ -d $OUT/$name/adapter ] || continue
  PYTHONPATH=$L/llama.cpp/gguf-py $L/env/bin/python $L/llama.cpp/convert_lora_to_gguf.py --base $L/models/tiny-aya-global --outtype bf16 --outfile $OUT/$name.gguf $OUT/$name/adapter 2>&1 | tail -1 | cut -c1-160
  ls -la $OUT/$name.gguf 2>/dev/null | awk '{print "'$name' gguf bytes", $5}'
done
echo "done $(date +%T)"
