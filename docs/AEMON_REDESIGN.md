# Aemon redesign (2026-11-11)

The interface was rebuilt as one workspace on branch `claude/strategy-lab-ui`. The frozen V1 model, adapter, inference settings, tool schemas, guards, test cases and metrics are untouched. Only `app/web` changed, apart from the cache header noted below. Before and after screenshots, dark theme at 1440 px: `docs/figures/ui/redesign/{before,after}/`.

## Foundation
- **Design system.**
  - One token set with two themes: dark (the default, a layered charcoal-navy) and light. Tokens are at the top of `app/web/src/style.css`.
  - One type scale: Source Serif 4 for titles, company names and questions; Inter for the interface.
  - `app/web/src/ui.css` is loaded last and holds the shell, containers and shared components: buttons, fields, segmented controls, chips, panels, stats, empty states, skeletons and page headers.
  - The page-specific blocks follow in the same file.
- **Workspace sidebar** (it replaces the top bar):
  - the brand and company switcher;
  - New investigation;
  - Home, Investigations and Companies;
  - the six most recent investigations, each with its status;
  - Methodology and About;
  - Memory, Review, Sign out and the theme switch at the foot.
  - On phones it becomes a drawer behind a compact top bar.
- **The reasoning map belongs to one investigation.** It is no longer a global section. Each investigation has three views behind one header: Report, Reasoning map and Sources (`components/InvTabs.tsx`). The map's address is `/map/<id>`, and `/map` alone opens the newest investigation.

## Screens
- **Home.**
  - A two-column company hero: identity and the main action on one side, and the company's image on the other. An illustration is tagged "Illustration · not a company image".
  - Verified counts: investigations, finished, stopped early or interrupted, source records, and the last investigation.
  - Scannable investigation rows with Report and Map links. A finished run is labelled "Finished", not "Recommendation".
  - Suggested questions, labelled as starting points rather than findings, and a "How to read results" panel.
- **Investigate.**
  - The question is the centre of the page.
  - Depth, sources, the finish-on-time guard, and memory and project sit behind Options. Live web search and the guard are labelled experimental and outside the frozen evaluation.
  - A settings line shows what will run. Defaults are unchanged.
  - Example questions fill in the question box instead of starting a run.
  - Simulated scenarios sit in their own collapsed section. A chosen one replaces the question box with a clearly labelled scenario card.
- **Investigations library** (it replaces History):
  - collections for all, pinned and each project, with creating, renaming and deleting projects (moved here from the old investigate sidebar);
  - search, outcome filters, sorting, and a list or card view;
  - per-run actions: pin, move or delete, with confirmation;
  - repeated runs of a question are numbered ("Run 1 of 2") and never merged;
  - pick two runs to compare them side by side (`/compare/<a>/<b>`), field by field, from the recorded data. A field a run did not record is shown as "Not recorded".
- **Reasoning map.**
  - Full workspace height below the investigation header.
  - The toolbar is grouped: views, search, a Filters popover, the level indicator, the zoom group (− Fit +), a minimap toggle, and "Go to recommendation".
  - Overview cards are narrower and taller with larger type, so the fitted map reads without zooming: the fit zoom is 0.81, against about 0.68 before.
  - The minimap appears only when the map is larger than the screen.
  - The question and recommendation cards have their own dark-theme style.
  - On phones the map opens on its text Outline view.
  - Semantic zoom, the detail panel and focus dimming are kept from the previous version.
- **Report.**
  - The same header and tabs as the map.
  - Why, What is uncertain and Next step are stacked rows with the label beside each one. They are no longer three narrow columns.
  - The conclusion is set smaller.
  - The report's Reasoning map tab opens `/map/<id>`. The map's "Open in the report" opens the report at that section.
- **Methodology.**
  - An interactive seven-stage process. Each stage gives what the agent does, why it matters, the tools it calls, and an example taken from the latest finished investigation of the current company.
  - The technology explained in plain words.
  - Measured results, with the reliability audit beside them.
  - Only published resources are linked. The paper is marked as not yet published.
- **About.** Four sections:
  - a mission hero with an illustrative SVG investigation diagram;
  - How Aemon thinks;
  - what makes it different;
  - a closing statement linking to Methodology.

  It contains no metrics.
- **Who we are** (`/team`, under Research in the sidebar). Only the two researchers' profiles, with no invented biographies or made-up photographs. Both portraits are their own photos, cut out on the Mac (Apple Vision) and set on one shared backdrop with the same framing and grade; the only link is Hatem's GitHub.

## Backend
The main page is now sent with `Cache-Control: no-cache` (`app/server.py`), so a refresh always loads the newest build. There are no other backend changes.

## Measurements
All runs used headless Chrome at 1440×900 with 4× CPU throttling, on the largest Hellberg investigation (`a30d166b`).

| | Cards | Layouts during zoom | Script | Layout | Style | Frames > 50 ms | p95 frame |
|---|---|---|---|---|---|---|---|
| Zoom, Overview (106 wheel steps through all levels) | 8 | 3 | 25.1 ms | 17.4 ms | 5.8 ms | 0 | 16.7 ms |
| Zoom, Evidence | 12 | 3 | 26.2 ms | 25.5 ms | 13.3 ms | 0 | 16.7 ms |
| Pan (120-step drag) | 8 | n/a | 28.7 ms | 0 ms | 12.8 ms | 0 | 16.8 ms |

Readability check across every saved investigation, in Overview and Evidence at all three zoom levels: 22 map views, 0 overlapping card pairs, 0 cards with cut text.

## Tests run
- TypeScript check and production build: pass.
- `app/test_api.py` and `app/test_companies.py`: 10 passed.
- A console sweep over all 12 routes found 0 errors and no horizontal overflow at 1440 px.
- A click-through of the journey passed every step:
  - a Home example fills the question and starts nothing;
  - Options opens;
  - library selection leads to the comparison;
  - the card view works;
  - report → map → sources tabs;
  - a node click opens its panel and dims unrelated cards;
  - the filters popover opens;
  - a company switch from the sidebar updates Home.
- Screenshots: 1440, 1024, 768 and 390 px for About; 1440 and 390 px for the other screens; the light theme for Home and the map.

## Limits
- **Timeline playback** is not implemented. The Timeline view lists the recorded actions in order, but does not replay the map step by step.
- **Live progress** was not exercised in this pass; starting a run would add to the history. It uses the same components and its Full page map.
- **The PDF export** keeps its earlier layout.
- **The Review page** and the company directory use the new tokens and shell but were not redesigned.
- **Command or search palette:** not added. The sidebar and the library search cover finding investigations; there is no cross-company evidence search.
- **The map's layout** is still a left-to-right layered layout with simple curves. There is no crossing minimisation beyond banding.
