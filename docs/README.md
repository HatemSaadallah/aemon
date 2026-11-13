# Documents

Start with the [README](../README.md) and the [paper](PAPER.pdf). Everything below is supporting material, grouped by
what it is for. Plans marked *registered* were fixed before the runs they describe, and are left as written.

## The result and how it was measured
| Document | What it is |
|---|---|
| [LATER_WORK.md](LATER_WORK.md) | Everything built and tried after the frozen tests (exploratory): version 3, adapter switching, the status check, loop guards, evidence first, what failed |
| [DECISIONS.md](DECISIONS.md) | Every decision, dated, with the numbers it rested on: the full history of the project |
| [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md) | How the agent is evaluated: frozen test sets, blind judges, paired comparisons |
| [RUBRIC.md](RUBRIC.md) | The quality rubric the judges score against |
| [final_test_freeze.json](final_test_freeze.json), [test2_freeze.json](test2_freeze.json) | Digests of the two frozen test sets, fixed before their single runs |
| [FINAL_TEST_DIAGNOSIS.md](FINAL_TEST_DIAGNOSIS.md) | Why the fine-tuned agent still fails some mechanical checks on the first test |
| [RELIABILITY_REPORT.md](RELIABILITY_REPORT.md) | The reliability audit and the verification layer |
| [RECOVERY_REPORT.md](RECOVERY_REPORT.md) | The failure-aware recovery experiment, final report |
| [replays/](replays/README.md) | Every test run, browsable as text: base and fine-tuned side by side |

## The model, the data and the code
| Document | What it is |
|---|---|
| [MODEL_CARD.md](MODEL_CARD.md) | The model card: what it does, how it was trained, limits |
| [DATASET_CARD.md](DATASET_CARD.md) | The dataset card: training rows, dossier, cases, evaluation artefacts and licences |
| [ARCHITECTURE.md](ARCHITECTURE.md) | How the code is organised |
| [SPEC.md](SPEC.md) | The project specification |
| [TRACK3.md](TRACK3.md) | The hackathon track: what is asked, and how this project fits |
| [EVIDENCE_KIND_GUIDE.md](EVIDENCE_KIND_GUIDE.md) | The annotation guide for evidence kinds |
| [terms/](terms/) | The terms of a teacher service, as read when it was used |

## Plans registered before runs
| Document | What it is |
|---|---|
| [V1_FREEZE.md](V1_FREEZE.md) | The submitted system, frozen |
| [FINAL_EVAL_PLAN.md](FINAL_EVAL_PLAN.md) | The final evaluation plan |
| [V1_1_PLAN.md](V1_1_PLAN.md), [VERIFY_EVAL_PLAN.md](VERIFY_EVAL_PLAN.md) | Two runtime interventions on version 1, each fixed before its run |
| [V2_PLAN.md](V2_PLAN.md), [V2_CORRECTIVE_PLAN.md](V2_CORRECTIVE_PLAN.md) | Version 2 plans (version 2 stopped at its screen) |
| [RECOVERY_EXPERIMENT.md](RECOVERY_EXPERIMENT.md), [RECOVERY_PILOT.md](RECOVERY_PILOT.md) | The recovery experiment and pilot |
| [CORRECTIVE_DISTILLATION_PROPOSAL.md](CORRECTIVE_DISTILLATION_PROPOSAL.md), [RETRIEVAL_PROPOSAL.md](RETRIEVAL_PROPOSAL.md) | Proposals reviewed and not run |

## The app
| Document | What it is |
|---|---|
| [DESIGN_RESEARCH.md](DESIGN_RESEARCH.md) | The design research the app follows |
| [AEMON_REDESIGN.md](AEMON_REDESIGN.md), [STRATEGY_LAB_UI.md](STRATEGY_LAB_UI.md) | Interface redesigns |
| [REASONING_MAP.md](REASONING_MAP.md) | The reasoning map view |
| [COMPANY_PROFILES.md](COMPANY_PROFILES.md) | Company profiles in the app |

## Background
[ABSTRACT.md](ABSTRACT.md) is a short abstract. [reviews/](reviews/) holds reviews and handovers made during the work,
[archive/](archive/) older documents kept for the record, [history/](history/) the commit maps between the working and
public repositories, and [briefs/](briefs/) the prompts used to start the work.
