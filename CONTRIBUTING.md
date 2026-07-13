# Contributing questions

The practice bank lives in `seed_data_*.json` files and loads into `data/study.db`
via `seed.py`. This guide covers adding good questions in the project's format.

## Provenance rule (read first)

Every question must be **original** and grounded in **public** Anthropic documentation
(platform.claude.com docs, the public Claude Code docs, published blueprints). Do **not**
add questions recalled, transcribed, or screenshotted from a real proctored exam — that
is confidential Exam Content and may not be published or shared (see the
[README provenance section](README.md#provenance--compliance)). When in doubt, write a
fresh scenario that tests the same idea.

## Question shape

Each question is one JSON object in a `seed_data_*.json` array. Fields (see `db.py` for
the schema and `seed.py` for the loaded columns):

```json
{
  "domain": "agentic",
  "scenario": "multi_agent_research",
  "principle": "stop_reason_terminates_loop",
  "stem": "A long, realistic scenario (3–6 sentences)…",
  "choice_a": "…", "choice_b": "…", "choice_c": "…", "choice_d": "…",
  "correct": "C",
  "rationale_a": "Incorrect. …", "rationale_b": "Incorrect. …",
  "rationale_c": "Correct. …", "rationale_d": "Incorrect. …",
  "anti_pattern": "Short prose description of the trap the wrong choices embody.",
  "anti_pattern_slug": "loop-termination-nl",
  "source": "your-source-tag"
}
```

`domain`, `scenario`, and `correct` are `CHECK`-constrained — use only the allowed values
below. `principle`, `anti_pattern`, `anti_pattern_slug`, and `source` are optional
(nullable). Use `anti_pattern_slug: null` when none of the catalog slugs fit — don't
force-fit.

### Allowed `domain` values

`agentic`, `claude_code`, `prompt_eng`, `tool_mcp`, `context`, `off_blueprint`
(`off_blueprint` is a local-only study domain with zero exam weight for topics the
Exam Guide lists as out of scope.)

### Allowed `scenario` values

`customer_support`, `code_generation`, `multi_agent_research`, `dev_productivity`,
`cicd`, `data_extraction`, `cli_lookup`
(`cli_lookup` was retired in Exam Guide v0.2 and is kept only so legacy rows
validate — don't use it for new questions.)

## The "near-miss" format

Strong CCA-F questions have **four choices: one correct, one near-miss, two distractors**.

- **Correct** — fully defensible from public Anthropic guidance.
- **Near-miss** — almost right, but with ONE specific, **objective** flaw that makes it
  wrong: a wrong value, a wrong mechanism, or a missing required piece. The flaw must be
  checkable, not a matter of taste. This is what the real exam uses to separate
  candidates who understand the principle from those who pattern-match.
- **Two distractors** — plausible but clearly wrong.

Randomize which letter is correct. The generator script (`scripts/assemble_new_bank.py`)
balances this automatically for machine-generated questions; for hand-written ones, just
don't pile them all on B.

## Anti-pattern catalog

The near-miss flaw is usually one of these (slug → trap → correct move):

| slug | ✗ Trap | ✓ Correct |
|------|--------|-----------|
| `loop-termination-nl` | Parse natural language for loop termination | Inspect `stop_reason` (`tool_use` vs `end_turn`) |
| `iteration-cap` | Arbitrary iteration cap as the primary stop | Let the loop end naturally; cap is only a backstop |
| `prompt-vs-hook` | Prompt-based enforcement of a critical rule | Programmatic hook = deterministic |
| `confidence-escalation` | Self-reported confidence score for escalation | Structured criteria + programmatic checks |
| `sentiment-escalation` | Sentiment-based escalation | Escalate on task complexity / policy gap |
| `generic-error` | Generic `"Operation failed"` error | `isError`, `errorCategory`, `isRetryable`, context |
| `empty-as-success` | Empty results treated as success | Distinguish access-failure from genuinely-empty |
| `too-many-tools` | 18+ tools per agent | ~4–5 focused tools per agent |
| `same-session-review` | Same-session self-review | Separate session (no reasoning bias) |
| `aggregate-metrics` | Aggregate accuracy only | Per-doc-type accuracy (catches masked failures) |

## After editing a seed file

```bash
uv run python seed.py        # idempotent: skips questions whose stem already exists
uv run pytest -q             # selection helpers must stay green
uv run uvicorn app:app --port 8765   # smoke test: drill a question, check all 4 rationales render
```

## Regenerating the machine-built bank

`seed_data_v10_original_2026_06.json` was produced by a generate-then-adversarially-verify
pipeline and assembled by `scripts/assemble_new_bank.py`. To regenerate, re-run that
pipeline to repopulate the source directory, then `uv run python scripts/assemble_new_bank.py`.
