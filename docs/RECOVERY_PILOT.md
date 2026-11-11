# Proposal: a recovery-data pilot

Status: **proposed 2026-11-03, not approved.** Needs Hatem's go-ahead and Codex's review before any row is trained on.

## Why

Teacher demonstrations show successful paths. The student fails off those paths: in the second pilot it repeated
an identical search after refusal (67 of its 113 refusals) and reread sources until the turn limit. Harness changes
removed budget refusals but not the loops (laptop probe, 2026-11-03). The student has almost no examples of escaping
its own states, because the teacher rarely enters them: about 7 rows recover from a repeated search.

## What

1. **States.** Replay recorded student runs and keep the exact compact state shown at each turn that starts a loop: a
   call refused as a repeat, the third reread of one source, or a second refusal in a row. Training companies only:
   never the six validation companies in `src/aemon/pipeline/splits.py` or the frozen final test. Each state keeps its student run,
   model identity and turn index.
2. **Corrections.** Command A+, the permitted teacher, gets that state under the teacher prompt and writes the next
   call. A correction is kept only if replaying it from the state is accepted by the tools, is not itself a repeat, and
   moves toward the stage's goal (an unread source, a new theory, the stage's tool). Every kept and refused correction is
   recorded with its reason. The teacher may also see a one-line note that the previous call was refused, the same note
   the student saw.
3. **Provenance.** A new protocol id, `correction-v1`. The manifest records the student run and turn the state came
   from and the hash of the teacher's reply. Rows from it carry `source: correction`, so they can always be counted,
   capped or removed.
4. **Rows.** The student's state as context and the teacher's call as the only target, like every other row.

## The pilot and its test, declared before running

- About 150 corrections from about 40 student runs on training companies. At one teacher turn each, this is about
  two hours of one teacher slot.
- Adapter C2 = the second adapter's training rows plus the corrections, capped at 20% of rows, same settings.
- Compared with the second adapter on the six validation companies, same runtime, prompt and cases, both arms compact:
  repeated calls per run, median highest stage completed, finished runs, sources read and used, and the test-stage
  prefix probe. Paired by case.
- **Success:** repeated calls per run fall by at least half, the median stage completed rises, and finished runs do not
  fall. Otherwise the corrections are not used in the full run.

## Risks

- Student states can be ones the teacher would never reach, so its correction may be odd. The guards, the replay check
  and the recorded refusals screen mechanical errors, not judgement.
- Corrections that only teach "stop repeating" could cut repeats without better investigations. The prefix probe and
  the stage measures, and later the blind judges, check that.
- A new protocol id means the provenance and row code change. Codex should review it like the existing manifest.
