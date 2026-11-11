#!/bin/bash
# Status check (DECISIONS 2026-11-11): submit the Aquaporin diagnostic, the teacher run and the development harm check as
# the per-user limit of 4 jobs allows, after the switching test's last arm is in.
set -uo pipefail
cd "$(dirname "$0")/../.."
REV=be69cd1
DEV=hellberg-base,hellberg-new-evidence-looks,hellberg-new-evidence-comfort,hellberg-new-evidence-favours-looks,hellberg-new-evidence-irrelevant,neumann-base,neumann-new-evidence-irrelevant,jotun-base,jotun-new-evidence-irrelevant,tanita-base,tanita-new-evidence-irrelevant,deere-base,deere-new-evidence-irrelevant,acr-base,acr-new-evidence-irrelevant
AQP=aqp-base,aqp-new-evidence-irrelevant,aqp-new-evidence-undermines-maintenance,aqp-new-evidence-favours-maintenance
active() { python3 scripts/cluster.py status 2>/dev/null | grep -c " \(RUNNING\|PENDING\) "; }
until grep -q "submitted eval_switch" experiments/switch/pipeline.log 2>/dev/null; do sleep 300; done
JOBS=(
  "jobs/eval_switch.sbatch NAME=status_aqp_v1 ROUTE=default=0 SPLIT=heldout STATUS_CHECK=1 CASES=$AQP REVISION=$REV"
  "jobs/eval_switch.sbatch NAME=status_aqp_v3 ROUTE=default=1 SPLIT=heldout STATUS_CHECK=1 CASES=$AQP REVISION=$REV"
  "jobs/command_a_plus.sbatch NAME=status_teacher STATUS_CHECK=1 QUEUE=/home/CLUSTER_ACCOUNT/lexsi/runs/teacher/status.queue REBUILD=1 HOURS=21 REVISION=$REV"
  "jobs/eval_switch.sbatch NAME=status_dev_v1 ROUTE=default=0 STATUS_CHECK=1 CASES=$DEV REVISION=$REV"
  "jobs/eval_switch.sbatch NAME=status_dev_v3 ROUTE=default=1 STATUS_CHECK=1 CASES=$DEV REVISION=$REV"
)
for j in "${JOBS[@]}"; do
  until [ "$(active)" -lt 4 ]; do sleep 300; done
  set -- $j; script=$1; shift
  python3 scripts/cluster.py submit $script --env "$@" || { echo "submit failed: $j"; sleep 300; python3 scripts/cluster.py submit $script --env "$@" || echo "gave up: $j"; }
  sleep 30
done
echo "all submitted $(date +%T)"
