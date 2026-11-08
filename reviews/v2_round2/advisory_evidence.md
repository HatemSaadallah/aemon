# Advisory review: evidence fidelity and period (Claude agent; advice only, Hatem decides)

I'd keep 2 of the 5 (Andis and Cotral) and drop 3 (Cree, Embrace, Black & Decker). The three to drop are exactly the three cases set in the past.

**Why the teacher's period handling failed:** it was never shown the dates of the sources. `state_of` in `/home/USER/Desktop/lexsi-ai-hackathon/src/strategy_agent/agent/runner.py` lists `sources_read` with only id, class, title and excerpt. The dates in the review file were added later by the export script. So "only facts from sources dated on or before it" could only be applied by guessing from titles. None of the five replies names a single source id, although the instructions ask it to.

### 1. andis (present day): FIXABLE, minor; keepable as is
Nothing is invented, but the evidence is picked selectively.
- **"42% market growth":** andis-wahl-6-million (2021-03-15) actually says "It is up 42% in the last quarter. This is after over 6 million people joined home haircutting… after the lockdowns." That is one lockdown quarter and a competitor's estimate, presented as a current surge.
- **Reversal left out:** andis-wahl-10-percent, in the same state, says "Wahl has seen a large percentage of men go back to barbershops and salons".
- **Only buyer voice left out:** andis-attest-20-dollars says "clippers for about $20 from Amazon". That is a cost motive, which cuts against T1's premium and is not T2's convenience either.
- **T1 is already what Andis sells:** andis-home-line reads "Pro-Level Tools. At Home Confidence", so the "Premium" kit tests the current range, not a new proposition.
- **Prices unused:** no kit price is set, though andis-athome-prices gives $24.99 to $59.99, and US adults pay a "€5" deposit.

### 2. cree-base (late 2012): DROP
- **"price comparable to incandescent, e.g., $30":** nothing supports this, and the state contradicts it.
  - cree-abc-cheaper (2012-03-09) says LED bulbs "comparable to the L-Prize winner sell for less than half its price". The winner was the $50 bulb, so comparable LEDs already sold for under about $25.
  - A $30 arm is above the going LED price and nowhere near incandescent prices, so it cannot test T1.
- **"Cree has introduced low-priced bulbs under $50":** the only product under $50 in the state is cree-pr-ecosmart (2010), "The EcoSmart LED Downlight retails for less than $50".
  - That is a downlight sold under Home Depot's brand. An unread dossier record, cree-fool-brand, says it was "sold under Home Depot's EcoSmart brand".
  - Cree's own cheap bulbs came in March 2013: see the title of cree-ledp-reason (2013-03-06, "…Introduce Price-Barrier-Breaking 40/60 W Equivalent LED Lamps") and cree-wiki-first ("In 2013, the company's first consumer products…").
  - So the claim is either a misdescription or knowledge from after the case date. "Consumer adoption of Cree's LED bulbs" assumes a product that did not exist in late 2012.
- **Methods:** an online panel and a refundable deposit are fine for 2012.
- **Design, outside my lens:** price and message change together, so the cheaper arm wins whatever the real reason.

### 3. cotral (present day): FIXABLE, minor; the cleanest of the five
- **Accurate:** sales mainly to companies (ctl-channel), the Bluetooth model (ctl-it1) and the frequency filters (ctl-filter).
- **"A 2015 study of musicians… comfort and looks drive appreciation more than sound quality":** bockstael-2015-looks says "In this test group… appreciation mainly depended on comfort and looks, while differences in sound quality were less noticeable."
  - It does not say the testers were musicians, and "less noticeable" is about what people could hear, not what they value.
  - This is a mild overstatement, and to its credit the teacher uses the record against T1.
- **Fitting ignored:** ctl-onsite says "The ear impressions of your employees are taken directly on-site." The test promises custom-moulded plugs within 8 weeks to 400 people recruited online, with no way to take their impressions.
- **Unsourced terms:** the €150 price and "medical-grade" (taken from T2) appear in no source. "Medical-grade" is an unsupported claim in an offer that takes real money.
- **Competitor ignored:** minuendo-claim, a specialist product for musicians, bears on T1 and is not mentioned.

### 4. embrace (March 2016): DROP
- **A later source presented as period-valid:** "From public sources up to March 2016… used in B2B settings (e.g., hospitals in India)" and "clinical validation" both rest on embrace-smg-launch.
  - That record reads "Following clinical trials, the Embrace® Nest was launched in 2011 in India, where it is widely used". It is a museum entry for an object made in 2017.
  - "Validation" overstates a museum label. An unread dossier record, embrace-pmc-notrials (2014), says "There have been no published trials of EMBRACE".
- **The SIDS claim is moved and turned into the sales pitch:**
  - embrace-her-sids is the company's own claim about "The €160 swaddling wrap", which "may even reduce the risk of SIDS… linked with babies being too warm".
  - The test offers parents a "medical device reducing SIDS risk".
  - The dossier also holds the AAP's 2011 advice to avoid overheating (embrace-aap-overheating). Today's Safe to Sleep page (embrace-s2s-claims) warns against products that "claim to prevent SIDS". Training on this is harmful.
- **Misreads the state:** it says there is "no direct evidence of consumer sales… nor of demand for a differentiated consumer proposition".
  - But embrace-cnbc-price says "Little Lotus products are available for sale on the company website, and swaddles have recently decreased in price from $98 to $85".
  - That is the existing consumer line the brief asked about, and the price cut bears on both theories.
- **Smaller problems:**
  - Parents recruited on social media are not T1's "low-resource settings".
  - It relies on stated preference without saying what that can and cannot show.
  - There is a "$120‑30" typo.

### 5. blackdecker-base (1977): DROP
- **The central fact is hindsight with an invented date:** the teacher writes "(B&D market research, 1977)".
  - The source is blackdecker-uspto-forget, a 2019 USPTO retrospective: "One reason, B&D's market researchers soon discovered, was that consumers would often forget to place the tool's rechargeable batteries back in the charger". The excerpt gives no date.
  - It was internal research on the Mod 4, launched in 1974 (unread blackdecker-wp-mod4). An outside analyst working from public sources could not have seen it in 1977.
  - It is the insight behind the 1979 DustBuster, and the "always charged, ready to use" arm builds in that known answer.
- **"Reliable enough for a differentiated use case":** this is in no excerpt. The only engineering record, blackdecker-spinoff-motor (1981), is about motor power use.
- **"€50 deposit (non-refundable)" from US shoppers in 1977:** the euro did not exist until 1999. Taking money that cannot be refunded for a mock-up the rule may abandon is a separate problem.
- **Every source read is later than 1977:** 1981, 2019 three times, and an undated page read in 2026.
  - The 1977 records in the dossier (blackdecker-patent-prior and blackdecker-patent-module, a cordless-vacuum patent published 1977-03-15) were never read.
  - The honest move was to say the state holds nothing datable to 1977. The 1961 and 1914 facts are fine in substance.

### What goes wrong across the batch
1. **The case date gets stamped on later facts.** Instead of checking dates, the teacher writes "up to March 2016" and "1977" onto facts from later sources. That teaches the student to make hindsight look legitimate, which is worse than an open leak.
2. **The state has no dates.** Adding `date` to `sources_read` would change the state format that existing training rows must match, so that is your call.
3. **The in-period gate cannot fire.** `gate_case_bounds` in `/home/USER/Desktop/lexsi-ai-hackathon/src/strategy_agent/pipeline/targeted.py` flags a late source only when its id appears in the reply, and none of the five names any source id. Dates like "unknown (object made 2017…)" are skipped. Nothing checks currency (€ in 1977) or price sense ("$30 ≈ incandescent").
4. **Flawed framing comes in with the student's theories.** The SIDS claim, "medical-grade" and the Black & Decker T1 (built from the 2019 source) all come from the student's theories. A better test step cannot repair a theory built on later sources.

None of the five uses the simulated warehouse record (SYN-D), which is correct.
