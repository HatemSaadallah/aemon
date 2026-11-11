#!/bin/bash
# After the DeepSeek investigations end: rows, upload, v3 training, and the screen (DECISIONS 2026-11-10 23:25 UTC).
set -euo pipefail
cd "$(dirname "$0")/../.."
D=experiments/hosted_investigations
until [ -s $D/run.out ] && [ -s $D/run_new.out ]; do sleep 30; done
echo "generation ended $(date -u +%T)"
PYTHONPATH=src .venv/bin/python -W ignore scripts/oneoff/v3_rows.py --folder $D --base rows/final.jsonl --out rows/v3 > $D/v3_rows.log 2>&1 || { echo "rows step refused or failed: $(tail -3 $D/v3_rows.log)"; exit 1; }
cp rows/v3_report.json $D/v3_rows_report.json
git add $D docs/DECISIONS.md && git commit -q -m "DeepSeek V4-Pro investigations complete; version 3 rows built (report in experiments/hosted_investigations/v3_rows_report.json)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin claude/strategy-agent && git push -q origin HEAD:main
REV=$(git rev-parse --short HEAD)
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
git archive $REV src jobs scripts data/dossier | gzip | $SSHO CLUSTER_ACCOUNT@CLUSTER_HOST "mkdir -p ~/lexsi/code_$REV && tar -xz -C ~/lexsi/code_$REV"
rsync -az --partial -e "$SSHO" rows/v3_deepseek_train.jsonl rows/v3_deepseek_val.jsonl CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/rows/
echo "local  $(sha256sum rows/v3_deepseek_train.jsonl | cut -c1-16)  remote $($SSHO CLUSTER_ACCOUNT@CLUSTER_HOST 'sha256sum ~/lexsi/rows/v3_deepseek_train.jsonl' | cut -c1-16)"
L=/home/CLUSTER_ACCOUNT/lexsi
C=hellberg-base,hellberg-new-evidence-looks,hellberg-new-evidence-comfort,hellberg-new-evidence-favours-looks,hellberg-new-evidence-irrelevant,neumann-base,neumann-new-evidence-irrelevant,jotun-base,jotun-new-evidence-irrelevant,tanita-base,tanita-new-evidence-irrelevant,acr-base,acr-new-evidence-irrelevant,deere-base,deere-new-evidence-irrelevant
T=$(python3 scripts/cluster/cluster.py submit jobs/train_v3.sbatch --env REVISION=$REV NAME=v3 EXTRA=$L/rows/v3_deepseek_train.jsonl VALROWS=$L/rows/v3_deepseek_val.jsonl | tee /dev/stderr | grep -o 'job [0-9]*' | cut -d' ' -f2)
python3 scripts/cluster/cluster.py submit jobs/eval_adapter.sbatch --env REVISION=$REV NAME=screen3_v1 ADAPTER=$L/runs/final_pilot/adapter CASES=$C PROMPT=compact SKIP_BASE=1 DIAGNOSTIC=1 ATTEMPTS=1 SPLIT=development ROWS=$L/rows/final.jsonl
python3 scripts/cluster/cluster.py submit jobs/eval_adapter.sbatch --after $T --env REVISION=$REV NAME=screen3_v3 ADAPTER=$L/runs/v3/adapter CASES=$C PROMPT=compact SKIP_BASE=1 DIAGNOSTIC=1 ATTEMPTS=1 SPLIT=development ROWS=$L/rows/v3_deepseek_val.jsonl
python3 scripts/cluster/cluster.py status | head -6
echo "chain submitted $(date -u +%T), code $REV"
