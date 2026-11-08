# Advisory review: experimental design (Claude agent; advice only, Hatem decides)

**Verdicts: Andis DROP, Cree FIXABLE, Cotral DROP, Embrace DROP, Black & Decker DROP. None of the five is fit to train on as it stands.** I only read files; nothing in the repository was changed. Power figures come from a binomial simulation with 200,000 draws per scenario (`/tmp/claude-1000/-home-hatem-Desktop-lexsi-ai-hackathon/e2c37e73-91ee-41f6-8d67-ac5bfa091a72/scratchpad/power.py`).

### 1. Andis — DROP
- **The two kits differ only in label, and one label already exists.** why_next calls them "premium‑branded vs. convenience‑branded". The Premium kit restates Andis's current line ("Pro-Level Tools. At Home Confidence."). There is no "neither" option and no existing kit to compare against, so the test cannot show demand beyond the current range, which is the decision being asked.
- **The price comparison is biased.** People state a price only "for the chosen kit", so the two averages come from self-selected groups. A "premium" label raises stated prices by itself, so T1's branch wins by construction.
- **The deposit decides nothing.** The €5 refundable deposit is not in the decision rule. Both theories predict the same ">70%" conversion. No purchase is ever observed; the follow-up is a survey.
- **The thresholds contradict each other.** The predictions say +20% for T1 and +15% for T2, but the rule says +10%. A +12% gap with 56% choosing Premium triggers "developing" while contradicting both predictions. This 20/15 asymmetry was flagged last round and is repeated.

*Ideal:* offer the existing $59.99 kit against kits that differ in a real attribute (pro-grade motor vs guided guards with a tutorial), at matched prices, plus "neither", on a real store listing. A win leads to a limited production run.

### 2. Cree — FIXABLE (the closest to sound)
- **The core is good.** The theories are genuine rivals with different actions (cut the price vs invest in quality). It asks for a real commitment, the rule covers every outcome, and the cost is credible (€45 per participant).
- **Price and message change together.** A lower price raises conversion under either theory, so both theories predict that the low-price arm wins.
- **T2's prediction does not follow from T2.** Valuing quality means being willing to pay more for it, not converting more at $60 than at $30. T2's real signature is a premium message making up for a doubled price. That result falls into the "<10 points → qualitative research" branch.
- **The low-price arm does not test T1.** $30 is not "comparable to incandescent", which cost about a dollar in 2012.
- **The fixed 10-point bar is weak.** It is reached 50% of the time when the true rates are 20% vs 10%, and under 1% of the time at a realistic 8% vs 4%.

*Fix:* add a plain arm at $60, or run a 2×2 of price × colour quality that buyers can see, with real bulbs on sale. Use a relative threshold or a significance test, and send a win to a retail pilot rather than to "develop".

### 3. Cotral — DROP
- **The theories are not rivals.** They describe two segments, and both can be true. The rule's own branch "develop … both segments" admits this.
- **The contrast only checks that the framing reached people.** Musicians preferring the musician message is expected under any theory. This was flagged last round and is repeated with a deposit added.
- **The rule ignores that contrast.** It compares only the matched groups with an absolute 30%, so 200 of the 400 participants never inform the decision.
- **The bar is set at the predicted rate.** With 100 per group (±9 points), a true 30% clears it 54% of the time and a true 25% only 15%. A realistic rate for a cold deposit offer (5–15%) never clears it, so the test says "decline" whichever theory holds.
- **It ignores its own evidence.** It cites the 2015 study (comfort and looks beat sound quality), then frames the musician offer on sound anyway. It also leaves out the ear impression, the real hurdle for a custom plug.

*Ideal:* sell the same €150 product, with each segment seeing only its own message, and measure paid bookings for ear impressions. Within musicians, vary what the 2015 study questions (a fidelity filter vs a comfort shell). A win leads to a pilot with one partner.

### 4. Embrace — DROP
- **It measures stated preference only, and never says what a survey cannot show.** The state already has a real sales channel: Little Lotus products sold on the company website, which "decreased in price from $98 to $85". The teacher dismisses this as "a different product".
- **Price and positioning are bundled.** This was flagged last round and is unchanged. The sample (parents on US and Indian forums) is also not the low-resource population T1 is about.
- **The rule breaks.**
  - If option (a) reaches 30% and option (b) reaches 20%, both predictions hold and no clause applies. Read as "otherwise", the rule declines when demand is strongest. With true shares of 33% and 22%, 77% of samples land there.
  - At exactly 30% and 20%, both actions fire.
- **T2 is a strawman, and the T1 arm makes an unsafe claim.** In the teacher's own words there is "no evidence" for T2. The T1 arm asserts "reducing SIDS risk", which is stronger than the company's "may even reduce". The source also links SIDS to babies being too warm.

*Ideal:* set T2 aside and run a real-purchase price test of one product, with no health claim. Run it through the existing web shop, or through clinics for the parents T1 names. A win leads to a pilot.

### 5. Black & Decker — DROP
- **The deposit is non-refundable, on a mock-up of a product the rule may cancel.** That is ethically untenable. It is also priced at "€50" in 1977, before the euro existed; as dollars, that is over $250 today.
- **The deposit decides the outcome.** At the predicted 15-point gap (30% vs 15%), the rule says "proceed" 49% of the time. At a realistic 20% vs 5%, which is significant in 92% of samples, it says "proceed" 1% of the time. The 30% floor turns a clear T1 win into "no expansion".
- **The arms differ only in framing.** One reads "always charged, ready to use", the other "high-performance, status symbol". The teacher found "no evidence … for status/prestige motivation", so T2 loses by construction.
- **The sample is screened on past adoption.** Requiring people to already own a cordless tool excludes the buyers the proposition targets. How people are assigned to the two arms is not stated.
- **The rule is lopsided, and one date is invented.** A convenience win leads to "develop", a prestige win only to "explore". The citation "(B&D market research, 1977)" gives a date the 2019 source does not.

*Ideal:* use methods available in 1977, such as split-run mail-order coupons or a test market in a few stores. Sell real tools at the same price, one stored on its charger and one standard, and measure paid orders. A win leads to a regional test market.

### Overall
**0 of the 5 are fit to train on.** Cree can only be fixed by asking the teacher again. The training rows are the teacher's hashed replies, so FIXABLE means re-ask, not edit.

**The most important pattern: a real commitment was added to the measure, but what differs between the arms is still a label, or a label bundled with price.** Andis and Cotral came back with last round's design plus a deposit; Embrace came back unchanged. As a result:
- **The predictions don't come from the theories.** They come from "people pick the matching or cheaper offer".
- **The thresholds sit at the effect size itself.** They are absolute: Andis 55%, Cotral 30%, Cree 10 points, Black & Decker a 30% floor. A true effect of that size triggers the rule about half the time, and realistic commitment rates almost never.
- **Every winning branch goes straight to development.** The only exception is Black & Decker's "explore". The keyword flag meant to catch this missed Cotral and Embrace.

The existing flag "the arms differ in framing or message" already marks 4 of the 5. Turned into a refusal unless the design has a same-price control or a 2×2, it would catch those four. It would catch Andis as well if it also read why_next.
