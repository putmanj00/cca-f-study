# CCA-F Study App

Local study app for the Claude Certified Architect – Foundations exam.
FastAPI + SQLite + HTMX. Single-user, runs on localhost only.

## Conventions

- Python 3.11+, type hints required on all function signatures
- Use stdlib `sqlite3`, not an ORM
- Routes return Jinja templates, not JSON, except `/healthz` and `/answer`
- HTMX swaps target `#main` for partial updates
- No external auth, no rate limiting, no CORS — this is local-only
- Run with: `uvicorn app:app --reload --port 8765`

## Testing

- Manual smoke test after changes: load `/`, drill a question, submit an
  answer, verify result page shows rationales for all 4 choices
- If adding routes, update the route table in README.md
