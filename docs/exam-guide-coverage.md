# Exam Guide v0.2 coverage map (2026-07-13)

Every question now carries a `guide_section` field naming the Exam Guide
v0.2 task statement it covers (shown as a green tag in the app, exported by
`generate_markdown.py`, filterable in SQL). Mapping lives in
`scripts/add_guide_sections.py` (principle → task statement); re-run that
script after retagging principles.

Guide source: `SecondBrain/instructor_*_Claude+Certified+Architect+-+Foundations+-+Exam+Guide.pdf`
(v0.2, 2026-06-30). 5 domains, 30 task statements (D1 §1.1–1.7, D2 §2.1–2.5,
D3 §3.1–3.6, D4 §4.1–4.6, D5 §5.1–5.6) + Appendix out-of-scope list.

## Coverage after v12 gap fill (150 questions: 118 in-scope + 32 appendix)

| Section | Task statement | Qs |
|---|---|---|
| D1 §1.1 | Agentic loops (stop_reason, tool results, loop control) | 6 |
| D1 §1.2 | Coordinator–subagent orchestration | 4 |
| D1 §1.3 | Subagent invocation, context passing, spawning | 5 |
| D1 §1.4 | Multi-step workflows: enforcement + handoff | 2 |
| D1 §1.5 | Hooks: interception + normalization | 11 |
| D1 §1.6 | Task decomposition strategies | 2 |
| D1 §1.7 | Session state, resumption, forking | 3 |
| D2 §2.1 | Tool interface design | 5 |
| D2 §2.2 | Structured MCP error responses | 4 |
| D2 §2.3 | Tool distribution + tool_choice | 3 |
| D2 §2.4 | MCP server integration (.mcp.json, resources) | 3 |
| D2 §2.5 | Built-in tools (Read/Write/Edit/Bash/Grep/Glob) | 3 |
| D3 §3.1 | CLAUDE.md hierarchy, @import, /memory | 4 |
| D3 §3.2 | Slash commands + skills | 3 |
| D3 §3.3 | Path-specific rules | 1 |
| D3 §3.4 | Plan mode vs direct execution (+ Explore subagent) | 5 |
| D3 §3.5 | Iterative refinement (tests-first, interview pattern) | 3 |
| D3 §3.6 | CI/CD integration (-p, --json-schema) | 3 |
| D4 §4.1 | Explicit criteria / false-positive control | 2 |
| D4 §4.2 | Few-shot prompting | 2 |
| D4 §4.3 | Structured output via tool use + JSON schemas | 11 |
| D4 §4.4 | Validation, retry, feedback loops | 2 |
| D4 §4.5 | Batch processing | 3 |
| D4 §4.6 | Multi-instance / multi-pass review | 2 |
| D5 §5.1 | Long-interaction context management | 6 |
| D5 §5.2 | Escalation + ambiguity resolution | 4 |
| D5 §5.3 | Error propagation across multi-agent systems | 3 |
| D5 §5.4 | Context in large codebase exploration | 8 |
| D5 §5.5 | Human review + confidence calibration | 3 |
| D5 §5.6 | Provenance + multi-source uncertainty | 2 |

All 30 task statements have ≥1 question. Bank counts intentionally do NOT
mirror exam weightings — `pick_weighted_domain` handles exam-like sampling;
the bank targets task-statement coverage.

## v12 gap fill (seed_data_v12_guide_gap_fill.json, 8 questions)

Pre-v12 audit found one hole and three thin spots:

- **D5 §5.3 had ZERO questions** → added 3: structured error context for
  coordinator recovery; subagent local recovery + partial-result
  propagation; coverage annotations vs silent-gap/full-abort.
- **D1 §1.7 had 1** (fresh-session-with-summary only) → added 2:
  fork_session parallel exploration; informing resumed sessions of file
  changes.
- **D3 §3.5 had 1** (concrete I/O examples only) → added 2: test-driven
  iteration with shared failures; interview pattern.
- **D1 §1.4 had 1** (handoff only) → added 1: programmatic prerequisite
  gate (mirrors the guide's own sample Q1).

## Remaining thin spots (1–2 questions, acceptable but drillable)

- **D3 §3.3 (1)** — path-scoped rules is a narrow task; single question
  covers its core skill.
- **D1 §1.6 (2)** — prompt chaining vs adaptive decomposition both covered.
- **D4 §4.1/4.2/4.4/4.6, D5 §5.6 (2 each)** — each question pair covers the
  task's two main knowledge bullets.

Sub-topics in the guide with no dedicated question (folded into neighbors):
§1.2 iterative-refinement re-delegation loop; §3.5 single-message
(interacting) vs sequential (independent) fixes; §4.6 confidence
self-report for review routing; §5.5 is otherwise fully covered.

## Mapping conventions (why some tags cross domain buckets)

The bank's `domain` field is the sampling bucket; `guide_section` is the
guide's own home for that content. They differ where the guide places
content differently than the bank's original taxonomy, e.g.:

- Deterministic-enforcement questions (claude_code/prompt_eng domains) tag
  **D1 §1.5** — the guide's home for hooks-vs-prompt enforcement.
- Strict-schema/structured-output questions in tool_mcp tag **D4 §4.3**.
- Verbose-isolation/scratchpad/memory questions across domains tag
  **D5 §5.4**; `empty_result_vs_access_failure` tags **D2 §2.2** (the same
  knowledge bullet also appears under §5.3, now separately covered).
- All 32 `off_blueprint` questions tag
  "Appendix — Out of scope for the exam (drill-only)".
