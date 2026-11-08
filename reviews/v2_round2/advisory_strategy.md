# Advisory review: strategy and decision value (Claude agent; advice only, Hatem decides)

**Verdicts:** none of the five is fit to train on. All five are DROP, though Cotral comes closest to fixable. I read each state exactly as the teacher saw it (from `/home/USER/lexsi-backup/cluster/teacher/capv2_targeted3.json`), and the case premises in `data/dossier/evidence.json`.

**1. Andis: DROP**
- **It tests the wrong choice.** The question is "further differentiated proposition … or concentrate on professional barbers". The design is a forced choice between two new kits. It has no "neither" option, no existing $59.99 inCRED kit and no $20 Amazon clipper, so one concept wins whatever the demand. "Otherwise … focus on professional segment" fires when the two concepts tie, which says nothing about the professional business.
- **T1 is the status quo.** The state quotes the home line as "Pro-Level Tools. At Home Confidence." The only customer evidence ("clippers for about $20 from Amazon … than one haircut") points to saving money. That is the rival which favours the professional business, and neither theory states it.
- **The deposit is decoration.** The rule reads only the choice share and stated willingness to pay (WTP). The €5 deposit never enters it, and both theories predict the same "deposit conversion >70%". WTP is asked only "for the chosen kit", so the two averages come from self-selected groups.
- **The thresholds drift:** 20% and 15% in the predictions, 10% in the rule. Gemini flagged this same defect on Andis last round. The cost is exactly €20,000 and 12 weeks, though only €4,500 is itemised.
- *Ideal:* test one new proposition grounded in the state against the existing kit and a no-buy option, using paid pre-orders. The state's "preferred brand for textured hair" suggests a textured-hair kit. A win leads to a limited run, a loss to concentrating on professionals.

**2. Cree: DROP**
- **The price anchor is wrong.** It calls $30 "price comparable to incandescent". Incandescent bulbs cost about a dollar, and the state says LED alternatives already "sell for less than half" the $50 prize-winning bulb. The "low-price" arm is above the market.
- **The result is settled before the test runs.** Price and message move together, and T2 has to predict that a $60 bulb with premium copy beats a $30 one. T1 wins by construction, so the test cannot change the decision.
- **There is no exit.** Every branch is "develop low-price", "develop premium" or "further qualitative research". Staying a component and fixture supplier, the main alternative, is never an outcome.
- **The theories are about the category, not Cree.** They explain why consumers adopt LEDs. The state shows Cree already supplies Home Depot's EcoSmart line, so the real issue is its own brand versus supplying others (margin, conflict with customers). No "specific use case" is named.
- *Ideal:* say the state already points to price, and that whether an own-brand bulb is worth the channel conflict is not a consumer-motive question. Either decline on that ground, or test one bulb at two or three prices with the existing retail partner, with a "stay a supplier" branch.

**3. Cotral: DROP (closest to fixable)**
- **It has the best rule of the five:** an absolute 30% bar per segment, real money, and "neither → focus on existing B2B". But a win still means "develop differentiated propositions for both segments" on 100 people per cell.
- **The predictions are not rivals.** Musicians preferring musician copy and sleepers preferring sleep copy can both be true. Gemini named this same tautology for this case last round. The 200 people in the mismatched-copy cells feed nothing the rule reads.
- **It ignores its own evidence.** The teacher notes that appreciation "mainly depended on comfort and looks" (Bockstael), then frames the musician arm as "sound-preserving".
- **It skips the real constraint.** Cotral takes impressions "directly on-site" for employers. A web deposit for a custom-moulded plug "delivered within 8 weeks" never says how a consumer gets an impression, so it overstates demand. Making the promised units is not costed in a budget spent to the euro, and there is no comparison with a universal-fit plug (Minuendo is in the state).
- *Ideal:* matched offers only, with the impression step included through a partner such as an audiologist or music shop. Frame the musician offer on comfort and fit, compare it with a universal-fit plug, and count paid orders. Success leads to a partner pilot.

**4. Embrace: DROP**
- **It misses the case premise.** Embrace already sells a consumer product built on the same technology: Little Lotus swaddles on its website, "recently decreased in price from $98 to $85". The teacher waved it off as "a different product". That price cut is the most decision-relevant fact in the state.
- **The rival is a strawman.** It proposes a "fashion accessory … status symbol" for premature, low-birth-weight babies in low-resource settings, while conceding "no evidence shows a fashion- or status-driven demand". T1 borrows its SIDS claim from the swaddle article.
- **Last round's confound is back:** price ($80–90 against "$120‑30") moves with positioning. The sample is US and Indian parenting forums, which do not reach T1's population. It measures stated choice only and never says what the survey cannot show, which the teacher's instructions required.
- **The rule is broken.** At 35% and 25% no branch fires; at 30% and 20% both do. T2 wins at 20% while T1 needs 30%. The win branch is "proceed with … consumer proposition" for a neonatal medical device.
- *Ideal:* base the decision on Little Lotus. Run a real-order price or use-case test on the existing site, with a "refocus on the hospital warmer" branch.

**5. Black & Decker: DROP**
- **T2 is a foil.** T1 is grounded: consumers "forget to place the tool's rechargeable batteries back in the charger". But the teacher admits "T2 lacks supporting evidence", and the test is built to beat it.
- **It varies wording, not the product.** The evidence points at a design attribute, where the battery sits between uses. The arms differ only in copy: "always charged, ready to use" against "high-performance, status symbol".
- **It cannot discriminate.** A non-refundable €50 deposit on a mock-up, in a currency that did not exist until 1999, with a 30% bar, makes "no expansion" almost certain whatever the truth. The sample is screened to people who already own a cordless tool, the wrong group for a new use case. "e.g., home DIY" is not a specific use case.
- **The actions are lopsided:** the favoured theory's win means "develop", the foil's win means "explore". The teacher's summary also invents a date ("B&D market research, 1977"; the source gives none) and asserts battery reliability that no source shows.
- *Ideal:* two mock-ups at the same price and copy, one stored on its own charging base and one with a separate charger. Show them to households without cordless tools and take refundable dollar deposits. A clear win leads to a limited run for one task where the cord is the main problem.

**Overall**

None of the five is fit to train on. This round is better than the last in form: four of five ask for money, the rules are written out in full, and four of five include a "no" branch.

The main pattern is that the teacher fills in the task's template rather than the company's decision. The template is two marketing angles, one per theory, a deposit or a survey, and develop whichever wins. Two of the rival theories are foils the teacher itself calls unsupported (Embrace, Black & Decker), and Cree's T2 is set up to lose. In three cases it misses the fact that defines the real decision: Embrace's existing swaddle line, Cree's role as Home Depot's supplier, and Andis's existing "Pro-Level" home line.

Every winning branch commits to developing a proposition. None takes the "pilot, prototype run, partner trial" the instructions named. Three of five spend exactly €20,000 and 12 weeks. None declines, though declining was defensible for Cree. A model imitating these would learn the template, not judgement.

Two notes on the review file itself:
- **The flags undercount.** The "rule leads straight to developing" flag misses Cotral and Embrace, because its pattern needs "develop a/an/the …". The "asks for a real commitment" flag fires on Andis even though its rule ignores the deposit.
- **Andis was refused at generation** (rule of 615 characters against a 600 limit) and kept only on the re-check. Its last two "rule" sentences are budget text, not rule.
