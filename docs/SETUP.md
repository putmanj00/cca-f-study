# Team setup guide

Step-by-step setup for running the CCA-F study app locally. The app is a single-user,
**localhost-only** FastAPI + SQLite + HTMX app — no auth, no external services, nothing
to deploy. Each teammate runs their own copy and keeps their own attempt history.

## 1. Prerequisites

- **Python 3.11+** (`python3 --version`)
- **git**
- Optional but recommended: [`uv`](https://github.com/astral-sh/uv) for fast, reproducible
  installs (the repo ships a `uv.lock`).

## 2. Clone

```bash
git clone https://github.com/putmanj00/cca-f-study.git
cd cca-f-study
```

## 3. Install dependencies

**With `uv` (recommended — uses the locked versions):**

```bash
uv sync
```

**With pip + a virtualenv (no `uv`):**

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install fastapi "uvicorn[standard]" jinja2 python-multipart
```

> The dependency set is small (FastAPI, Uvicorn, Jinja2, python-multipart). If `uv sync`
> isn't available, the pip line above is sufficient to run the app and tests.

## 4. Seed the question bank

```bash
uv run python seed.py        # or: python seed.py  (inside your venv)
```

This creates `data/study.db` and loads every `seed_data_*.json` file. It is **idempotent**
— running it again skips any question whose `stem` is already present, so it's safe to
re-run after pulling new questions.

## 5. Run

```bash
uv run uvicorn app:app --reload --port 8765
```

Open <http://localhost:8765>.

> The `data/` directory (your SQLite DB and its backups) is git-ignored, so your attempt
> history is yours alone and never gets committed or pushed.

## 6. (Optional) Study on your phone

The app binds to localhost. To reach it from your phone on the same
[Tailscale](https://tailscale.com) tailnet without exposing it to the internet:

```bash
# with the app running on :8765
tailscale serve --bg 8765
tailscale serve status        # prints the https URL to open on your phone
```

`tailscale serve` keeps it inside your tailnet (HTTPS, no public exposure). Stop sharing
with `tailscale serve --https=443 off` (or `tailscale serve reset`).

## 7. Verify it works

```bash
uv run pytest -q                      # selection/stats helpers
curl -s localhost:8765/healthz        # -> {"ok": true}
```

Then in the browser: pick a domain, drill a question, submit an answer, and confirm the
result page shows a rationale for **all four** choices.

## Study modes

| Where | URL | What it gives you |
|-------|-----|-------------------|
| Home | `/` | Pick a mode and a domain filter |
| Drill | `/drill` | One question at a time. `?only=unanswered` walks every never-answered question in order and **resumes** where you left off after a restart. `?weighted=1` samples by exam blueprint weight. |
| Review | `/review` | Re-serve questions you last answered wrong |
| Questions | `/questions` | Browse the bank with answered / unanswered / last-wrong status |
| Stats | `/stats` | Per-domain accuracy (with exam target weights) and your most-missed anti-patterns |

The route table is also in the main [README](../README.md#routes).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `python: command not found` | Use `python3`, or run everything through `uv run …`. |
| `no such table: question` | You skipped step 4 — run `python seed.py`. |
| Port 8765 already in use | Pick another: `uvicorn app:app --port 8780`. |
| Empty `/drill` | The DB has no questions — re-run `python seed.py` and check it printed `Inserted: N`. |
| Want a clean slate | Delete `data/study.db` and re-run `python seed.py` (wipes your attempt history too). |

## Want to add or improve questions?

See [CONTRIBUTING.md](../CONTRIBUTING.md) — it covers the question format, the allowed
domain/scenario values, the "near-miss" structure, and the provenance rule (original,
public-docs-grounded questions only).
