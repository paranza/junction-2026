# MUSTA HELMI

Four-person team at **Junction 2026: European Tech Renaissance**, 13-15 November 2026, Espoo, Finland.

The team selected Stoa's Make Blueprints Talk challenge. The working **Trace** application is isolated in [`stoa-trace/`](stoa-trace/): construction drawing and BIM questions with source evidence, explicit highlighting, reproducible quantities and human review.

Read the [application setup](stoa-trace/README.md), [engineering handoff](stoa-trace/HANDOFF.md) and [prompt for a teammate's Codex session](stoa-trace/FRIEND_PROMPT.md). The source dataset, generated runtime and credentials are separate from Git. [Dataset inventory and limits](stoa-trace/DATA_INVENTORY.md) explains what is loaded.

## Run Trace

Use Python 3.11 and Node 22.14.0 with npm 10.9.2. From the repository root on macOS or Linux:

```sh
cd stoa-trace
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
cp .env.example .env
# Configure STOA_DATA_ROOT and a fresh STOA_RUNTIME_DIR in .env.
.venv/bin/python ops/start_local.py
```

Open <http://127.0.0.1:8787>. Native analysis needs no API key. Visual analysis needs a privately configured OpenAI key. Windows setup and dependency refresh instructions are in the application handoff.

Verify from `stoa-trace/`:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python ops/benchmark.py --dry-run
```

The unit suite uses fixtures and no model calls. Source-backed benchmark execution additionally needs the separately downloaded preview dataset and a running backend. The [GitHub Actions template](stoa-trace/ops/ci/github-actions.yml.example) checks the unit suite, frozen-manifest validation and frontend build. It is not active: the credential used for this handoff can push code but lacks GitHub's `workflow` scope. A maintainer with suitable permissions can copy it to `.github/workflows/stoa-trace.yml`.

## Start here

1. Read the [challenge research](docs/challenges.md). It covers all 19 titles from the dashboard screenshot and separates evidence from guesses.
2. Check the [event rules and deadlines](docs/event.md) and [submission checklist](docs/submission.md).
3. Follow the [tool and agent setup](docs/setup.md) and [contribution guide](CONTRIBUTING.md).
4. Check the current [decisions](docs/decisions.md) and the Trace handoff before implementing another pipeline or provisioning infrastructure.

## Team

Assign the four owners together. These are suggested responsibilities, not fixed job titles.

| Responsibility | Owner |
| --- | --- |
| Product, integration and submission | Unassigned |
| Frontend and user experience | Unassigned |
| Backend, AI and partner APIs | Unassigned |
| Data, verification and demo | Unassigned |

## Event essentials

All event times use **Europe/Helsinki (UTC+02:00 on these dates)**.

- Hacking starts: Friday 13 November, 19:30. The guide prohibits advance project code.
- Preliminary submission: Friday 13 November, 23:59.
- Final deadline: Sunday 15 November, 10:00. Set the project to **FINAL**, not DRAFT.
- Peer review: Sunday from 10:30. All teammates must participate for main-prize eligibility.
- Submission video: at most two minutes. Stage pitch: three minutes plus three minutes for questions.

The [event notes](docs/event.md) flag conflicting guide details rather than silently choosing one.

## Repository map

- [Trace application](stoa-trace/): code, tests, setup, measured results and teammate handoff.
- [Public Stoa project research](docs/research/): competitor approaches, dated updates, source links and monitoring instructions.
- [AGENTS.md](AGENTS.md): shared guidance for coding assistants.
- [CLAUDE.md](CLAUDE.md): imports the shared guidance for Claude Code.
- [Setup](docs/setup.md): tools, team skills and agent workflow.
- [Partners](docs/partners.md): evidence, credit status and integration questions.
- [Demo](docs/demo.md): recording, live demo and fallback plan.
- [Submission](docs/submission.md): required fields and final checks.

## Sources and status

Initialized on 13 November 2026 from the participant guide pasted by a teammate, their dashboard screenshot, and linked public sources. The screenshot confirms titles only. Public announcements are clues, not complete challenge briefs. Follow later organizer announcements when they update these notes.

[Event website](https://2026.hackjunction.com/) | [Junction Platform](https://hackjunction.app/)

Team-authored repository content is covered by the [MIT license](LICENSE). Partner data, source-derived examples, third-party dependencies and the organizer screenshot retain their own terms. See [Trace third-party notices](stoa-trace/THIRD_PARTY_NOTICES.md).
