#!/usr/bin/env python3
"""Build the v11 seed bank aligned to Exam Guide v0.2 (2026-06-30).

Two inputs, one output (see docs/exam-guide-v0.2-alignment.md for rationale):

1. The v10 seed file: every question is carried forward, with (a) questions on
   topics the guide lists as out of scope retagged to the zero-weight
   ``off_blueprint`` domain, and (b) a handful of in-scope questions retagged
   to the guide's domain home (escalation -> D5, review architecture -> D4,
   tool_choice -> D2, in-scope cli_reference survivors -> weighted domains).
2. New role-keyed question drafts (``newq_*.json``, same format as
   assemble_new_bank.py's inputs) covering guide task statements the v10 bank
   missed. Correct-answer letters are assigned with the same balanced,
   deterministic shuffle as the v10 build.

Deterministic: same inputs -> same output. Anything skipped is reported
explicitly (no silent drops).

Usage:
    uv run python scripts/build_v11_bank.py <new_q_dir>
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assemble_new_bank import (  # noqa: E402
    LETTERS,
    REQUIRED,
    SLUGS,
    balanced_positions,
    build_row,
)

BASE = Path(__file__).resolve().parent.parent
V10 = BASE / "archive" / "seed_data_v10_original_2026_06.json"
OUT = BASE / "seed_data_v11_exam_guide_v0_2.json"
SEED = 20260712

DOMAINS = {"agentic", "claude_code", "prompt_eng", "tool_mcp", "context", "off_blueprint"}
SCENARIOS = {
    "customer_support", "code_generation", "multi_agent_research",
    "dev_productivity", "cicd", "data_extraction", "cli_lookup",
}

# (domain, principle) -> new domain. Everything else keeps its v10 domain.
# "off_blueprint" entries match the guide's explicit out-of-scope list:
# prompt-caching internals, streaming, pricing/quotas, token counting, model
# comparison — plus API features absent from the guide (MCP connector, API
# context editing, citations, programmatic tool calling, effort/thinking).
RETAG: dict[tuple[str, str], str] = {
    # -- out of scope -> off_blueprint --
    ("agentic", "match_tier_to_task_determinism"): "off_blueprint",
    ("agentic", "programmatic_tool_calling_keeps_intermediate_results_out_of_context"): "off_blueprint",
    ("agentic", "subagent_model_isolation_vs_main_loop_model_switch_cache_impact"): "off_blueprint",
    ("agentic", "compaction_vs_context_editing_selection"): "off_blueprint",
    ("tool_mcp", "mcp_connector_requires_server_plus_matching_toolset"): "off_blueprint",
    ("tool_mcp", "tool_search_preserves_cache_prefix"): "off_blueprint",
    ("prompt_eng", "cache_prefix_stable_first_volatile_last"): "off_blueprint",
    ("prompt_eng", "cache_breakpoint_placement_respects_render_order"): "off_blueprint",
    ("prompt_eng", "place_volatile_content_after_cache_breakpoint"): "off_blueprint",
    ("prompt_eng", "stable_prefix_volatile_last_for_cache_hits"): "off_blueprint",
    ("prompt_eng", "tool_choice_force_specific_tool_preserves_cache"): "off_blueprint",
    ("prompt_eng", "use_adaptive_thinking_not_fixed_budget_tokens"): "off_blueprint",
    ("prompt_eng", "effort_level_tradeoff_for_volume_vs_capability"): "off_blueprint",
    ("prompt_eng", "mid_conversation_instruction_placement_preserves_cache"): "off_blueprint",
    ("prompt_eng", "enable_citations_on_document_block"): "off_blueprint",
    ("prompt_eng", "measure_prompt_size_with_count_tokens_not_tiktoken"): "off_blueprint",
    ("prompt_eng", "cache_prefix_render_order"): "off_blueprint",
    ("prompt_eng", "stateless_api_resend_history_with_stable_cached_prefix"): "off_blueprint",
    ("context", "compaction_vs_context_editing_selection"): "off_blueprint",
    ("context", "stable_prefix_volatile_suffix_for_cache_hits"): "off_blueprint",
    ("context", "cache_break_even_requires_stable_prefix"): "off_blueprint",
    ("context", "cache_ttl_selection_by_reuse_frequency"): "off_blueprint",
    ("context", "stream_large_outputs_to_avoid_idle_connection_timeout"): "off_blueprint",
    ("context", "preserve_cached_prefix_no_midsession_model_or_tool_swap"): "off_blueprint",
    ("context", "cache_prefix_reuse_requires_identical_prefix_and_model"): "off_blueprint",
    ("context", "match_context_edit_strategy_to_bloat_source"): "off_blueprint",
    ("cli_reference", "model_id_and_context_window_lookup"): "off_blueprint",
    ("cli_reference", "prompt_cache_ttl_defaults"): "off_blueprint",
    ("cli_reference", "cache_control_breakpoint_limit"): "off_blueprint",
    ("cli_reference", "use_model_specific_count_tokens_endpoint"): "off_blueprint",
    ("cli_reference", "effort_level_tier_support"): "off_blueprint",
    ("cli_reference", "mcp_connector_requires_server_and_toolset"): "off_blueprint",
    # -- in scope, moved to the guide's domain home --
    ("agentic", "escalate_on_complexity_or_policy_gap_not_sentiment"): "context",       # 5.2
    ("agentic", "escalate_on_structured_criteria_not_self_reported_confidence"): "context",  # 5.2
    ("agentic", "separate_context_verification"): "prompt_eng",                          # 4.6
    ("agentic", "empty_result_vs_access_failure"): "tool_mcp",                           # 2.2
    ("cli_reference", "enumerate_complete_stop_reason_set"): "agentic",                  # 1.1
    ("cli_reference", "tool_choice_value_semantics"): "tool_mcp",                        # 2.3
    ("cli_reference", "message_batch_limits_and_pricing"): "prompt_eng",                 # 4.5
    ("cli_reference", "batch_results_keyed_by_custom_id"): "prompt_eng",                 # 4.5
}

# In-scope cli_reference survivors leave the retired cli_lookup scenario.
RESCENARIO: dict[tuple[str, str], str] = {
    ("cli_reference", "enumerate_complete_stop_reason_set"): "multi_agent_research",
    ("cli_reference", "tool_choice_value_semantics"): "data_extraction",
    ("cli_reference", "message_batch_limits_and_pricing"): "data_extraction",
    ("cli_reference", "batch_results_keyed_by_custom_id"): "data_extraction",
}


def retag_v10() -> list[dict]:
    rows = json.loads(V10.read_text())
    applied: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["domain"], row["principle"])
        if key in RESCENARIO:
            row["scenario"] = RESCENARIO[key]
        if key in RETAG:
            row["domain"] = RETAG[key]
            applied.add(key)
        elif row["domain"] == "cli_reference":  # leftover zero-weight rows
            row["domain"] = "off_blueprint"
    missing = set(RETAG) - applied
    if missing:
        raise SystemExit(f"retag keys not found in v10 seed: {sorted(missing)}")
    return rows


def load_new(src: Path) -> list[dict]:
    items: list[dict] = []
    problems: list[str] = []
    seen_principles: set[str] = set()
    for path in sorted(src.glob("newq_*.json")):
        for i, data in enumerate(json.loads(path.read_text())):
            tag = f"{path.name}[{i}]"
            missing = (REQUIRED | {"principle", "doc_links", "source"}) - set(data)
            if missing:
                problems.append(f"{tag}: missing keys {sorted(missing)}")
                continue
            if data["domain"] not in DOMAINS or data["scenario"] not in SCENARIOS:
                problems.append(f"{tag}: bad domain/scenario")
                continue
            if data["principle"] in seen_principles:
                problems.append(f"{tag}: duplicate principle {data['principle']}")
                continue
            slug = data.get("anti_pattern_slug")
            if slug is not None and slug not in SLUGS:
                problems.append(f"{tag}: unknown anti_pattern_slug {slug!r} (nulled)")
                data["anti_pattern_slug"] = None
            seen_principles.add(data["principle"])
            items.append(data)
    for p in problems:
        print(f"NOTE: {p}", file=sys.stderr)
    return items


def main() -> None:
    src = Path(sys.argv[1])
    old_rows = retag_v10()
    old_all_principles = {r["principle"] for r in old_rows}

    new_items = [
        d for d in load_new(src)
        if d["principle"] not in old_all_principles
        or print(f"NOTE: dropped duplicate of existing principle {d['principle']}", file=sys.stderr)
    ]
    positions = balanced_positions(len(new_items), Random(SEED))
    new_rows = [build_row(d, pos, idx) for idx, (d, pos) in enumerate(zip(new_items, positions))]
    for d, row in zip(new_items, new_rows):
        row["source"] = d.get("source", "exam_guide_v0_2_2026_06_30")

    rows = old_rows + new_rows
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} questions ({len(old_rows)} carried, {len(new_rows)} new) -> {OUT.name}")
    print("per-domain:", dict(sorted(Counter(r['domain'] for r in rows).items())))
    print("new-Q correct letters:", dict(sorted(Counter(r['correct'] for r in new_rows).items())))
    in_scope = [r for r in rows if r["domain"] != "off_blueprint"]
    print(f"in-scope: {len(in_scope)}, off_blueprint: {len(rows) - len(in_scope)}")


if __name__ == "__main__":
    main()
