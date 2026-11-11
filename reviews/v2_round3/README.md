# Version 2, third round (job 748005): verified answers for review

Command A+ answered states from version 1's own training-company runs. Before export every saved reply was re-judged by
today's gates (no new sampling), one answer was kept per state, and each answer had to pass provenance (its exact reply
is in the append-only manifest), replay (the student's recorded run rebuilds the exact context the teacher saw) and the
split check (a training case; no development case and no case from either frozen test set).

| batch | states answered | kept at generation | refused by today's gates | passed every check |
|---|---|---|---|---|
| `targeted5e` test design | 178 | 6 | 3 (arms differ only in wording, no product or price difference) | **3** |
| `targeted5w` weighing (assess 3 sources per theory) | 162 answers, 81 states | 60 | 0 (22 later answers to a state already kept were not counted) | **60** |

63 of the 66 answers kept at generation are exported. Review them in the Strategy Lab's **Review** page (Keep or Drop,
with a note); only examples marked Keep can train.
