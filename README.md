# CCA-F Study App

A local, single-user app for drilling **scenario-based multiple-choice questions** for
the **Claude Certified Architect – Foundations (CCA-F)** exam, plus an interactive AI
tutor prompt. FastAPI + SQLite + HTMX. Runs entirely on localhost — no accounts, no
external services, nothing to deploy.

Two ways to study:

1. **The app** — a fixed, reviewed practice bank with resumable drilling, exam-blueprint
   domain weighting, and per-anti-pattern stats so you can see exactly where you're weak.
2. **The tutor prompt** ([`prompts/cca-f-tutor-prompt.md`](prompts/cca-f-tutor-prompt.md))
   — paste it into Claude for 60 fresh, adaptive questions with live coaching.

## Provenance & compliance

**This is a Blueprint-Aligned Practice Set, not an exam dump.** Every question is
**original**, written to match the *style and difficulty* of the CCA-F exam and grounded
in **public** Anthropic documentation and the published exam blueprint. Nothing here is
recalled, transcribed, or reproduced from a real proctored exam.

This is deliberate. The Anthropic Certification Exam Policy (§1 Confidentiality, §2
Misconduct) prohibits publishing or sharing real exam questions or answers — doing so can
get a certification revoked and the person permanently barred from the exam. So:

- ✅ Original scenarios that train the same architectural judgment — fine to share and publish.
- ❌ Real exam questions/answers — **never** add them, even privately. See
  [CONTRIBUTING.md](CONTRIBUTING.md#provenance-rule-read-first).

If you contribute questions, keep them original and public-docs-grounded.

## Quickstart

```bash
git clone https://github.com/putmanj00/cca-f-study.git
cd cca-f-study
uv sync                                   # or: pip install fastapi "uvicorn[standard]" jinja2 python-multipart
uv run python seed.py                     # loads the question bank into data/study.db (idempotent)
uv run uvicorn app:app --reload --port 8765
```

Open <http://localhost:8765>.

New teammate? The full walkthrough — pip-only path, phone access over Tailscale, and
troubleshooting — is in [docs/SETUP.md](docs/SETUP.md).

## The tutor prompt

For variety and exam-day prep, run the interactive tutor: copy the prompt from
[`prompts/cca-f-tutor-prompt.md`](prompts/cca-f-tutor-prompt.md) into a fresh Claude
conversation. It asks 60 original scenario questions one at a time, scores you, explains
every wrong choice, and flags the mistake patterns it notices. Details:
[`prompts/README.md`](prompts/README.md).

## How the bank is built

The current bank is original questions in the "near-miss" format: each has one correct
choice, one *almost*-correct choice with a single objective flaw (usually one of the
exam's [anti-patterns](CONTRIBUTING.md#anti-pattern-catalog)), and two distractors, with a
rationale for all four. Machine-generated questions are produced by a
generate-then-adversarially-verify pipeline and assembled (with balanced, randomized
correct-answer positions) by [`scripts/assemble_new_bank.py`](scripts/assemble_new_bank.py).
Add your own by hand following [CONTRIBUTING.md](CONTRIBUTING.md).

## Exam blueprint (public)

Scenario-based MCQ, 60 questions / 120 minutes, pass **720 / 1000**. Weights from
Exam Guide v0.2 (2026-06-30; see
[docs/exam-guide-v0.2-alignment.md](docs/exam-guide-v0.2-alignment.md)), used by the
weighted-drill mode and the stats page:

| ID | Domain | Weight |
|----|--------|-------:|
| D1 | Agentic Architecture & Orchestration | 27% |
| D2 | Tool Design & MCP Integration | 18% |
| D3 | Claude Code Configuration & Workflows | 20% |
| D4 | Prompt Engineering & Structured Output | 20% |
| D5 | Context Management & Reliability | 15% |

Questions on topics the guide lists as out of scope live in the zero-weight
`off_blueprint` domain — drillable via the domain filter, never weighted-sampled.

## Routes

| Method | Path        | Purpose                                                          |
|--------|-------------|------------------------------------------------------------------|
| GET    | `/`         | Home: pick mode (drill / review-wrong / add) and domain filter   |
| GET    | `/drill`    | Serve one question. `?domain=` filters; `?only=unanswered` serves the next never-answered question in fixed order with an "N remaining" counter (resumable across restarts); `?weighted=1` samples a domain by exam blueprint weight, then a random question in it |
| POST   | `/answer`   | Submit `question_id` + `selected`, record the attempt, return the result. Carries `only`/`weighted` so the result's Next link stays in the same mode |
| GET    | `/review`   | Serve a random question from those last answered incorrectly     |
| GET    | `/questions`| List questions with answered / unanswered / last-wrong status    |
| GET    | `/question/{id}` | Serve a specific question from the list                     |
| GET    | `/add`      | Form to add a question                                           |
| POST   | `/add`      | Insert a question, redirect to `/add?added=1`                    |
| GET    | `/stats`    | Accuracy summary: per-domain (with exam target weight), weakest principles, and most-missed anti-patterns |
| GET    | `/healthz`  | `{"ok": true}` sanity check                                      |

## Tests

```bash
uv run pytest -q
```

Pure selection helpers (`selection.py`) are unit-tested against a throwaway SQLite DB:
unanswered-set computation, resume cursor across a simulated process restart,
weighted-sampler distribution, and per-anti-pattern stats.

## Project layout

| Path | What |
|------|------|
| `app.py` | FastAPI routes |
| `db.py` | SQLite connection + schema |
| `selection.py` | Unanswered/resume/weighted selection + anti-pattern stats (unit-tested) |
| `seed.py` | Idempotent loader for `seed_data_*.json` → `data/study.db` |
| `seed_data_*.json` | The question bank |
| `scripts/` | `assemble_new_bank.py` — builds the question bank from verified question JSON |
| `prompts/` | The AI tutor prompt |
| `docs/SETUP.md` | Team setup walkthrough |
| `CONTRIBUTING.md` | Question format + provenance rules |
| `templates/`, `static/` | Jinja templates and assets |
| `tests/` | Pytest suite |

## Conventions

Python 3.11+, type hints on all signatures, stdlib `sqlite3` (no ORM), parameterized SQL,
Jinja templates (JSON only for `/healthz` and `/answer`). See `CLAUDE.md`.
