"""Backfill ``guide_section`` (Exam Guide v0.2 task statement) onto the bank.

Maps every question's ``principle`` to the exam-guide task statement it
covers, rewrites the v11 seed JSON in place, and migrates the live DB
(ALTER TABLE if needed + UPDATE by principle). Idempotent.

Source of truth for section titles:
``SecondBrain/instructor_*_Claude+Certified+Architect+-+Foundations+-+Exam+Guide.pdf``
(v0.2, 2026-06-30). Domains D1-D5, task statements 1.1-5.6.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import connect, init_schema  # noqa: E402

BASE_DIR = Path(__file__).parent.parent
V11 = BASE_DIR / "seed_data_v11_exam_guide_v0_2.json"

SECTIONS: dict[str, str] = {
    "1.1": "D1 §1.1 — Design and implement agentic loops for autonomous task execution",
    "1.2": "D1 §1.2 — Orchestrate multi-agent systems with coordinator-subagent patterns",
    "1.3": "D1 §1.3 — Configure subagent invocation, context passing, and spawning",
    "1.4": "D1 §1.4 — Implement multi-step workflows with enforcement and handoff patterns",
    "1.5": "D1 §1.5 — Apply Agent SDK hooks for tool call interception and data normalization",
    "1.6": "D1 §1.6 — Design task decomposition strategies for complex workflows",
    "1.7": "D1 §1.7 — Manage session state, resumption, and forking",
    "2.1": "D2 §2.1 — Design effective tool interfaces with clear descriptions and boundaries",
    "2.2": "D2 §2.2 — Implement structured error responses for MCP tools",
    "2.3": "D2 §2.3 — Distribute tools appropriately across agents and configure tool choice",
    "2.4": "D2 §2.4 — Integrate MCP servers into Claude Code and agent workflows",
    "2.5": "D2 §2.5 — Select and apply built-in tools (Read, Write, Edit, Bash, Grep, Glob) effectively",
    "3.1": "D3 §3.1 — Configure CLAUDE.md files with appropriate hierarchy, scoping, and modular organization",
    "3.2": "D3 §3.2 — Create and configure custom slash commands and skills",
    "3.3": "D3 §3.3 — Apply path-specific rules for conditional convention loading",
    "3.4": "D3 §3.4 — Determine when to use plan mode vs direct execution",
    "3.5": "D3 §3.5 — Apply iterative refinement techniques for progressive improvement",
    "3.6": "D3 §3.6 — Integrate Claude Code into CI/CD pipelines",
    "4.1": "D4 §4.1 — Design prompts with explicit criteria to improve precision and reduce false positives",
    "4.2": "D4 §4.2 — Apply few-shot prompting to improve output consistency and quality",
    "4.3": "D4 §4.3 — Enforce structured output using tool use and JSON schemas",
    "4.4": "D4 §4.4 — Implement validation, retry, and feedback loops for extraction quality",
    "4.5": "D4 §4.5 — Design efficient batch processing strategies",
    "4.6": "D4 §4.6 — Design multi-instance and multi-pass review architectures",
    "5.1": "D5 §5.1 — Manage conversation context to preserve critical information across long interactions",
    "5.2": "D5 §5.2 — Design effective escalation and ambiguity resolution patterns",
    "5.3": "D5 §5.3 — Implement error propagation strategies across multi-agent systems",
    "5.4": "D5 §5.4 — Manage context effectively in large codebase exploration",
    "5.5": "D5 §5.5 — Design human review workflows and confidence calibration",
    "5.6": "D5 §5.6 — Preserve information provenance and handle uncertainty in multi-source synthesis",
}

OUT_OF_SCOPE = "Appendix — Out of scope for the exam (drill-only)"

# principle -> task statement key. Questions whose domain is off_blueprint
# get OUT_OF_SCOPE regardless of this map.
PRINCIPLE_SECTION: dict[str, str] = {
    # --- agentic (D1 home, some content lives in D2/D5 per the guide) ---
    "terminate_loop_on_stop_reason_not_text": "1.1",
    "loop_termination_on_stop_reason_not_iteration_cap": "1.1",
    "enumerate_complete_stop_reason_set": "1.1",
    "parallel_tool_results_single_user_message": "1.1",
    "route_subagent_communication_through_coordinator": "1.2",
    "coordinator_subagent_context_isolation_and_flat_delegation": "1.2",
    "coordinator_decomposition_breadth_covers_topic_scope": "1.2",
    "async_retained_context_vs_spawn_and_block_delegation": "1.2",
    "subagent_spawn_cost_vs_context_isolation": "1.3",
    "pass_findings_explicitly_with_content_metadata_separation": "1.3",
    "parallel_subagents_via_multiple_task_calls_single_response": "1.3",
    "coordinator_allowed_tools_must_include_task": "1.3",
    "define_done_via_outcome_and_gradeable_rubric": "1.3",
    "structured_escalation_handoff_with_case_facts": "1.4",
    "posttooluse_hook_normalizes_heterogeneous_tool_data": "1.5",
    "interception_hook_blocks_policy_violating_refunds": "1.5",
    "prompt_chaining_for_predictable_dynamic_decomposition_for_open_ended": "1.6",
    "match_workflow_shape_to_task_structure": "1.6",
    "fresh_session_with_structured_summary_over_stale_resume": "1.7",
    "file_based_memory_for_cross_session_state": "5.4",
    "isolate_verbose_discovery_in_subagent": "5.4",
    "tool_choice_force_vs_disable_parallel": "2.3",
    "scope_tools_per_agent_for_selection_accuracy": "2.3",
    "surface_failed_tool_call_with_is_error": "2.2",
    # --- tool_mcp ---
    "tool_description_states_when_to_call": "2.1",
    "promote_action_to_dedicated_tool_for_staleness_gate": "2.1",
    "parallel_safe_tool_promotion": "2.1",
    "gate_hard_to_reverse_actions_via_dedicated_tool": "2.1",
    "structured_tool_error_design": "2.2",
    "server_tool_error_is_a_result_block_not_an_exception": "2.2",
    "empty_result_vs_access_failure": "2.2",
    "tool_choice_value_semantics": "2.3",
    "mcp_resources_expose_catalog_to_cut_exploratory_calls": "2.4",
    "mcp_project_scope_env_expansion_for_shared_credentials": "2.4",
    "mcp_credential_storage_in_vault_not_agent_definition": "2.4",
    "match_tool_surface_to_execution_environment": "2.5",
    "grep_entry_points_then_read_not_bulk_upfront_reading": "2.5",
    "edit_non_unique_match_read_write_fallback": "2.5",
    "parse_tool_input_with_json_parser": "1.1",
    "parallel_tool_result_correlation": "1.1",
    "deterministic_redaction_in_tool_handler_not_prompt": "1.5",
    "offload_large_tool_results_out_of_context": "5.1",
    "strict_schema_requires_additionalproperties_false": "4.3",
    "strict_goes_on_tool_definition_not_tool_choice": "4.3",
    "enum_constrains_field_but_strict_enforces_schema": "4.3",
    "enforce_structured_json_via_output_config_not_prefill": "4.3",
    # --- claude_code ---
    "project_claude_md_shared_via_vcs_not_user_level": "3.1",
    "durable_conventions_in_claude_md_vs_per_prompt_repetition": "3.1",
    "diagnose_instruction_loading_with_memory_command": "3.1",
    "at_import_selective_standards_per_package": "3.1",
    "workflow_packaging_vs_deterministic_enforcement": "3.2",
    "team_slash_command_in_project_commands_dir": "3.2",
    "skill_context_fork_isolates_verbose_output": "3.2",
    "path_scoped_rules_for_conventions_spanning_directories": "3.3",
    "subagent_type_selection_by_output_contract": "3.4",
    "subagent_isolation_when_discovery_is_verbose": "3.4",
    "subagent_fanout_preserves_main_context": "3.4",
    "plan_mode_for_architectural_scope_direct_for_bounded_fix": "3.4",
    "isolate_verbose_discovery_in_subagent_context": "3.4",
    "concrete_io_examples_over_prose_for_ambiguous_transformations": "3.5",
    "verify_by_running_not_by_self_report": "3.6",
    "json_schema_flag_for_machine_parseable_ci_findings": "3.6",
    "headless_vs_interactive_for_unattended_jobs": "3.6",
    "prompt_instruction_vs_deterministic_hook_enforcement": "1.5",
    "enforce_gate_with_permission_mode_not_prompt": "1.5",
    "enforce_destructive_git_gate_with_hook_not_prompt": "1.5",
    "deterministic_hook_vs_advisory_prompt_enforcement": "1.5",
    "deterministic_gating_of_tool_actions": "1.5",
    "deterministic_enforcement_via_hook_not_prompt": "1.5",
    "claude_md_vs_hook_enforcement": "1.5",
    "proactive_context_isolation_over_reactive_compaction": "5.4",
    "isolate_verbose_work_in_subagent_not_compact": "5.4",
    # --- prompt_eng ---
    "explicit_categorical_criteria_over_vague_confidence_instructions": "4.1",
    "disable_high_fp_category_to_restore_trust_while_iterating": "4.1",
    "few_shot_varied_document_structures_reduce_extraction_hallucination": "4.2",
    "few_shot_reasoned_examples_for_ambiguous_case_handling": "4.2",
    "structured_output_schema_supported_constraints": "4.3",
    "strict_tool_use_placement_and_schema_requirements": "4.3",
    "parse_tool_input_as_json_not_string_match": "4.3",
    "nullable_optional_fields_prevent_fabricated_values": "4.3",
    "guarantee_json_shape_with_output_config_format_not_prefill": "4.3",
    "enum_unclear_and_other_detail_for_extensible_categorization": "4.3",
    "constrain_label_set_via_tool_enum_not_free_text": "4.3",
    "retry_with_validation_error_feedback_and_absence_limits": "4.4",
    "detected_pattern_field_enables_false_positive_analysis": "4.4",
    "message_batch_limits_and_pricing": "4.5",
    "batch_results_keyed_by_custom_id": "4.5",
    "batch_api_for_latency_tolerant_workloads_custom_id_resubmission": "4.5",
    "separate_context_verification": "4.6",
    "per_file_passes_plus_cross_file_integration_pass": "4.6",
    "prescriptive_tool_description_raises_should_call_rate": "2.1",
    "enforce_hard_requirements_with_hooks_not_louder_prompt_imperatives": "1.5",
    # --- context ---
    "retrieve_only_needed_vs_fill_context": "5.1",
    "preserve_full_response_content_in_history": "5.1",
    "persistent_case_facts_block_outside_summarized_history": "5.1",
    "lead_with_summary_and_headers_to_mitigate_position_effects": "5.1",
    "distinguish_context_window_exceeded_from_max_tokens_stop": "5.1",
    "request_additional_identifiers_on_multiple_matches": "5.2",
    "honor_explicit_human_request_without_first_investigating": "5.2",
    "escalate_on_structured_criteria_not_self_reported_confidence": "5.2",
    "escalate_on_complexity_or_policy_gap_not_sentiment": "5.2",
    "structured_state_manifests_for_crash_recovery": "5.4",
    "scratchpad_files_counteract_context_degradation": "5.4",
    "proactive_context_isolation_via_subagent": "5.4",
    "memory_tool_for_cross_session_persistence_vs_in_context_state": "5.4",
    "stratified_sampling_of_high_confidence_extractions": "5.5",
    "report_per_doctype_accuracy_not_aggregate": "5.5",
    "calibrate_field_confidence_with_labeled_validation_sets": "5.5",
    "require_publication_dates_to_prevent_temporal_false_conflicts": "5.6",
    "preserve_claim_source_mappings_through_synthesis": "5.6",
}


def section_for(row: dict) -> str:
    if row["domain"] == "off_blueprint":
        return OUT_OF_SCOPE
    key = PRINCIPLE_SECTION.get(row.get("principle") or "")
    if key is None:
        raise SystemExit(f"unmapped principle: {row.get('principle')!r}")
    return SECTIONS[key]


def rewrite_seed() -> int:
    data = json.loads(V11.read_text())
    for row in data:
        row["guide_section"] = section_for(row)
    V11.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return len(data)


def migrate_db() -> tuple[int, int]:
    init_schema()
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(question)")}
        if "guide_section" not in cols:
            conn.execute("ALTER TABLE question ADD COLUMN guide_section TEXT")
        updated = 0
        for principle, key in PRINCIPLE_SECTION.items():
            cur = conn.execute(
                "UPDATE question SET guide_section = ? WHERE principle = ? "
                "AND domain != 'off_blueprint'",
                (SECTIONS[key], principle),
            )
            updated += cur.rowcount
        cur = conn.execute(
            "UPDATE question SET guide_section = ? WHERE domain = 'off_blueprint'",
            (OUT_OF_SCOPE,),
        )
        off = cur.rowcount
        conn.commit()
    return updated, off


if __name__ == "__main__":
    n = rewrite_seed()
    updated, off = migrate_db()
    print(f"seed rows tagged: {n}")
    print(f"db rows updated: {updated} in-scope, {off} off_blueprint")
    with connect() as conn:
        missing = conn.execute(
            "SELECT COUNT(*) FROM question WHERE guide_section IS NULL"
        ).fetchone()[0]
    print(f"db rows still missing guide_section: {missing}")
