Current rerun policy (2026-11-06): [explicit greedy controls and training boundary](EXPLICIT_GREEDY.md).

# Conversion diagnosis — evidence before tolerances

2026-11-05, responding to Hatem/Claude's request. **PR#31 is draft pending this diagnosis. No revised tolerance is adopted here and no adapter is qualified.** This deliverable contains actual local artifact inspection, a mathematical counterexample to the old effect interpretation, and a read-only cluster replay to obtain missing evidence.

## What has actually been checked

2026-11-06 update: [job740313 partial diagnosis](partial_job_findings.md) now matches both native/GGUF factor pairs and the actual runtime/exporter. Both504-factor audits pass expected BF16 casts; numerical replay stopped before margins. The collector fix resolves unset HF num_beams via its real global default and preserves complete future error evidence. No adapter is qualified.

Update: [first cluster receipt review](receipt_findings.md) and immutable small receipts under cluster_receipts/ are now available. Actual incremental margins, aligned adapter effects and native tensor equality remain unmeasured.

The locally available Nov3 `second_adapter.gguf` is60,491,936bytes, SHA256 `be8a6b004dee357e6feab9a1404fc7f5c9dbbe3c3eeb79cbb4e97fb7cea0c1bd`. Its504tensor directory and payloads were read independently. There are exactly36layers ×7linear-module types ×A/B, every expected name and architecture-reference shape is present, all tensors areBF16(type30), and every tensor is finite and contains nonzero elements. Alpha metadata is32; all factor pairs have rank16. See local_second_findings.json and local_second_inventory_hashed.json, including per-tensor numeric hashes and a tensor-value identity that binds architecture/alpha and excludes provenance metadata.

That excludes missing factors, wrong directory shapes/rank/type and nonfinite payloads **in this local artifact**. It does not establish that it is the cluster file, that factors equal the native PEFT checkpoint, that the actual cluster runtime applies the right scales, or that a trajectory change is harmless. The architecture reference is the pinned public Tiny Aya GGUF header already in scripts/gguf_header.json, not an independently obtained current native config.

Public llama.cpp tagb12032 resolves at review time to commit `dde879bc4f954b809892fd0d660515f42536394a`. Its [runtime scale](https://github.com/ggml-org/llama.cpp/blob/dde879bc4f954b809892fd0d660515f42536394a/src/llama-adapter.h#L53) is request_scale ×alpha/rank: request1,alpha32,rank16 means2. The [exporter](https://github.com/ggml-org/llama.cpp/blob/dde879bc4f954b809892fd0d660515f42536394a/convert_lora_to_gguf.py#L413) writes alpha metadata and separate A/B factors, and the [Cohere2 conversion](https://github.com/ggml-org/llama.cpp/blob/dde879bc4f954b809892fd0d660515f42536394a/conversion/command_r.py#L37) has no Q/K permutation for these linear factors. The public graph has LoRA-aware Q/K/V, output and FFN paths. There is no obvious global-alpha or skipped-module defect in these inspected sources. **Actual cluster source/binary hashes remain unmatched.** Public source receipts are in public_sources.json; upstream code/weights are not copied into this PR.

The current job converts a separate adapter; it does not merge it into the base. Local PEFT0.21.2 defaults upcast half/BF16 adapters toFP32; the GGUF here storesBF16 factors. Thus storage/cast and accumulation pathways can differ even when the base isBF16. The real checkpoint dtype is still needed. BF16's expected round-to-nearest-even casting is checked elementwise, rather than treating arbitrary factor differences as benign. A CPU configuration-only Cohere2/PEFT fixture independently confirms that all-linear expands to these seven projection names and excludes lm_head; it performs no forward pass or training.

## What can be refuted without cluster access

Subtracting two maximum absolute errors is **not a bound on adapter-effect reproduction**. The following normalized, synthetic two-token distributions keep the adapted top1 unchanged:

| Distribution | token0 | token1 |
|---|---:|---:|
| PEFT off | .60 | .40 |
| GGUF off | .64 | .36 |
| PEFT on | .80 | .20 |
| GGUF on | .78 | .22 |

The old on maximum log-gap is0.09531, off maximum0.10536, so the fe0db0a-style added maximum is−0.01005. But on the **same token IDs**, `(GGUF_on−GGUF_off)−(PEFT_on−PEFT_off)` reaches0.20067. See max_gap_counterexample.json. This is a mathematical counterexample, never model evidence or training data. fe0db0a literally implements its empirical gap difference, but interpreting that difference as isolated conversion error is unjustified. Its post-failure adoption cannot establish fidelity of either actual adapter.

A base-only gap also does not prove harmless kernel noise: wrong base provenance, attention/window/cache semantics or decoding settings can produce it. Diagnose those before defining a tolerance.

## What the saved JSONs cannot answer

The historical checker saves aggregate first-step maximum gaps and greedy-prefix lengths. It does not save raw token IDs, actual divergence-token top1/top2 margins, or four aligned probability arrays. You cannot recover the requested margins or per-token effect residual by subtracting those maxima. The summary tool returns missing fields as unknown, never guessed numbers.

The old checker also compares its prefix count to32 even when `of` is shorter. Exhausting a common prefix is not an observed token disagreement. The new summary distinguishes these without assuming identical EOS. Decoder defaults were not explicitly matched or recorded. This is a confound to check, **not a confirmed repetition-penalty mismatch**: the inspected public b12032 common/common.h default is1.00, despite documentation elsewhere advertising1.1; actual server properties and the model generation_config are decisive.

At the initial #32 delivery, raw cluster files were not accessible locally. Claude has since copied four numerical files and both adapter configs through the existing connection. See [the saved-receipt analysis](receipt_findings.md): the numbers are now independently recalculated from those files, but no fresh numerical replay or native-factor comparison has been completed by Codex. The three third-adapter files are byte-identical. Codex opened no SSH connection or cluster job. The stage correction is likewise attributed: third7completed challenge then looped in test(117test repeats),8completed evidence then stopped in theories; second10stopped in theories,1assessment,2conclude,2finished. These establish neither a data-volume effect nor native-versus-converted behavioral equivalence.

## Read-only evidence collection

`conversion_diagnose inventory` inspects GGUF alone. `audit-tensors` additionally reads actual adapter_config, native safetensors and base config, checks every adapted tensor name/shape/rank/alpha and expected F32/F16/BF16 cast, records hashes and actual dtypes, and compares factorized updates on fixed Rademacher vectors without forming a dense base merge. Unexpected native tensors are reported, not ignored. Nonempty RS-LoRA/DoRA/rank/alpha patterns and unsupported mapping features are not falsely cleared. A mismatch identifies an inconsistent artifact pair; provenance must be checked before blaming a converter.

`replay` is guarded to run inside an owner-submitted Slurm job and:

1. Binds the actual local server PID/port/base path, loaded adapter, native/GGUF/config hashes, runtime properties, PEFT dtypes/scales, merge state, generation configuration and attention/window parameters.
2. Uses recorded input IDs where available; otherwise requires --ack-reconstructed and an archived row file, checking historical case/stage/token length. Such reconstruction is labelled weak and is not proof of exact historical input identity. The old JSON did not bind its row-file hash.
3. Runs one explicit greedy profile with adapter off/on. HF fixes num_beams=1, do_sample=False, repetition_penalty=1, temperature=1, top_k=0, top_p=1. llama.cpp fixes temperature=0, top_k=1, top_p=1, min_p=0 and neutral penalties. The inherited HF config, effective HF config, server /props, exact requests and returned settings are retained. Raw pre-sampling probabilities remain requested for numerical comparisons. Historical default-driven traces are not regenerated.
4. Captures the **actual incremental native raw and processed logits at each first differing token**, including top1/top2 margin, both selected IDs, score under the native distribution, and server incremental candidates. An exhausted prefix is labelled separately. A small margin may explain a numerical flip but does not prove the changed action/trajectory is harmless.
5. Replays each distinct shared prefix through all four distributions(PEFT/GGUF ×off/on), using the same token IDs, and records signed per-token adapter effects and their difference-of-differences. It compares incremental versus full-prefix recomputation, and native full projection versus last-position-only projection, to separate cache/batching/kernel paths from stored-factor differences. All common finite vocabulary metrics include support coverage; missing or zero probabilities are censored, never assigned invented values.
6. Preserves exact token streams, request/effective settings, compressed probability arrays and hashes. Traces are saved before later distribution queries, retaining useful margins if a full-vocabulary API query fails. No threshold or model selection is applied; every report is diagnostic/ineligible.

The full-logprobs option requests the native vocabulary size. If the server caps it, count/coverage reveal the missing values and effect statistics remain explicitly conditional on observed support. Arrays are retained on the cluster; copy the small JSONs for review, not base weights. No real replay has been executed by Codex. Real API compatibility and numerical results remain unmeasured.

## Controlled precision comparison

Replay additionally rounds only LoRA A/B values to BF16 and restores their original dtype before querying native PEFT. Base weights and arithmetic dtype stay unchanged. Cloned original factors are restored in a finally block, including on exceptions; checkpoint files are unchanged. This separates stored-value rounding from runtime/kernel changes. Its effect and remaining PEFT/GGUF disagreement are reported without replacing the original reference.

Keep original BF16 files unchanged. Under Slurm, export a new F32 adapter from the **same native checkpoint**, using the exact converter/source revision and a fresh filename; archive both conversion logs. Audit both tensor pairs and repeat the same diagnostic prompts/server build/base. F32 storage also changes runtime kernels, so an end-to-end improvement supports a precision/kernel pathway, not proof that storage rounding alone caused the old split. Elementwise factors and factorized-update probes quantify the representation component independently. Native and GGUF runtime scale1 must be checked, not inferred from filenames.

Do not merge the base in BF16 to create a purported native reference. If testing merged versus unmerged execution, label the extra treatment and preserve the FP32 master; it is a separate diagnostic, not a replacement for the original baseline.

## Run and inspect

Claude submits jobs/diagnose_conversion.sbatch using the existing persistent connection. Set REVISION, ADAPTER, GGUF, REFERENCE_REPORT, ROWS and NAME. ACK_RECONSTRUCTED=1 is appropriate only when the archive is identified and the limitation is recorded. Run separately for second/third and any same-source F32 control. The script reads artifacts and produces diagnostics; it neither trains nor qualifies an adapter.

CPU/local inspection examples:

    python -m strategy_agent.evaluation.conversion_diagnose inventory --gguf PATH --output NEW.json
    python -m strategy_agent.evaluation.conversion_diagnose summarize --reports SECOND.json THIRD.json --output NEW.json
    python -m strategy_agent.evaluation.conversion_diagnose serve --port 8015 \
      --tensor-audit INVENTORY_OR_AUDIT.json --summary SUMMARY.json --replay REPLAY.json

Open http://127.0.0.1:8015. The read-only backend and text-only UI show unknown evidence explicitly; /api/diagnosis exposes artifacts and unknown routes404. Until data arrive, the local artifact is structurally inspected and cluster margins/effects remain unknown. Model text is never inserted as HTML.

The causal interpretation and any new gate wait for these observations. Re-check every adapter, including the second, under one justified frozen rule before final selection. PR#31 remains a proposal; neither its CPU tests nor a tensor-count check justify relaxing the failed gate.
