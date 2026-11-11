# Evidence-kind annotation audit (2026-11-10)

Scope: training-company records only (1,155; no development, final-test or test-set-2 record). v1 labels in
`data/dossier/evidence.json` are unchanged.

**What the labels mean.** `type` records the origin (company_claim / verified_observation); `kind` mostly records the
nature of the quoted claim (e.g. ResMed investor relations: market_fact; Wikipedia on a law: regulation). The corrective
classify instructions of pilots 1–3 said the opposite ("from what the source is, not what it says"), which explains part
of their low acceptance. Guide: `docs/EVIDENCE_KIND_GUIDE.md`.

**Consistency.** 59 of 89 publishers with at least 3 records carry more than one kind; much of that is legitimate (one
publisher prints different claims), some is not. 44 records use kinds outside the tool's six (product_fact 13,
company_history 13, channel_fact 11, financial_context 7) that no answer can match.

**Blind independent labels** (an independent model annotator with the guide, without v1 labels; advisory):
60 records stratified by kind (`sample_blind.json`, `sample_key.json`, `sample_independent_labels.json`).
- 45 / 60 the same label (75%); 5 more where the annotator lists v1 as also defensible (50 / 60, 83%).
- 10 disagreements: 2 are off-list v1 kinds; 3 high-confidence likely v1 errors (a patent's government-funding note as
  regulation; a patent-expiry encyclopedia fact as regulation; a company scientist describing its own research as
  customer_observation); 5 medium-confidence ambiguities, mostly trade press between market_fact, customer_observation
  and company_assertion.

**Overlay v2 (proposed, not reviewed):** `data/dossier/evidence_kinds_v2.json`, 81 records: the 44 off-list kinds mapped
by the guide, and 37 audit-sample records with their acceptable set (v1 kept as the kind, the 3 high-confidence
disagreements marked `proposed_correction`). Used only by the development measure `evidence_kinds_v2`
(`strategy_agent.evaluation.grounding_v2`), reported beside the unchanged `evidence_kinds`.

**Conclusion for V2 data.** Classification examples are not expanded (two pilots without improvement, and a label
noise of roughly 1 in 5 limits what matching the annotation can teach). The 7 kept classify answers go to review as they
are; the reviewer should prefer those whose kind is right under the guide, not merely equal to v1.
