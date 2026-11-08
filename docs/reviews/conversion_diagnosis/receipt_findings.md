# First cluster receipt review, 2026-11-05

These are independent calculations from the six small files copied by Claude into `~/.cache/lexsi-cluster-receipts/`. This is an analysis of saved measurements, not a new model run or an adapter qualification. Raw files are preserved alongside this note.

| Saved check | Adapted first token | Sum of shared-prefix counts | Sum of recorded common lengths | Recorded token divergences | Short exhausted prefixes with no recorded split | Maximum on/off first-step log-gap |
|---|---:|---:|---:|---:|---:|---:|
| second | 8/8 | 202 | 205 | 1/8 | 4/8 | .2454 / .1925 |
| third | 8/8 | 187 | 205 | 1/8 | 4/8 | .2747 / .1736 |

The common-length sums are descriptive, not a proposed replacement denominator or passing threshold. A short exhausted prefix does not establish identical stopping tokens or EOS handling. Each report also contains three full32-token agreements. The old gate compares mean shared-prefix counts with24 against a nominal32 even when the stored `of` is15,22,23,24,25 or26. Thus the third's23.4/32 is not evidence of widespread token disagreement. It still has a genuine recorded first differing token at offset4; the second has one at offset22. Their margins and consequences remain unknown.

The third's observed fork is Hellberg/new-evidence-favours-looks, theories,2,416 prompt tokens, prefix4/of22, on-gap.1616 and off-gap.0832. The same prompt's base-only first token differs between backends despite the smaller gap. The maximum third on-gap and maximum added-maximum gap occur on Neumann/new-evidence-irrelevant, evidence,2,380tokens: .2747 on, .1169 off, difference.1578. That prompt has23/of23 with no recorded differing token. It is a different measurement/location from the greedy fork. Near-tie and harmlessness cannot be inferred from these summaries.

Second and third used different sampled contexts/stages/token lengths. They are not a matched comparison of conversion quality at identical prefixes; do not attribute their summary difference to the adapters alone. The new replay can diagnose each historical set, while any eventual common qualification instrument must use the same frozen contexts for both.

`val_third_conversion.json`, `val_third_diag_conversion.json` and `student_third_train_conversion.json` are byte-identical, SHA256 `37d3bd8cd1f61d8cb10cfbc5b52ca6b1751d2c1809115778692cbcf85f89b147`. They contribute **one** saved numerical result, not three replications. All eight cases in the file named student_third_train_conversion are validation-company cases (Hellberg, Neumann, Jotun); its basename does not establish an independently measured training-context check. This does not imply that validation trajectories became demonstrations.

The actual second and third adapter configs are semantically identical: rank16, alpha32, seven projection targets, ordinary LoRA, no RS-LoRA/DoRA/rank or alpha pattern, no bias or saved extra module. Their only JSON difference is the order of target_modules. This supports expected scale2 at request1 in the inspected public runtime, but does not verify native tensor values, cluster GGUF identity or actual activation.

No raw token IDs, actual incremental divergence margins or four aligned probability distributions occur in these receipts. They do not resolve conversion fidelity. fe0db0a's difference between aggregate maxima remains under review, and the second's saved passed=true is the historical rule's result, not approval under a new rule.

Claude reports diagnostic Slurm job740313 from code35eaa12, second then third, ACK_RECONSTRUCTED=1. The identified third archive was rebuilt at11:10 from the same24-report list (2,027rows). This is attributed owner provenance, not proof of exact historical bytes. Preserve the source-list/row hashes, timestamps and original replay receipts; matching case/stage/token count remains a weak reconstruction. The replay must fail rather than silently substitute a different prompt if those checks disagree. Codex initiated no SSH connection or cluster job.
