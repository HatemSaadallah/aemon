# V1 freeze: the submitted system (2026-11-10, approved by Nour)

| | |
|---|---|
| Evaluated code | `d3aa608` (final test), `2e9cbbd` (test set 2); git tags `v1-final-test`, `v1-test2` |
| Base model | CohereLabs/tiny-aya-global, commit `af89d21`; bf16 GGUF sha256 `4d8845665456cb90…` |
| Adapter | LoRA `adapter_model.safetensors` sha256 `740c4a9b2f415c7b…`; converted GGUF (bf16) sha256 `41794b5756b9e0f8…` |
| Published | huggingface.co/HatemSaadallah/tiny-aya-global-strategy-agent (both files; hashes checked 2026-11-10) |
| Runtime | llama.cpp `b12032` (`dde879b`), `llama-server --parallel 1 -c 12288 -ngl 99 --jinja --reasoning-format none` |
| Agent settings | `python -m aemon.agent.run_investigations --prompt compact --context 12288 --max-tokens 520 --max-turns 45` (4 refusals in a row stop a run; temperature 0, 0.4 on a retry after a refusal) |
| Off by default | the recovery features (`--recovery`), verification (`agent.verify`), V1.1 (`agent.grounded`), V1-r (`agent.novelty`) and every Aemon extra |
| Training stack | Python 3.12.16; torch 2.11.0+cu128, transformers 5.22.1, peft 0.21.2, trl 1.7.1, accelerate 1.15.0, datasets 5.1.0, tokenizers 0.23.3, safetensors 0.8.0; `requirements.lock.txt` for the rest |

**Reproduction check** (job 752500, 2026-11-10 17:46): the 15 development cases, attempt 1, were run from the frozen
commit `2e9cbbd` with the gated adapter (GGUF `41794b57…`). The runs are identical, call for call and in every
recommendation, to the same cases run today from current code (job 751713, code 9f107b1). That job is itself
identical, run for run, to stage 2 (code 52d4f4a). Result: 7 of 15 finished, 2 with every check cleared. Record:
`experiments/verify/freeze_check_adapter.json`.

The frozen results are the final test (mean of judges +0.83 [0.69, 0.97]) and test set 2 (mean of judges +0.52 [0.33, 0.70]; Claude
+0.41, Codex +0.63). They belong to this configuration only.
