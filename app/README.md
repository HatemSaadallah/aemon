# Strategy Lab

The local UI and backend for this project. It binds to `127.0.0.1` only.

```bash
./app/run_model.sh   # Tiny Aya on port 8091, with every trained adapter found in ~/.cache/lexsi/adapters
./app/run.sh         # the Strategy Lab on http://127.0.0.1:8000
```

## Frontend

React 18 with React Router and strict TypeScript, built by Vite, in `app/web`. FastAPI serves the build in
`app/web/dist` when it exists and the older plain pages in `app/static` otherwise; the API is the same either way.
`app/run.sh` builds it once if `dist` is missing and Node is installed (the user-space install in `~/.local/node`, or
any `npm` on `PATH`). By hand:

```bash
export PATH="$HOME/.local/node/bin:$PATH"
npm --prefix app/web ci          # node_modules is gitignored; package-lock.json pins every version
npm --prefix app/web run build   # tsc --noEmit, then vite build into app/web/dist (also gitignored)
npm --prefix app/web run dev     # live reload on :5173, proxying /api to the app on :8000
```

Model-written text is rendered as React text only, never as HTML. Restart the app after a build so it picks up `dist`.

## Sign in

Every page and API route needs a signed-in user. Companies, accounts, memberships, sessions, history and saved runs live in one SQLite file outside the repository, `~/.local/share/lexsi/strategy_lab.db` (or `LEXSI_DATA`), mode 600, holding salted scrypt hashes and never a plain password; on first start it imports an older `~/.config/lexsi/users.json` and `chats/` folder once and leaves them in place. There is no default account. An account is a member of one or more companies and works in one company's workspace at a time: the switcher in the header changes the whole app to that company, and an account never sees a company it is not a member of (the API answers 404). The companies table is filled from the dossier at start-up; an account in no company joins `LEXSI_DEMO_COMPANY` (default `hellberg`), so the demo shows one company.

```bash
.venv/bin/python app/users.py add NAME COMPANY    # asks for the password twice, at least 8 characters
.venv/bin/python app/users.py join NAME COMPANY   # another company's workspace for the same account
.venv/bin/python app/users.py leave NAME COMPANY
.venv/bin/python app/users.py list                # accounts and their companies
.venv/bin/python app/users.py companies
.venv/bin/python app/users.py remove NAME
```

Sessions last 12 hours in an HttpOnly, SameSite=Strict cookie and are stored as token hashes in the database, so a
restart keeps everyone signed in. Five failed sign-ins for one name within a minute block that name for a minute.

- **Try it:** a workflow studio inside the current company's workspace (the companies are `WORKSPACES` in `server.py`, none of which the current adapters trained on). The left sidebar holds the company, a new-investigation button and the account's history in this workspace. A new investigation starts from a typed question, the case's own question and two rephrasings, or a what-if with simulated new evidence; it runs only on that company's dossier, and the server refuses any other company's case. The middle is a dotted canvas drawing the investigation as a workflow: the question is the trigger card, each call a connected step card coloured by tool, stage names label the connectors, steps that weigh evidence on specific theories branch into one lane per theory, identical calls in a row are drawn once with a count, refused calls are dashed red, and the last card is the recommendation or where and why it stopped. A stage map above it shows progress. The right panel shows the selected step (what the model sent, the harness's verdict), the outcome and the theory board with the evidence weighed and the stated beliefs. Each run starts fresh. A finished run is saved under its case and evidence digest, model and prompt, the adapter contents and base model the server holds, the llama.cpp build and context, and the code; asking the same again shows it at once, labelled as a saved result with its date and configuration, with a button to run it again live. Failed or interrupted runs are never saved. The page runs one model, `LIVE_MODEL` in `server.py`.
- **How it works:** the stage controller as a diagram, drawn from `/api/workflow`: the stages in order, grouped, the tools each one opens, what moves the investigation on, the optional what-if branch, and the tools that stay open from the test onward. It is the same table a test checks against the controller, so it cannot drift from the code.
- **The math:** the model of Camuffo, Gambardella and Pignataro (2024), equations 1 to 7 with their Luxottica numbers, a calculator that illustrates the framework with standard Bayesian updating (the agent computes no probabilities), how each concept maps to a stage and tool, and how the agent is assessed: its own five-point beliefs before and after each simulated what-if, checked for direction by `/api/beliefs`.
- **Results:** the paired pilots. The same cases, controller, prompt and settings, and the only difference is the adapter. Each case shows how far each model got and why it stopped, and opens the full run as a tree (or as the step list). A pilot appears once both of its reports exist; add the next one to `PILOTS` in `server.py`. A run can be linked directly, such as `#/results/pilot2/trained/5` (old `#results/...` links still work).
- **Training:** the live loss chart from `scripts/training_feed.py`, with the best held-out checkpoint marked.

These are development pilots on two companies, not a final test. Checks are guards against mechanical mistakes, not measures of strategy quality.
