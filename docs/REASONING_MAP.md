# Strategy Reasoning Map (2026-11-10)

`app/web/src/components/reasoning/`. The graph is built in `graph.ts`; the interface is in `ReasoningMap.tsx`. It is a
frontend view of the recorded investigation. The model, prompts, tools, guards, inference settings and evaluations are
unchanged, and no backend change was needed: the run record already holds every field used.

## What caused the lag (measured before changing anything)
Benchmark (`scratchpad/bench.py`): a 120-step drag in headless Chrome with 4× CPU throttling, reading Chrome's counters
and frame times, on the company mind map with every branch expanded (32 cards, the largest map in the app).

| | script | style | frames > 50 ms | keeps moving after the pointer stops |
|---|---|---|---|---|
| Company mind map, before | 97 ms | 15.5 ms | 0 | **199 ms** |
| Company mind map, after (no transition) | 85 ms | 8.4 ms | 0 | **0 ms** |
| Reasoning map, overview (8 cards) | 29 ms | 17 ms | 0 | 0 ms |
| Reasoning map, evidence mode (12 cards) | 57 ms | 33 ms | 0 | 0 ms |

- **The main thread was not the bottleneck.** No frame was long, even with every branch open.
- **The lag was a CSS transition.** `transition: transform .2s` on the map's layer restarted on every pan step, so the
  map trailed the pointer by about 200 ms. It is removed.
- **A second, smaller cost:** every pan step set React state and re-rendered every card and edge. It is cheap at 32
  cards and grows with the graph. The new map never re-renders while panning or zooming: the transform is written to
  the DOM once per animation frame.

## How the graph is built (only from the record)
| Node | From | Edges |
|---|---|---|
| Strategic question | `question`, `frame` | considers → each hypothesis |
| Hypothesis | `theories` (★ the favoured one: `final.favoured_theory` or `position`) | |
| Evidence group, or source | `assessments` grouped by hypothesis and direction; expanded into one node per source, shared when a source was weighed for several hypotheses | supports, contradicts, no bearing |
| Challenge | `challenge_searches` (query, sources found) | challenges → its hypothesis |
| Experiment | `tests` (method, predictions per hypothesis, decision rule); or `test_declined` | tested by ← each hypothesis it tests |
| Simulated result | sources of class `synthetic` that were read, tagged "Not evidence" | observed → a revision that cites it |
| Revision | `revisions` (kept or revised, reason, evidence) | revises → its hypothesis |
| Recommendation | `final`, or `position` (interim), or "no recommendation" with its status, plus answer flags | favoured in ← hypothesis; cited by ← cited sources |

No edge is inferred. A revision connects to a simulated result only if it cites that result's id. The recommendation
connects only to the hypothesis it favours and the sources it cites.

**Layout:**
- columns by stage;
- rows banded by hypothesis, so a hypothesis's evidence and challenges sit beside it;
- a node linked to several hypotheses sits at the mean of their rows;
- each column is then pushed apart so nothing overlaps.

The layout is deterministic and recomputed only when the structure or the expanded set changes, which costs well under
1 ms here. A live run's map keeps the user's pan and zoom as new steps arrive.

## Interactions
- **Views:**
  - **Overview:** question, hypotheses, evidence as "N supporting / opposing" groups, challenges, experiments,
    revisions, recommendation;
  - **Evidence:** every source, shared across hypotheses;
  - **Timeline:** every recorded action, refused ones included;
  - **Outline:** the same content as text, for keyboard, screen-reader and print use.
- **Navigation:** drag to pan; scroll to zoom around the pointer; zoom buttons; `+`, `−` and `0` keys; Fit. A
  collapsible overview minimap; click it to move there.
- **Selection:** click any card for its details panel. Selecting a hypothesis highlights its path and dims the rest.
  Groups and hypotheses expand in place.
- **Finding:** search highlights matches, and Enter jumps to the first. Filters for supporting, opposing, no bearing,
  challenges and experiments. A Recommendation button jumps there.
- **Legend.**
- **Details panel:**
  - hypotheses: the claim, mechanism, supporting and opposing quotes, challenges and revisions;
  - sources: title, link, date, origin, excerpt, how the agent used each quote, the company-claim warning, the evidence
    kind's reliability;
  - experiments: design, predictions per hypothesis, decision rule, labelled as proposed and not run, and the
    check's leniency;
  - simulated results: never evidence;
  - recommendation: status (final, draft, interim, none), answer flags, next step, uncertainty, what would change it,
    and Open in the report.

**Where it appears:**
- the report has three views: **Executive report · Reasoning map · Sources**;
- the live progress page shows the map as its first view, labelled Live;
- company profiles link to their investigations' reports.

**Provenance labels:** quotes are "Quoted", the agent's statements are "Agent's hypothesis", "Agent's reading" or
"Agent's conclusion", and simulated results are "Simulated". The map says it shows the recorded reasoning, not that the
reasoning is right.

## Tested
In headless Chrome at 1440×900, on real saved investigations:
- **Largest:** Hellberg a30d166b, 2 hypotheses and 10 weighed quotes.
- **Simulated result and revision:** Hellberg ab30ffb2.
- **Draft answer:** Jotun.
- **Stopped with no recommendation:** Neumann.

Checks:
- selecting a hypothesis opens its panel and dims the unrelated branch (2 of 8 cards);
- Evidence mode shows 6 shared sources;
- the source panel shows the verified quote;
- Outline has 5 sections;
- drag, zoom and Fit work;
- the TypeScript build passes.

Screenshots: `docs/figures/ui/map/`.

## Semantic zoom (2026-11-10)
Three detail levels, chosen from the zoom factor k, so zooming changes what a card says and not only its size:

| Level | Card width | Shows |
|---|---|---|
| Structure (bird's-eye) | 196 px | type and a short title only; the shape of the argument |
| Overview (default) | 248 px | type, title, one recorded line (the hypothesis claim, the quote, the test), and the for / against / no bearing tally |
| Detail | 352 px | the full title and every recorded field: quote, the agent's reading with its direction, who it is for, how the company earns, reliability notes |

Every word on every level comes from the run record. Nothing is summarised or generated for the map.

- **Hysteresis.** The map goes up from Structure at k ≥ 0.64 and from Overview at k ≥ 1.3. It goes down from Detail
  below k 1.18 and from Overview below k 0.56. Hovering around a threshold does not flicker.
- **No re-layout while zooming.** Pan and zoom only change one CSS transform. The layout is recomputed once, when the
  level changes. Cards at a level have heights estimated from their text, erring tall, so they never overlap or cut
  a line.
- **Focal point.** The card nearest the pointer (or the screen centre for +/− and keys) keeps its place under the
  pointer across the change of level.
- **Opening view.** The map opens at Overview. It shows the whole map when that fits at k ≥ 0.62, otherwise the middle
  of the map at that scale. **Fit** (or the 0 key) shows everything, dropping to Structure when needed.

**Measured** with headless Chrome at 1440×900, 4× CPU throttling, on the largest Hellberg investigation
(`a30d166b`). The test was 106 wheel steps: zoom in to Detail, then out to Structure.

| View | Cards | Levels passed | Layouts during zoom | Script | Layout | Style | Frames > 50 ms | p95 frame |
|---|---|---|---|---|---|---|---|---|
| Overview | 8 | Overview → Detail → Overview → Structure | 3 | 34.6 ms | 25.0 ms | 18.8 ms | 1 | 16.8 ms |
| Evidence | 12 | the same | 3 | 21.0 ms | 22.9 ms | 9.7 ms | 0 | 16.8 ms |

The layout count is one per change of level and none in between. The hypothesis under the pointer stayed under it
after zooming in.

**Readability check, all 12 saved investigations.** The investigations span Hellberg, Neumann and Jotun, with 2 to 13
cards each. Each was checked in Overview and Evidence at all three levels:

- overlapping card pairs: 0;
- cards whose text is cut: 0.

An earlier run found 1 to 6 cut cards per map at Detail, so the height estimate was made more generous. At Overview,
text is clamped to whole lines. Screenshots: `docs/figures/ui/map/zoom_overview_default.png`, `zoom_detail.png`, `zoom_structure.png`.

## Limitations
- The saved investigations are small: at most 13 cards in Evidence mode. Larger graphs are untested on real data. The
  render cost does not grow with panning; it grows only on expanding or selecting.
- Edge routing is simple curves. With many cross-links some may cross; no crossing minimisation beyond row banding.
- The live view re-lays out when the structure changes, so a card can shift as new hypotheses arrive. The viewport
  itself is kept.
