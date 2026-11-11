#!/bin/bash
# Watches the final training job and everything it submits, through the existing SSH master only. Every 5 minutes it
# reads the job states and the training log in one SSH call, writes what changed to ~/lexsi-backup/watch.log, and
# queues the same lines to Codex. Training progress and the latest logged loss are reported every 30 minutes. It uses only the shared SSH master: when the
# master is gone (the laptop slept) it reopens it, at most once every 20 minutes, and ssh cannot open side connections.
# Usage: scripts/oneoff/watch_final.sh JOBID [CODEX_THREAD]
set -u
JOB=$1
THREAD=${2:-}
OUT=$HOME/lexsi-backup/watch.log
STATE=$HOME/lexsi-backup/watch_state
mkdir -p "$STATE"
# ProxyCommand=false: when the master is gone, ssh cannot fall back to a connection of its own
SSH=(ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false CLUSTER_ACCOUNT@CLUSTER_HOST)
HERE=$(cd "$(dirname "$0")" && pwd)
last_open=0
open_master() {  # the one shared connection, reopened after the laptop sleeps; at most one attempt every 20 minutes
  [ $(( $(date +%s) - last_open )) -ge 1200 ] || return 1
  last_open=$(date +%s)
  ssh -o BatchMode=yes -o ControlMaster=yes -o ControlPath=$HOME/.ssh/cm-lexsi -o ControlPersist=12h -o ServerAliveInterval=30 \
    -o IPQoS=none -o KexAlgorithms=curve25519-sha256 -o "ProxyCommand=python3 $HERE/hpc_proxy.py %h %p" -Nf CLUSTER_ACCOUNT@CLUSTER_HOST \
    </dev/null >/dev/null 2>&1
  ssh -O check -o ControlPath=$HOME/.ssh/cm-lexsi CLUSTER_ACCOUNT@CLUSTER_HOST 2>/dev/null
}
PATTERN='teacher stage reports|rows built|correction rows|only [0-9]+ rows|coverage|overfit gate|overfit run|training run finished|conversion gate|development evaluation|Traceback|Error|error:|Killed|out of memory|No space|nothing to train'
last_progress=0
master_down=0

say() {  # one batch of event lines: to the log, to stdout, and to Codex
  [ -s "$1" ] || return 0
  sed "s/^/$(date +%H:%M) /" "$1" | tee -a "$OUT"
  [ -n "$THREAD" ] && codex queue --thread "$THREAD" --message "From Claude's watcher on final training $JOB ($(date +%H:%M)):
$(cat "$1")" > /dev/null 2>&1
  return 0
}

while true; do
  NEW=$STATE/new
  : > "$NEW"
  if ! ssh -O check -o ControlPath=$HOME/.ssh/cm-lexsi CLUSTER_ACCOUNT@CLUSTER_HOST 2>/dev/null && ! open_master; then
    [ $master_down = 0 ] && echo "SSH master is down and could not be reopened; next attempt in 20 minutes" > "$NEW"
    master_down=1
  else
    master_down=0
    "${SSH[@]}" "sacct -u \$USER -S 2026-11-07T14:30 -X -n -P -o JobID,JobName,State,ExitCode,NodeList; echo ===;
      f=~/lexsi/logs/train-after-$JOB.out; tr '\r' '\n' < \$f | grep -a -E '$PATTERN' | cut -c1-240; echo ===;
      tr '\r' '\n' < \$f | awk '/overfit gate passed/{m=1} m' | grep -a -o -E '[0-9]+/[0-9]+ \[[0-9:]+<[0-9:?]+' | awk -F'[/ ]' '\$2 >= 100' | tail -1; echo ===;
      tr '\r' '\n' < \$f | awk '/overfit gate passed/{m=1} m' | grep -a -o -E \"\\{'(eval_)?loss'[^}]*\\}\" | tail -3; echo ===;
      squeue -u \$USER -h | wc -l" > "$STATE/now" 2>/dev/null
    if [ $? = 0 ]; then
      awk 'BEGIN{RS="===\n"} NR==1' "$STATE/now" | awk -F'|' -v j=$JOB '$1>=j {print "job " $1 " " $2 ": " $3 " (exit " $4 ", " $5 ")"}' | sort > "$STATE/jobs"
      awk 'BEGIN{RS="===\n"} NR==2' "$STATE/now" | grep . > "$STATE/log"
      touch "$STATE/jobs.seen" "$STATE/log.seen"
      comm -13 "$STATE/jobs.seen" "$STATE/jobs" >> "$NEW"
      grep -v -x -F -f "$STATE/log.seen" "$STATE/log" | grep . >> "$NEW"
      cp "$STATE/jobs" "$STATE/jobs.seen"
      cat "$STATE/log" "$STATE/log.seen" | sort -u > "$STATE/log.tmp" && mv "$STATE/log.tmp" "$STATE/log.seen"
      p=$(awk 'BEGIN{RS="===\n"} NR==3' "$STATE/now" | tr -d '\n')
      loss=$(awk 'BEGIN{RS="===\n"} NR==4' "$STATE/now" | tr -d "{}'" | sed 's/grad_norm: [^,]*, //' | paste -sd ';')
      if [ -n "$p" ] && [ "$p" != "${last_p:-}" ] && [ $(( $(date +%s) - last_progress )) -ge ${EVERY:-1800} ]; then
        last_p=$p
        echo "training progress: step $p; last logged: ${loss:-none yet}" >> "$NEW"
        last_progress=$(date +%s)
      fi
    fi
  fi
  say "$NEW"
  # done when every watched job has ended and nothing of ours is queued (held jobs do not show in sacct)
  queued=$(awk 'BEGIN{RS="===\n"} NR==5' "$STATE/now" 2>/dev/null | tr -d ' \n')
  if [ -s "$STATE/jobs.seen" ] && [ "${queued:-1}" = 0 ] && ! grep -q -E ': (PENDING|RUNNING|REQUEUED|CONFIGURING|COMPLETING|RESIZING|SUSPENDED)' "$STATE/jobs.seen"; then
    echo "all watched jobs have ended" > "$NEW"; say "$NEW"; exit 0
  fi
  [ -n "${ONCE:-}" ] && exit 0
  t=$(( $(date +%s) + 300 )); while [ $(date +%s) -lt $t ]; do sleep 20; done
done
