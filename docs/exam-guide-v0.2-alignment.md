# Bank alignment to Exam Guide v0.2 (2026-06-30)

Source: `SecondBrain/instructor_*_Claude+Certified+Architect+-+Foundations+-+Exam+Guide.pdf`
(Version 0.2, Last Updated June 30 2026). Supersedes the blueprint the v10 bank
(2026-06-22) was built against.

## What changed in the exam

- **5 domains, new weightings**: D1 Agentic Architecture & Orchestration 27%,
  D2 Tool Design & MCP Integration 18%, D3 Claude Code Configuration &
  Workflows 20%, D4 Prompt Engineering & Structured Output 20%, D5 Context
  Management & Reliability 15%. (Old local weights were 25/20/20/20/15.)
- **No standalone CLI-reference domain.** CLI content (`-p`, `--output-format
  json`, `--json-schema`) now lives inside D3 task 3.6 (CI/CD).
- **6 scenarios, 4 drawn at random**: customer_support, code_generation,
  multi_agent_research, dev_productivity, cicd, data_extraction. `cli_lookup`
  scenario retired.
- 60 questions / 120 min / scaled 100–1000, pass 720 / $125 / valid 12 months.
- **Explicit out-of-scope list** (§Appendix) that large parts of the v10 bank
  sat in: prompt caching implementation details, streaming/SSE, rate
  limits/quotas/pricing calculations, token counting, model comparison,
  fine-tuning, auth/billing, computer use, vision, embeddings.

## Bank changes (v11)

1. **`off_blueprint` domain** (weight 0, replaces `cli_reference` as the
   zero-weight bucket): all v10 questions whose principle is on the guide's
   out-of-scope list move here rather than being deleted — still drillable by
   domain filter, never weighted-sampled. Biggest movers: the ~15
   prompt-caching questions, streaming, effort/adaptive-thinking, count_tokens,
   model-id/tier lookups, MCP-connector API, citations, API context-editing.
2. **Retags into guide domain homes** (guide places escalation & error
   propagation in D5, review architecture in D4, tool_choice in D2):
   escalation questions agentic→context, `separate_context_verification`
   agentic→prompt_eng, `empty_result_vs_access_failure` agentic→tool_mcp,
   `stateless_api_resend_history*` prompt_eng→context, plus in-scope
   cli_reference survivors (`enumerate_complete_stop_reason_set`→agentic,
   `tool_choice_value_semantics`→tool_mcp, batch pair→prompt_eng).
3. **~40 new questions** covering task statements the v10 bank missed
   entirely, all sourced from the guide (`source:
   exam_guide_v0_2_2026_06_30`): Task-tool/allowedTools, parallel subagent
   spawning, AgentDefinition context passing, PostToolUse hooks, prompt
   chaining vs adaptive decomposition, --resume/fork_session (D1);
   .mcp.json project-vs-user scoping + env expansion, MCP resources,
   built-in tool selection (D2); CLAUDE.md hierarchy/@import/.claude/rules/
   globs//memory, skills frontmatter (context: fork, allowed-tools,
   argument-hint), plan mode vs direct execution, --output-format
   json/--json-schema (D3); explicit review criteria, few-shot patterns,
   nullable-field fabrication guards, enum "other"+detail,
   retry-with-error-feedback, batch appropriateness, multi-pass review (D4);
   lost-in-the-middle, case-facts block, verbose-output trimming, scratchpad
   files/crash manifests, stratified sampling/confidence calibration,
   claim-source provenance/temporal conflicts (D5).
4. `DOMAIN_WEIGHT` updated to 27/18/20/20/15 (+ off_blueprint 0).

Bank counts need not match blueprint percentages — `pick_weighted_domain`
drives exam-like sampling; bank composition targets full task-statement
coverage instead.
