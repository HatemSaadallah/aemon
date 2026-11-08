#!/usr/bin/env bash
# Copies the cluster's collected data to this computer, so nothing depends on the cluster's disk: teacher reports,
# episode streams, corrections and the provenance manifest, the queue and correction states, training rows, and
# evaluation results (converted adapter files are left out; they can be rebuilt). Uses the one persistent SSH
# connection. Run it any time: rsync only copies what changed. Usage: scripts/sync_cluster.sh [DESTINATION]
set -euo pipefail
B=${1:-$HOME/lexsi-backup/cluster}
E="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"  # ProxyCommand=false: no fallback connection when the master is gone
R=CLUSTER_ACCOUNT@CLUSTER_HOST
mkdir -p "$B"
rsync -a -e "$E" $R:lexsi/runs/teacher/ "$B/teacher/"
rsync -a -e "$E" $R:lexsi/queue/ "$B/queue/"
rsync -a -e "$E" $R:lexsi/rows/ "$B/rows/"
rsync -a -e "$E" --include='*/' --include='*.json' --include='*.jsonl' --include='*.log' --exclude='*' $R:lexsi/runs/eval/ "$B/eval/"
for d in conversion_diagnosis final_pilot; do
  rsync -a -e "$E" --include='*/' --include='*.json' --include='*.jsonl' --include='*.txt' --include='*.log' --exclude='*' $R:lexsi/runs/$d/ "$B/$d/" 2>/dev/null || true
done
echo "synced to $B at $(date +%T): $(ls "$B/teacher" | wc -l) teacher files"
