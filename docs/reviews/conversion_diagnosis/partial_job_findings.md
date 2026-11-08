# Job740313: tensor diagnosis completed, numerical replay incomplete

2026-11-06. These observations are independently calculated from Claude's copied job receipts in cluster_receipts/diagnosis_740313/. Codex submitted no cluster job and performed no pretrained inference.

Both native/GGUF artifact pairs pass every implemented factor check:504/504 factors equal the expected BF16 cast of their native FP32 tensors, with complete names/shapes/ranks, alpha32 and finite values. The252 native LoRA modules each report scale2 and no merge. Tensor/config hashes in each replay header match its CPU audit. The local second GGUF SHA matches the cluster exactly; the third GGUF is3399908f0af5bdc0a6cc6f2d5b9790591438a3b542b78b16f4919d28b1ee228a. Both jobs report the inspected llama.cpp commit dde879bc4f954b809892fd0d660515f42536394a and matching exporter SHA. The shared runtime binary SHA is482df3a48976112c5a476fd7acdd7d377f47653a1edfb34241aa5a29165080f4.

| Diagnostic | second | third |
|---|---:|---:|
| Expected-cast factor equality | 504/504 | 504/504 |
| Maximum relative L2 factor storage error against FP32 | .00172949 | .00171924 |
| Maximum relative L2 factorized-update error, fixed four-vector probes | .00361794 | .00385291 |
| Native module count / effective scale | 252 / 2 | 252 / 2 |

These fixed-vector update errors quantify representation loss only; they do not bound actual hidden-state/output-logit error. They are not a fidelity tolerance or model qualification. The receipts rule out the inspected missing-factor, wrong-value-beyond-cast, shape, global-scale-metadata and merge defects for these pairs. They do not rule out backend execution/attention/cache differences or show that a changed generated action is harmless.

The numerical replay stopped after the first legacy-like server completion, before any per-prompt trace/margin/effect files were saved. The copied traceback is truncated at269bytes and omits the final exception; the full traceback has been requested. The recorded HF generation_config has num_beams=None. The collector's old `getattr(gcfg, 'num_beams', 1) != 1` guard incorrectly rejects that as beam search. The failure point matches the saved server logs. A local CPU GenerationConfig fixture reproduces this guard defect. Transformers5.22.1's local _prepare_generation_config fills unset fields using its global defaults; num_beams defaults to1. The corrected collector resolves that default without changing the config and still rejects genuine beam search. It records the effective beam count. A second regression test saves complete failure evidence if a later replay step fails.

This is a collector bug, not evidence of a LoRA conversion bug. The precise cluster exception remains unconfirmed until its untruncated traceback arrives. No new gate or pass status is inferred.

The server headers confirm repeat_penalty1, presence/frequency penalties0 and build b1-dde879b, so the previously considered default repetition-penalty mismatch is not supported in this run. The server caps its requested12288 context to8192; the saved prompts are shorter, so that log alone does not demonstrate truncation. Its EOS warning also does not prove that EOS is ignored: the [pinned loader](https://github.com/ggml-org/llama.cpp/blob/dde879bc4f954b809892fd0d660515f42536394a/src/llama-vocab.cpp#L3330) inserts the EOS ID into the EOG set before emitting that warning. Exact generated IDs/stops still need capture.

Rerun the second and third diagnostics with the corrected #32 head, fresh output filenames/job IDs, unchanged historical inputs and ACK_RECONSTRUCTED limitation. Preserve740313's partial evidence. This adds no model-selection result, changes no thresholds and does not repair/reclassify either adapter. Actual incremental margins, same-prefix adapter-effect residuals and the native rounded-value control remain required before attributing greedy flips to near-ties or choosing a justified conversion gate.
