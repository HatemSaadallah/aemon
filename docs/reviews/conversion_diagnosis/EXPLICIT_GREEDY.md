# Explicit greedy diagnostic, 2026-11-06

Hatem requested one rerun with explicit controls. Both on/off arms now use one profile, matched_raw_greedy. The historical/default-driven legacy_like profile is no longer executed.

Transformers: num_beams=1, do_sample=False, repetition_penalty=1.0, temperature=1.0, top_k=0, top_p=1.0. The inherited config is copied, these controls override it, and remaining unset values resolve through the library's global defaults. Original config values remain recorded in the header and each trace; the effective config and beam count are separate fields. EOS/BOS/PAD are preserved.

llama.cpp completion and distribution requests: temperature=0, top_k=1, top_p=1, min_p=0, repeat_penalty=1, presence_penalty=0, frequency_penalty=0, post_sampling_probs=false. Exact requests, /props and returned generation settings are retained. Numerical comparisons still use raw pre-sampling probabilities, not a top1-renormalized distribution. Missing returned settings are unknown, not fabricated effective settings.

Owner submits one rerun, second then third, after the current teacher batch completes, with fresh output names and the identified archived rows. ACK_RECONSTRUCTED remains explicit. Keep the old partial results. Conversion remains unqualified until numerical evidence is assessed; no tolerance changes in this revision.

Training boundary per Hatem and DECISIONS e18d86c: final training can start when collection closes and its training/data gates pass. Conversion must be resolved before interpreting converted-model evaluations or releasing GGUF. If native PEFT evaluation is used instead, compare base and adapter under the same Transformers runtime, protocol, prompts and budgets; record this as the native-runtime evaluation, and do not attribute it to GGUF. The reported158 investigations/3484 training/411 validation/51 correction rows and0.35% correction tokens are Claude's accounting, not independently audited by this code change. Request provenance in#25 remains a separate outstanding item.
