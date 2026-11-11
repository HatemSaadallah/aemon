# Aemon design research (agent-compiled, with sources; the spec the app follows)

# Aemon: UX research and design spec

## 1. What the research says (key findings)

**Long-running agent work**
- **Show the plan and live progress, and let people stop or steer.** ChatGPT deep research shows the plan before it starts, live progress, an activity log next to a sources list, and lets you interrupt. Its Feb 2026 viewer moved reports out of the chat: contents on the left, sources on the right, export to PDF/Word ([OpenAI help](https://help.openai.com/en/articles/10500283), [LetsDataScience](https://letsdatascience.com/news/openai-updates-chatgpt-deep-research-viewer-8778744e)). Gemini shows an editable plan card with "Start research" ([guide](https://avidopenaccess.org/resource/gemini-deep-research/)). Shape of AI calls these patterns Action plan, Stream of thought and Controls ([shapeof.ai](https://www.shapeof.ai/)).
- **For waits over 10 seconds, show "step X of N", what is happening now, a rough time estimate and a cancel button.** A spinner alone is not enough ([NN/g](https://www.nngroup.com/articles/progress-indicators/)). Agents can't show an honest percentage, so count steps rather than a % bar ([Tian Pan](https://tianpan.co/blog/2026/07/02/why-you-cant-put-a-progress-bar-on-an-agent)).
- **Put the answer first.** Perplexity's order is answer, then evidence, then suggested follow-ups, with numbered citations that open into source cards ([925studios teardown](https://www.925studios.co/blog/perplexity-design-breakdown)). This is also NN/g's inverted pyramid ([NN/g](https://www.nngroup.com/articles/inverted-pyramid/)) and Minto's "answer first, grouped reasons below" ([Management Consulted](https://managementconsulted.com/pyramid-principle/)).
- **Citations: put each one next to the claim, name it by title, link to the passage, and say plainly "check these".** Put that warning near the input box. Don't present step-by-step reasoning as if it were a faithful explanation ([NN/g explainable AI](https://www.nngroup.com/articles/explainable-ai/)). In NN/g's diary study, users rarely checked answers ([NN/g](https://www.nngroup.com/articles/generative-ai-diary/)), so quotes have to be visible without clicking.
- **NotebookLM:** hovering a citation shows the quoted passage, it suggests follow-up questions from the sources, and its mind map has collapsible branches where clicking a node asks the chat about it ([Google support](https://support.google.com/notebooklm/answer/16179559?hl=en), [mind maps](https://support.google.com/notebooklm/answer/16212283?hl=en)).

**Memory**
- **Precedents:**
  - ChatGPT shows a "Memory updated" notice linked to "Manage memories" ([OpenAI](https://openai.com/blog/memory-and-new-controls-for-chatgpt)). It now uses an editable memory summary plus saved items ([Memory FAQ](https://help.openai.com/en/articles/8590148-memory-faq)).
  - Claude keeps a separate memory per project, lets you view and edit it as a summary, and has incognito chats ([Claude blog](https://claude.com/blog/memory), [help](https://support.claude.com/en/articles/11817273)).
  - ChatGPT Projects offer project-only memory, set when the project is created ([TechRadar](https://www.techradar.com/ai-platforms-assistants/chatgpt/chatgpt-project-only-memory-is-live-and-it-might-change-how-you-work-with-ai)).
- **What confused users:**
  - Memories saved that they never asked for, or got wrong.
  - "Memory updated" shown when memory was full and nothing was saved.
  - Controls that disappeared from settings.
  ([forum](https://community.openai.com/t/chatgpt-plus-plan-memory-issue-no-warning-when-memory-is-full-leading-to-lost-entries/1111613), [forum](https://community.openai.com/t/memory-management-system-creates-unwanted-memories-without-permission/1245049))
- **What this means for us:** ask before saving, never claim a save that didn't happen, and always show which memory is being used. This matches PAIR's advice to tell users what data is used and how to remove it ([PAIR](https://pair.withgoogle.com/chapter/explainability-trust/)).

**Uncertainty and numbers**
- **PAIR:** prefer categories (high/medium/low), each with a stated action. Numeric confidence is risky for non-experts. Skip fine-grained values that wouldn't change a decision. Show alternatives when confidence is low ([PAIR](https://pair.withgoogle.com/chapter/explainability-trust/)).
- **Words alone are read inconsistently.** People translate "likely" into very different numbers; adding a rough numeric range narrows that ([Wintle et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6469752/)).
- **Precise numbers make the speaker look more confident than they are** (2,611 reads as more confident than 2,600) ([APS](https://www.psychologicalscience.org/news/were-only-human/precisely-right-no-doubt-trust-me.html)). Round, or use words.
- **Error bars and intervals are often misread by lay readers** ([Kale, Kay, Hullman](https://arxiv.org/pdf/2007.14516v3.pdf)).
- **Encode quantities with length and position, not area, angle or colour; avoid pie charts** ([NN/g](https://www.nngroup.com/articles/dashboards-preattentive/)).
- **Chart types that fit:** arrow plots for showing change, bullet charts for planned vs actual ([Datawrapper](https://www.datawrapper.de/blog/new-arrow-and-range-plots)).

**Mind map**
- **Use a left-to-right tree, not radial.** In an eye-tracking study, conventional and orthogonal tree layouts beat radial ones ([Burch et al.](https://api-pubmed-ncbi.laibokeji.com/22034365)).
- **Avoid force-directed layouts.** They turn into a "hairball"; people end up using local, colour-coded views instead ([discussion](https://forum.zettelkasten.de/discussion/comment/16703/)).
- **Precedents:** MindNode defaults to a horizontal layout with folding and a focus mode ([MindNode](https://www.mindnode.com/support/guides/focus-mode)). Collapsible tidy trees are the standard pattern ([UW lecture](https://courses.cs.washington.edu/courses/cse442/18au/lectures/CSE442-Networks.pdf)).
- **For about 10–100 nodes across 3–4 levels:** a horizontal tree with collapsing, focus mode and search.

**Visual trust and accessibility**
- About half of the participants in Stanford's credibility study cited design or "look" when judging a site ([Stanford/Fogg](https://clickz.com/study-for-site-cred-looks-matter/56564/)).
- Keyboard focus must not be hidden by other content (WCAG 2.2, 2.4.11), and indicators need 3:1 contrast ([TetraLogical](https://tetralogical.com/blog/2023/10/05/whats-new-wcag-2.2)).
- Plain English is the default; aim for short sentences ([GOV.UK](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/clear-language/)).
- Empty states should explain the state, teach the feature and link to the next action ([NN/g](https://www.nngroup.com/articles/empty-state-interface-design/)).
- Keep lines to 45–90 characters ([Butterick](https://practicaltypography.com/line-length.html)).
- Okabe–Ito colours are safe for colour-blind readers ([ref](https://rdrr.io/github/rstudio/thematic/man/okabe_ito.html)).

---

## 2. Top 10 changes by impact

1. **A result page that opens with the answer**, replacing the workflow canvas as the main view. The canvas moves to a collapsed "How we got here" section.
2. **Plain-language glossary applied everywhere** (section 9). Hide "harness", "adapter", "refused", model and build strings.
3. **A progress view with a 7-step plan**, "Step 4 of 7", elapsed time, "usually 2–3 minutes", a Stop button, and a 5-line live activity feed.
4. **A follow-up box pinned to the bottom of the reading column**, with 3 suggested questions and answers that cite this investigation's sources.
5. **Four small SVG charts:** explanations compared (how likely, and how it moved), evidence for and against, source mix, and test cost vs budget plus predictions.
6. **Download PDF**: a print route with a one-page executive summary first.
7. **Navigation cut to three items:** Investigate, Mind map, How it works. Math, Results and Training go behind `?dev=1`.
8. **Memory you can see and edit** (company + project), shown as a "Using memory" chip in the composer and saved only after you confirm.
9. **Mind map tab**: horizontal collapsible tree, focus mode, search, keyboard tree navigation.
10. **New visual tokens** (palette, type, elevation), empty states and a first-run card.

---

## 3. Information architecture

```
Top bar: [Aemon] [Company ▾]   Investigate · Mind map · How it works   [Memory] [Account ▾]
```
- The "Research prototype" tag becomes a quiet grey "Prototype" chip.
- **Memory** opens a right drawer (section 6).
- **How it works** is a short page for managers: the 7 steps, where sources come from, limits. The current developer content goes under `?dev=1`.
- **Routes:**
  - `/investigate`, `/investigate/:id`, `/projects/:pid`
  - `/map`
  - `/report/:id` (print)
  - `/how`

---

## 4. Investigate page

**Grid:** replace the 3-column `.studio` with `264px | minmax(0,1fr)`. The right panel becomes an **on-demand drawer** (420px, overlaying, closes with Esc) for one source, one step, or memory. Content sits in a **reading column of at most 760px**, centred.

**Left sidebar**
- "+ New investigation" (primary)
- Search box
- Pinned
- Projects: clicking a project opens its overview page
- Recent (renamed from "History")
- Row meta in plain words: "Finished · 3 Nov", "Stopped early", "Running…". Drop "N steps".

### 4a. Before a run (empty state)
- H1 (24px): **"What decision are you facing?"**
- Large composer (4 rows). Placeholder: *"e.g. Should Hellberg sell hearing protection to consumers?"*
- Under the input:
  - Chip: **"Using: 3 company notes · 2 project notes"**. Clicking it opens a popover listing them, each with an Edit link.
  - "Options ▾" disclosure holding *"Search the live web (experimental)"*.
  - Notice next to the input (per NN/g): *"Answers are built only from the sources shown with each claim. Read the quotes before acting."*
- Button: **"Start investigation"**, plus the hint "Takes about 2–3 minutes".
- "Try one of these" example cards (2×2 grid) with a one-line description each. What-ifs go in a separate group titled **"What if new evidence appeared?"** with a "Simulated" chip.

### 4b. During a run
- **Header:** question (20px) and company; on the right, **Stop**.
- **Progress card:**
  - Title: "Step 4 of 7 · Weighing the evidence"
  - Elapsed time, plus "usually 2–3 minutes"
  - A horizontal stepper of 7 dots with short labels. This reuses `JourneyMap` with the plain labels from section 9.
- **"What it's doing"**: the last 5 activity lines, newest on top, fading in. Examples:
  - "Read *EU hearing protection market 2024* (independent)"
  - "Noted evidence **for** 'Comfort for long wear'"
  - "Not accepted by the checker; it changed nothing and is trying again" (muted)
  - Link: "Show every step" expands the existing `WorkflowCanvas`.
- **"Explanations so far"**: the explanation cards appear live as they are added (data comes from `TheoryBoard`).
- **When it finishes:**
  - Set `document.title` to "✓ Done – …".
  - Show a toast: "Investigation finished · View result".
  - Optionally use the Notification API, if the user allowed it.

### 4c. After a run (top to bottom)
1. **Header row:**
   - Question, company, date.
   - Status chip: "Finished", or "Stopped early: it ran out of time".
   - Actions: **Download PDF**, Pin, Move to project, ⋯ menu (Run again, Delete).
2. **Recommendation card** (the visual hero; `--accent-wash` left border):
   - Kicker: "Our recommendation"
   - The recommendation sentence in 20px semibold.
   - Confidence chip: **High / Moderate / Low confidence**, followed by a "Why:" line taken from `uncertainty`.
   - Next step: `next_action`, with the cost and weeks of the test when one is proposed.
   - "What would change our mind": up to 3 bullets.
   - Category actions (PAIR): Low means "Treat as a hypothesis; run the test before committing". Moderate means "Reasonable to act on small, reversible steps". High means "Evidence is consistent; check the quotes, then act".
   - Derive the category openly. The leading explanation's belief, *very likely* or *likely*, with at least 2 supporting independent sources, gives High or Moderate; anything else gives Low. Show the rule in a tooltip.
3. **At-a-glance tiles** (3–4):
   - "4 explanations compared"
   - "12 sources · 8 independent"
   - "Test: €5k of €20k · 2 weeks"
   - "Leading: Comfort for long wear"
   - Exact counts are fine. Never show a % for belief.
4. **"Why customers might buy: explanations compared"**: chart A plus chart B per row. Clicking a row expands it to show the quotes, each with a source chip.
5. **"Where the evidence came from"**: chart C, then the source list. Each source is a card with the title as the link, a class chip (Independent / Company's own claim / Simulated), date, and the quoted excerpt. Hovering an inline citation `[3]` anywhere shows the quote.
6. **"The test we propose"** (or "Why a test isn't worth it"): chart D, the predictions table, and the decision rule in a highlighted box: **"How we'll decide: …"**.
7. **"How we got here"** (collapsed): the challenge summary, then "Show every step (for reviewers)", which opens the existing canvas.
8. **Follow-ups:**
   - A thread renders below section 7.
   - The composer is **sticky at the bottom** of the column. Placeholder: *"Ask a follow-up about this investigation"*.
   - Above it go 3 suggested chips generated from the result, for example "What's the cheapest way to test this?", "What if a competitor launches first?", "Explain the leading explanation to my CEO."
   - Each answer ends with "Based on: [3] [7]".
   - If the answer isn't in the investigation's sources: *"That isn't covered by this investigation's sources. Start a new investigation on it?"* with a button.

---

## 5. Charts (plain SVG/CSS, about 40–80 lines each)

**Data rule:** beliefs are verbal (`very unlikely…very likely`). Keep the words and add the rough range only as a hint, as the IPCC does: "likely (roughly 2 in 3)".

- **A. How likely each explanation is.** A five-column labelled scale, one row per explanation. A hollow dot marks the first stated view; a filled dot marks the final one, with an arrow between them (arrow plot). The leading explanation gets a "Leading" chip. The row's aria-label reads, for example, "Comfort: moved from uncertain to likely."
- **B. Evidence for and against.** A diverging bar from a centre line: against on the left in `--against`, for on the right in `--support`, with the count at each end and "+" and "−" glyphs so colour isn't the only cue. Neutral is a grey count in text only.
- **C. Source mix.** One 100% horizontal stacked bar with direct labels: "8 independent · 4 company's own claims · 1 simulated". Company claims get a diagonal hatch (`repeating-linear-gradient`). No pie (NN/g).
- **D. Test cost vs budget.** A bullet bar: a grey track for the budget, a filled bar for the cost, labelled "€5,000 of €20,000 budget". A second mini bar shows weeks against the maximum weeks.
- **Predictions table.** One row per explanation with the header "If this is right, we'd expect…". The decision rule sits below it, with the threshold value shown on a small number line when it is numeric.
- Use `font-variant-numeric: tabular-nums` and round euros ("€5k" in tiles, the exact figure in the test card).

---

## 6. Memory UI

**Memory drawer** (from the top bar; also reachable via Account → Memory):
- Toggle: **"Use memory in new investigations"** (on/off), with the sentence: "When on, these notes are given to the assistant at the start of each investigation."
- Sections **"About you"** and **"About {Company}"**:
  - Each is a list of plain sentences with Edit (inline textarea) and Delete (inline confirm).
  - Provenance under each item: "Added by you · 3 Nov", or "From: *Should Hellberg sell…* · 5 Nov" as a link.
  - "+ Add a note" input at the bottom.
- A capacity meter ("6 of 30 notes"). When full: "Memory is full. Remove a note to add new ones." Never let a save fail silently.
- Empty state: *"Nothing remembered yet. Add facts that apply to every investigation, e.g. 'We only sell through distributors in the EU' or 'Test budgets rarely exceed €20k'."*

**Saving from chat** (ask first):
- When a follow-up reveals a durable fact, show an inline card: *"Remember this for future investigations? 'Our retail partners are Würth and Hoffmann.'"* with [Save to company] [Save to project] [No].
- After a save: *"✓ Saved to company memory · Undo · Manage"*.
- Show "Saved" only after the server confirms.

**Project page** (`/projects/:pid`):
- Header with the name and a Rename action.
- **"Project brief"**: a textarea, e.g. "Goal, constraints, markets in scope", used as the project's instructions.
- **"Project notes"**: the same list UI as memory.
- Toggle: **"Use company memory in this project"** (default on), with the line: "Turn off to keep this project self-contained."
- The project's investigations as cards (question, verdict chip, date).
- "+ New investigation in this project".
- Empty state: *"No investigations here yet. Start one, or move one in from its ⋯ menu."*

---

## 7. Mind map tab

**Layout:** horizontal left-to-right tidy tree.
- Root: Company → Projects (+ "Not in a project") → Investigations → (expanded) Explanations and Recommendation, then the top 2 quotes under the leading explanation.
- Default depth shows investigations; deeper levels stay collapsed.

**Rendering:**
- HTML nodes (200×56px, text clamped to 2 lines) absolutely positioned inside a `transform: translate() scale()` container.
- Connectors: one SVG layer of cubic Bézier paths.
- **Layout algorithm (hand-rolled, about 40 lines):**
  - x = depth × 248.
  - Visible leaves get y = rowIndex × 72.
  - Each parent's y = the mean of its first and last child.
  - Recompute on expand or collapse, and animate `transform` over 200ms (skip under `prefers-reduced-motion`).

**Node styles:**
- Company: filled accent.
- Project: folder icon, with a count.
- Investigation: status dot plus a verdict chip ("Go", "Test first", "Don't", "Stopped").
- Explanation: dot coloured by how likely it is, with a ★ on the leading one.
- Evidence: a quote snippet with a source-class chip.

**Interactions:**
- Click the ▸ to toggle children.
- Click a node to select it; the right drawer shows its summary with **"Open investigation"** or **"Ask about this"**, which opens the follow-up box pre-filled.
- **Focus**: double-click or the "Focus" button dims everything except the node's path and subtree.
- Search box highlights matches and expands their ancestors.
- Toolbar: + / − / Fit / Expand all / Collapse all.
- Drag to pan; Ctrl+wheel to zoom.
- **Accessibility:** `role="tree"`, `treeitem`, `aria-expanded`; arrow keys navigate, Enter opens. A "List view" toggle shows the same data as nested `<ul>`s.

**Empty state:** *"Your map grows as you investigate. Each investigation appears under its project."* with a [Start an investigation] button.

---

## 8. PDF report

**Method:** a "Download PDF" button opens `/report/:id` and calls `window.print()`, so no library is needed. Use `@page { size: A4; margin: 18mm 16mm }`, `break-inside: avoid` on cards, charts and table rows, `break-before: page` per section, and `print-color-adjust: exact` for charts ([print CSS guide](https://21pdf-marketing.pages.dev/blog/css-print-complete-guide)). Tip shown on the page: "Choose 'Save as PDF'".

**Page 1, executive summary** (must fit on one page):
- Title (the question), company, date, "Prepared with Aemon (prototype)".
- Recommendation box with the confidence category and its action.
- Next step and test cost.
- "What would change our mind".
- The 4 tiles.
- Chart A.

**Page 2:** explanations compared (charts A and B, with 1–2 quotes each), plus the source mix (chart C).

**Page 3:** the test plan (chart D, predictions table, decision rule).

**Appendix:**
- Numbered source list: title, class, date, URL, quoted excerpt.
- "How this was produced and its limits", in 5 plain lines.

**Typography and layout:**
- Body 10.5pt/1.45, H1 20pt, H2 13pt, captions 8.5pt.
- Single column at about 70 characters per line.
- Footer with the page number, via `@page` margin boxes in Chromium or a fixed footer as a fallback.

---

## 9. Glossary (UI words)

| Current | Show as |
|---|---|
| theory | **explanation** ("a possible reason customers would buy") |
| favoured theory | leading explanation |
| belief | how likely (the assistant's estimate) |
| assess_evidence / Weigh evidence | weighed a source: for / against / no bearing |
| evidence, dossier | sources, source library |
| verified_observation / company_claim / synthetic | Independent source / Company's own claim / Simulated (what-if) |
| stage | step |
| frame_problem | Defined the decision |
| challenge | Stress-tested the leading explanation |
| propose_test / decline_test | Designed a small market test / Decided a test isn't worth the cost |
| prediction_by_theory / decision_rule | "If this is right, we'd expect…" / How we'll decide |
| position | interim view |
| uncertainty / would_change_if | What we're unsure about / What would change our mind |
| harness / refused | checker / "Not accepted by the checker; it changed nothing" |
| turn limit / context limit / repeated errors | Ran out of time / Had too much to read / Got stuck, and so stopped early |
| shock / new evidence scenario | what-if |
| workspace | company |
| cached result | saved earlier result |
| adapter, base, llama.cpp, temperature | hidden (dev mode only) |

**7 step labels:**
1. Understand the question
2. Gather sources
3. List possible explanations
4. Weigh the evidence
5. Stress-test the favourite
6. Design a test
7. Recommend

---

## 10. Visual tokens

**Colour**

| Token | Light | Dark |
|---|---|---|
| --page | #F7F7F5 | #0F1115 |
| --surface | #FFFFFF | #171A21 |
| --sunken | #F0EFEC | #1F232B |
| --ink | #17181C | #ECEDEF |
| --ink-2 | #4A4D55 | #C2C5CC |
| --muted (≥4.7:1) | #6B6E76 | #9A9EA7 |
| --border | #E2E1DC | #2A2F38 |
| --accent | #2F5BD3 (white text 5.9:1) | #7C9BFF (text #0B1020) |
| --accent-ink | #1F45A8 | #A9BCFF |
| --accent-wash | #EAF0FD | #1C2645 |
| --support (for) | #0F7B6C | #3FBFA8 |
| --against | #C2410C | #F08A5D |
| --neutral | #8A8F98 | #8B919B |
| --independent | #334155 | #94A3B8 |
| --company-claim | #A16207 | #E0B252 |
| --good / --bad / --warn | #1F7A3A / #B3261E / #8A5A00 | #6CC77A / #F08B82 / #F0B545 |

Teal vs orange stays distinguishable for colour-blind readers (Okabe–Ito family). Always pair colour with a glyph or label.

**Type:**
- `system-ui` stack, or Inter from Google Fonts.
- Scale: 12 / 13 / 14 / 16 (body) / 20 / 24 / 32.
- Weights: 400 / 550 / 650.
- Line height 1.5 for body, 1.25 for headings.
- `tabular-nums` for numbers.

**Spacing, radii, elevation:**
- Spacing (4-point base): 4 / 8 / 12 / 16 / 24 / 32 / 48. Cards use 20–24px padding and 16px gaps.
- Radii: 6 (inputs, chips), 10 (cards), 14 (hero card, drawer), 999 (pills).
- Shadows:
  - `--sh-1: 0 1px 2px rgba(16,24,40,.06)`
  - `--sh-2: 0 4px 12px rgba(16,24,40,.08)`
  - `--sh-3: 0 12px 32px rgba(16,24,40,.14)` (drawer, toast)
  - Dark mode: borders plus `rgba(0,0,0,.45)`.

**Focus:** `outline: 2px solid var(--accent); outline-offset: 2px` on everything focusable. Add `scroll-margin-bottom` equal to the sticky composer's height so focus is never hidden (WCAG 2.4.11).

**Motion:** 150–200ms ease-out, with everything off under `prefers-reduced-motion`.

---

## 11. Onboarding and other empty states

**First-run card** (dismissible; dismissal remembered in `localStorage` inside try/catch):
> **Welcome to Aemon.** 1. Ask a decision question. 2. It gathers public sources and weighs the evidence for each possible explanation (2–3 min). 3. You get a recommendation, how sure it is, and a small test you could run.
> Buttons: [Try an example] [Tell it about your company] (opens Memory)

**Other empty states:**
- **Sidebar, no investigations:** "Your investigations will appear here."
- **No sources found:** "It found no sources on this. Try rephrasing, or turn on live web search."
- **Stopped early:** "It stopped before recommending, during *Weigh the evidence*. Here is its interim view." Then [Run again].
- **Model server down** (replaces the jargon): "The assistant isn't available right now. Ask your administrator to start it." Keep the technical detail in dev mode.

**Microcopy:**
- **Buttons:** "Start investigation", "Stop", "Download PDF", "Ask".
- **Toast:** "Investigation finished. Recommendation: test first."
- **Errors:** "Couldn't start the investigation. Check your connection and try again."

---

## 12. Implementation notes (current code)

**New files:**
- `pages/InvestigatePage.tsx` (replaces `TryPage`)
- `components/ResultView.tsx`
- `components/charts.tsx` (charts A–D)
- `components/FollowUp.tsx`
- `components/MemoryDrawer.tsx`
- `pages/ProjectPage.tsx`
- `pages/MindMap.tsx`
- `pages/ReportPage.tsx`

**Reuse:**
- `theoriesOf()` from `Trace.tsx`; export it and add first/last belief by scanning `state_position` and final.
- `JourneyMap` for the stepper.
- `WorkflowCanvas` and `StepDetail` stay unchanged inside "How we got here".

**Data available today:**
- Test fields: `propose_test` carries `cost_eur`, `weeks`, `prediction_by_theory` and `decision_rule`.
- The test budget is `test_budget_eur`, exposed in the brief.
- Source classes come from `Record.type`.
- Follow-ups, memory and suggestions need new endpoints.

**Labels:** rename the entries in `labels.ts` STAGES, SHORT and STOPS to the glossary above.

**Caveats:**
- The public sources disagree on some current ChatGPT/Claude memory and Projects details (project-only memory availability, the summary vs list UI). I cited what was verifiable.
- Confidence categories must stay derived from data the run actually produced. Don't add % beliefs, because the agent only produces verbal levels.
