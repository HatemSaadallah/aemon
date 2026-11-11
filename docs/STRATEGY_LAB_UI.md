# Strategy Lab: the redesigned interface (branch `claude/strategy-lab-ui`, 2026-11-10)

The agent is V1 as frozen (`docs/V1_FREEZE.md`). The redesign changes only the interface: no agent, prompt, tool,
setting or evaluation code was touched.

## Launch
```bash
./app/run_model.sh        # the local model server (llama-server on port 8091, Tiny Aya + the V1 adapter)
./app/run.sh              # the Strategy Lab on http://127.0.0.1:8000 (builds app/web once if dist/ is missing)
npm --prefix app/web run build   # after changing the frontend
```
Sign in with an account from `python app/users.py`. The theme is light by default; the moon icon in the header switches
to dark for this browser only.

## Screens
| Screen | Route | What it shows (all from the server's real records) |
|---|---|---|
| Home | `#/home` | New investigation, the model's state, running investigations, counts by outcome, recent investigations with their recommendation, example questions, how to read results (V1's limits and this installation's runtime) |
| Investigate | `#/investigate` | The setup form (question, depth, memory, web search, attachments, the opt-in guard), examples and what-if scenarios; the live progress (seven milestones, current action, counts against the budget, hypotheses as they form, the live flow) |
| Report | `#/investigate/<id>` | Executive summary (recommendation, confidence, who it is for, value proposition, next step); Reliability (answer flags, how the confidence score was set, what the evidence rests on, a legend); Hypotheses; Evidence for and against, filterable by hypothesis; Experiment; Risks and open questions; Sources; Method (every step); Follow-up questions. PDF export, run again, continue, pin, project, delete. |
| History | `#/history` | Every investigation, searchable, filtered by outcome or project |
| Mind map, Methodology, About, Review | unchanged in function, restyled | |

Each statement in a report carries its provenance:
- **Quoted from the source**: checked word for word.
- **Agent's reading**: the agent's interpretation, not checked.
- **Agent's conclusion**: the recommendation.
- **Simulated**: a what-if result, never evidence.

A report that stopped early or ended in a draft says so first, with Continue and Run again.

## Tested
In headless Chrome at 1440×900 and 390×844, against the saved investigations of the Hellberg, Neumann and Jotun
workspaces:
- **Journey:** Home → New investigation → question → Quick → Start → live progress → finished report, with a real local
  run of 200 s.
- **Report types:** a finished report, a stopped run with no recommendation, a draft answer, PDF export (HTTP 200,
  valid PDF), History search, the mind map and the methodology page.
- **Backend:** app tests pass (26).

Screenshots are in `docs/figures/ui/`.

## Still to do
- The PDF report (`app/report.py`) keeps its earlier layout.
- Dark mode was restyled through tokens but not reviewed screen by screen.
- Sharing is by PDF only. The app has no share links or multi-user workspaces beyond company membership.
- No automated accessibility audit was run. Focus styles, labels and ARIA roles follow the existing components.
