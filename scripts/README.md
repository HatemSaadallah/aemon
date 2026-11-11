# scripts

Command-line tools that are not part of the `aemon` package. Run them from the repository root.

## release/: what gets published

| Script | What it does |
|---|---|
| `build_public_repo.py` | Builds the public GitHub snapshot: no history or third-party papers, every dossier excerpt cut to its first sentence, internal identifiers scrubbed |
| `build_release.py` | Builds the public data release under the same short-quote policy |
| `make_readme_figures.py` | Draws the README figures from the committed final-test reports, light and dark |
| `replay_markdown.py` | Renders recorded final-test investigations as Markdown pages (`docs/replays/`), with no model or GPU |

## cluster/: the Bocconi cluster

| Script | What it does |
|---|---|
| `cluster.py` | `status`, `submit` (with `--after`, `--dependency`, `--array`) and `log`, over the one SSH master only |
| `sync_cluster.sh` | Copies the cluster's teacher reports, rows and evaluation outputs to this computer |
| `hpc_proxy.py` | SSH ProxyCommand with small TCP segments, for the VPN |
| `vram_probe.py` | Measures LoRA training memory for Tiny Aya (writes `vram_probe.json`) |
| `gguf_header.py` | Reads Tiny Aya's architecture from the GGUF header (writes `gguf_header.json`) |
| `check_bridge.py` | AuditKIT checks for the domain metric and the AgentTune bridge, simulated only (writes `check_bridge.json`) |

## oneoff/: scripts that produced one recorded result

They are kept so the result they produced can be traced. They are not part of any current pipeline.

| Script | What it produced |
|---|---|
| `audit_v1_evidence.py` | The evidence-reliability audit of version 1's training data and runs (2026-11-10, `docs/RELIABILITY_REPORT.md`) |
| `grpo_gpu_smoke.py` | One AgentTune GRPO step on the GPU, the smoke test for the RL path |
| `question_specificity.py` | The diagnostic of whether a narrower question changes how far the untrained model gets |
| `training_feed.py` | The live training view in the app, mirrored from a cluster training log |
| `v1r_report.py` | Version 1 against V1-r, novelty-first search (`docs/RETRIEVAL_PROPOSAL.md`) |
| `v2_review_export.py` | The version 2 answers kept by the gates, exported for review |
| `v2_reviewed_rows.py` | Version 2 rows from the examples a reviewer kept |
| `v2_training_set.py` | The version 2 continuation set (`docs/V2_CORRECTIVE_PLAN.md`) |
| `v3_rows.py` | Version 3 rows from the DeepSeek V4-Pro investigations (DECISIONS 2026-11-10 22:55 to 23:25 UTC) |
| `verify_report.py` | Version 1 against version 1 with the verification layer (`docs/VERIFY_EVAL_PLAN.md`) |
| `watch_final.sh` | The watcher for the final training job and everything it submitted |
