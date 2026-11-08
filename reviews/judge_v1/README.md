# Frozen judge and non-Claude screener package, v1

**Candidate status: not run / not qualified.** Claude owns the cluster connection and candidate Aya Expanse 32B Q4_K_M. Command A+ is the teacher and must not screen its own trajectories. This package made no model, paid API, GPU or cluster calls. Connection recovery and a saved candidate run are still required. The files freeze an instrument for review; freeze the commit before qualification, and never tune it against final-test runs.

`judge_prompt_v1.txt` includes the nine-dimension rubric and structured output contract. `rubric_v1.md` versions the source rubric with explicit proportional-retention, optional-test and predeclared-applicability clarifications. A scheduled but undelivered update is not reached, not outside scope. The prompt explicitly clarifies proportional revision, optional justified tests, source support versus verbatim quotation, missing-stage status, and how missing stages enter the all-case composite. `config_v1.json` pins SHA-256 hashes; changing any pinned artifact makes the tool refuse execution until deliberately versioned. Judges see episode chronology and sources without arm names or expected labels. Case-author labels are hypotheses about this instrument, not human-reviewed ground truth.

Six requested synthetic development anchors are in `anchors_v1.jsonl`: nonsense, clipped quote, false support, weak test, incomplete run and a strong reference. The reference is deliberately tentative about demand. Expected labels are separate in `anchor_key_v1.jsonl`. Do not send keys to a model.

The **separate qualification set** has 40 packets, 20 positive and 20 seeded-negative, in `qualification_packets_v1.jsonl`. There are 20 fictional scenario clusters across product/use combinations; each has one sound and one deliberately flawed version. Positive and negative examples share a writing template, so this controls superficial wording but does not establish broad natural-trajectory generalization. It does not contain any of the final held-out companies or sources. The set is separate from the six development anchors, but its construction remains synthetic and author-labelled. No passed qualification permits a commercial-correctness claim.

The conservative gate requires at least 20 distinct declared clusters per class, no missing/duplicate/malformed responses, correct critical-error flags, both TPR/TNR >= .8, and **each marginal 95% Wilson lower bound >= .8**. At n=20 this requires 20/20 in each class (lower bound about .839); 19/20 fails (about .764). Six anchors alone cannot qualify a screener. Repeated ratings of one packet do not increase independent cluster count. The intervals are per class, not a simultaneous 95% guarantee. Template/source dependence limits any statistical independence claim; natural teacher checks and error reporting are still needed. A failed candidate remains unqualified; do not relabel or replace difficult packets after seeing results.

## Run handoff for Claude

Copy this folder to the cluster code folder using your existing persistent connection. Do not create a second SSH connection. Start Aya Expanse using your existing Slurm server launcher and its own job port. Use the actual artifact hash/runtime in the job manifest. The HTTP runner below records requested model, teacher, exact prompt hash, full raw responses and parser errors. It cannot attest which weights a server loaded; preserve server metadata and hashes alongside its output.

```sh
python judge.py prepare --packets qualification_packets_v1.jsonl --output qualification_blind_local.jsonl
python judge.py run --packets qualification_blind.jsonl --output aya_qualification_raw.jsonl --url http://127.0.0.1:PORT --model aya-expanse-32b-Q4_K_M --teacher-model command-a-plus-05-2026-Q4_K_M
python judge.py evaluate --predictions aya_qualification_raw.jsonl --key qualification_key_v1.jsonl --output aya_qualification_result.json
```

The runner refuses Claude model labels and a candidate identical to the teacher, refuses overwrites, and does no automatic retry that might hide failures. Generation is frozen at 3,000 output tokens per packet and temperature zero, with an 8,192-token effective context requirement; the runner refuses a different output cap. Preserve the actual server context/template configuration as execution evidence. JSON/format failures are observed candidate failures and fail the gate. Preserve timeout/server errors as infrastructure observations before interpreting them as reasoning failures. If the batch is interrupted, keep its prefix and rerun a separately identified full batch instead of quietly filling favorable missing results.

Qualification does not grant data rights or model permission. This package does not call the teacher, import teacher trajectories, choose training rows, train an adapter or claim any screener accuracy. A subsequent actual screening run must retain every accept/reject decision and rationale and keep final-evaluation judges separate from row selection.

## Open the UI/backend

```sh
python judge.py serve --port 8012
```

Open http://127.0.0.1:8012. `/api/status` exposes the frozen config and synthetic development anchors. It truthfully shows not run; the UI never fabricates candidate results. The local read-only backend uses Python's standard library and binds to loopback. It does not invoke a model.

## Offline validation

```sh
PYTHONDONTWRITEBYTECODE=1 python check_offline.py
```

Fourteen offline probes passed (including provenance and applicability checks): a complete scripted perfect result passes only the offline fixture checks; missing, duplicate, misclassified, malformed-dimension and missed-critical-flag responses fail; development anchors cannot be mistaken for qualification. These scripted predictions are **checker tests only**, never candidate reliability evidence. `evaluate --fixture` always emits an offline-fixture status and can never mark a candidate qualified. Real qualification requires the pinned qualification-key bytes, pinned blind-packet digest, prompt hash and uniform exact candidate/teacher labels recorded by the runner. Wrong model/prompt/key/dataset, mixed metadata, fixture-labelled outputs and scheduled-but-undelivered updates mislabelled not-applicable are refused. Runtime labels do not cryptographically attest server weights; keep actual server metadata/hashes alongside the output. The blind packet preparer uses an explicit field allowlist, and the API refuses unknown routes.

## November 5 storage decision

Aya-specific qualification is deferred; Claude may delete the19GB GGUF after retaining small manifests/hashes/raw results. The candidate remains not_run/not_qualified. Prompt/anchors/checker/UI need no weights. Pinned instrument/candidate hashes are unchanged. A replacement requires a versioned configuration and a separate qualification; no quality gate is waived. This qualification runner is not the two-judge general-episode evaluation runner.
