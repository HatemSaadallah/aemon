# codex_judge

Codex as the second blind judge, run on 2026-11-11 under the same frozen instrument and receipt as the final test
(`reports/judge/codex_score_qualification_bound.json`). It judged three packet sets: test set 2 with base and version 1
(the frozen headline's second judge), then test set 2 and the final test with base, version 1 and version 3
(exploratory). A call that fails on the usage limit or a timeout is archived and judged again, waiting an hour per
round. A judge-invalid output stays missing.

`run.py` drives it; the reports go to `reports/judge/test2/`, `reports/judge/test2_v3/` and `reports/judge/final_v3/`.

DECISIONS.md: "2026-11-11: version 3 on both test sets, exploratory only", and the test set 2 entry
"2026-11-10 01:40: test set 2, Claude-only result (frozen protocol unchanged; Codex from 11 November)".
