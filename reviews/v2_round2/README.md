# Version 2, second round: review of the third batch

`targeted3_kept_for_review.md` holds the 5 answers (of 54) kept by the gates after the offline re-check. Three
independent advisory reviews (Claude agents, each with a different lens, none shown the others' or the author's view)
assessed them. They advise; Hatem decides which examples, if any, train.

| Example | Experimental design | Strategy and decision | Evidence and period |
|---|---|---|---|
| Andis (present day) | drop | drop | fixable, minor |
| Cree (2012) | fixable (re-ask) | drop | drop |
| Cotral (present day) | drop | drop (closest to fixable) | fixable, minor |
| Embrace (2016) | drop | drop | drop |
| Black & Decker (1977) | drop | drop | drop |

No example is kept by all three; Embrace and Black & Decker are dropped by all three. Shared findings: the test arms
differ in a label or a label bundled with price rather than in the product (4 of 5); one rival explanation is a foil
the teacher itself calls unsupported (Embrace, Black & Decker); every winning branch goes straight to developing a
proposition; and the teacher was never shown source dates, so it stamped the case's year on later facts (Black &
Decker's "B&D market research, 1977" comes from a 2019 source; € in 1977).

**Re-checked with the third round's screens (2026-11-08):** of the 5 above, Cree, Embrace and Black & Decker are now
refused (a rule that jumps to developing a product, or message-only arms); `targeted3_kept_for_review.md` now holds the
2 that still pass (Andis, Cotral).

**Second batch** (`targeted4_kept_for_review.md`): the 35 states where version 1 reread sources in the test stage, one
answer each; 35 valid, 4 kept at generation, 4 still kept after the offline re-check with every current screen (ARRI,
Superior, Hilti, Technogym). Not yet reviewed by the advisory agents.

Review either batch in the Strategy Lab's **Review** page (Keep or Drop, with a note), which writes the decision into
the `.json` file beside each `.md`. Only examples marked Keep can train.
