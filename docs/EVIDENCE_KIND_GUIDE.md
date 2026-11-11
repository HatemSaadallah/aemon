# Evidence kinds: annotation guide (v2 proposal, 2026-11-10)

The dossier records two different things about a source, and they must not be confused:

- **Origin** (`type`): who is speaking. `company_claim` = the company or its people (website, press release,
  investor relations, interview). `verified_observation` = a third party whose text was checked against the live
  source. This is what the evidence-class check and the "independent source" question use.
- **Kind** (`kind`, the `evidence_kind` the agent writes in `assess_evidence`): what the quoted passage establishes,
  whoever publishes it. A trade article quoting the CEO's plans is a `company_assertion`; a company's investor
  report giving a market size is a `market_fact` from a company origin.

Annotation v1 (in `data/dossier/evidence.json`) mostly follows this rule but not always, and 44 records use kinds the
tool cannot express. v1 stays unchanged: the frozen evaluations and the `evidence_kinds` check use it.

## The six kinds (the tool's list)
Decide from the **claim in the quoted passage**, in this order. Use the first one that fits.

1. **regulation**: a law, standard, certification, official approval or ruling, or an authority's recommendation
   (e.g. a regulator recommending a product move from prescription to over the counter).
2. **independent_study**: the result of formal research or testing by a party with no stake: a peer-reviewed or
   published study, a systematic review, a government or laboratory test, a consumer-testing organisation's
   ratings. A news report of a study is still independent_study if the passage gives the study's result.
3. **customer_observation**: what customers or users did, bought, said or complained about, including reviews by
   users, survey results about customers, sales to a named customer group, and adoption described from users' side.
4. **company_assertion**: the company or its people describing itself, its products, intentions, plans or
   performance, whether published by the company or quoted by someone else.
5. **analogy**: a different company, product, market or period, offered as a parallel to this decision.
6. **market_fact**: any other fact about the market, product, technology, channel, history or finances reported
   as fact (encyclopedias, news reporting, patents, histories, extension leaflets, field reports).

The four v1 extra kinds map to the tool's list as follows. They are facts that aren't the company's own claims:
- **product_fact** becomes **market_fact**;
- **company_history** becomes **market_fact**;
- **channel_fact** becomes **market_fact**;
- **financial_context** becomes **market_fact**.

The exception is a record whose origin is the company: classify it by rule 4 if it describes the company's own plans
or performance.

## Where more than one label is defensible
A record's excerpt can hold several claims, and the agent quotes part of it. When the excerpt clearly contains two
kinds (for example a trade article with a market figure and a quoted company plan), the v2 overlay lists both as
acceptable. The quoted words decide which one applies. Ambiguity is recorded, never resolved by guessing.

## How v2 is used
- `data/dossier/evidence_kinds_v2.json` is an overlay for training and development records only: the corrected kind,
  any other acceptable kinds, and the reason for each change. Frozen-test records are not in it.
- Corrective classification examples, and a development-only `evidence_kinds_v2` measure, read the overlay. The
  original `evidence_kinds` check and every reported number keep using v1, so earlier results stay reproducible.
- Every v2 change comes from the audit in `reports/annotation_audit/`. It is proposed for review, not adopted
  silently.
