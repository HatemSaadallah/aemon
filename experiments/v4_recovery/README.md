# v4_recovery

Version 4, recovery distillation for the reasoner: steps 1 to 3 of the plan registered in `docs/DECISIONS.md`,
"2026-11-12 01:10: version 4, recovery distillation for the reasoner", run as registered.

`driver.sh REVISION` runs from the laptop over the one SSH master and resumes from `state/` if restarted:

1. **Harvest.** Dig then reason without the status check (`ROUTE=default=1,brief=0,frame=0,evidence=0`: version 1
   writes brief, frame and evidence, version 3 the rest), compact prompt, 45 turns, 4 refusals in a row, one attempt,
   on the 192 training cases (`harvest_cases.json`: development cases of the 93 non-validation companies; none from a
   validation, final-test or test-set-2 company). Four `jobs/eval_switch.sbatch` jobs of 48 interleaved cases, reports
   in `harvest/`.
2. **States.** `aemon.teacher.corrections states` on the four reports, keeping loops that start in the stages
   version 3 writes (theories, assessment, challenge, challenge_reading, test, position, new_evidence, update,
   conclude), with the two adapters and the route as the student identity: `states.json`, split into batches of 20 in
   `batches/` and queued on the cluster as `~/lexsi/queue/recovery_v4.txt`.
3. **Teacher.** Command A+ (Q4_K_M, downloaded into node memory by the job) answers each state in the teacher job's
   `correct` queue mode, protocol correction-v1 unchanged. One or two workers share the queue; each is the 80 GB job if
   its slice can start within the hour, otherwise the 40 GB one. `MIN_KEPT=0` keeps a worker going when a batch keeps
   little (the job still stops on an unreadable output or when half the requests fail). The replies, the manifest
   copy and `corrections_summary.json` (kept and refused, with reasons) land in `teacher/`, `corrections.json` and
   `rows/v4_corrections.jsonl` (also `~/lexsi/rows/v4_corrections.jsonl`), built by `corrections rows`, manifest-checked.

The log is `driver.log`. Training (`jobs/train_v4.sbatch`, step 3 of the plan) is prepared but not submitted here.
