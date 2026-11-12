#!/bin/bash
# Hatem, 12 Nov 16:00: "it doesn't have to finish. can we use the data that we will generate today only?"
# At the cut-off (21:00 CET, DECISIONS 2026-11-12 16:10) the teacher step ends: driver.sh is told the teacher is done
# (state/teacher_done, read at its next 10-minute check), so it merges the batches finished by then and builds the rows;
# the teacher jobs are then cancelled. Unfinished batches are left out and named in the driver log.
set -uo pipefail
cd "$(dirname "$0")/../.."
D=experiments/v4_recovery
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
until [ "$(date +%H%M)" -ge "${CUTOFF:-2100}" ]; do sleep 300; done
grep -q "step 3 done\|teacher done" $D/driver.log && { echo "$(date '+%F %T') teacher already done before the cut-off"; exit 0; }
touch $D/state/teacher_done
echo "$(date '+%F %T') cut-off: teacher step ended (Hatem, 16:00); batches with output: $(ls $D/teacher 2>/dev/null | grep -cE '^v4t[0-9]+_correct_v4_[0-9]+\.json$') fetched before, the driver fetches again" >> $D/driver.log
until grep -q "teacher done" $D/driver.log; do sleep 60; done
sleep 120  # the driver's rsync of finished batches runs right after 'teacher done'
for j in $(awk '{print $1}' $D/state/teacher_jobs.txt); do $SSHO CLUSTER_ACCOUNT@CLUSTER_HOST "scancel $j 2>/dev/null || true"; done
echo "$(date '+%F %T') cut-off: teacher jobs cancelled" >> $D/driver.log
