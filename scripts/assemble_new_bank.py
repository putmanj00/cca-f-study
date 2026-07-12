#!/usr/bin/env python3
"""Assemble verified question objects into a seedable practice bank.

Reads the role-keyed question JSON produced by the generation/verification
workflow (``/tmp/cca_gen/verified/q*.json``), assigns A-D answer positions with
a balanced, deterministic shuffle (uniform correct-answer distribution, never a
run of the same correct letter longer than two), validates the schema enums, and
writes a single flat seed file the app can load via ``seed.py``.

Deterministic: same inputs produce the same output (fixed RNG seed). No network,
no model calls. Anything skipped is reported explicitly (no silent drops).

Usage:
    uv run python scripts/assemble_new_bank.py [SRC_DIR]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from random import Random

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/cca_gen/verified")
OUT = Path(__file__).resolve().parent.parent / "seed_data_v10_original_2026_06.json"
SEED = 20260622

DOMAINS = {"agentic", "claude_code", "prompt_eng", "tool_mcp", "context", "off_blueprint"}
SCENARIOS = {
    "customer_support", "code_generation", "multi_agent_research",
    "dev_productivity", "cicd", "data_extraction", "cli_lookup",
}
SLUGS = {
    "loop-termination-nl", "iteration-cap", "prompt-vs-hook", "confidence-escalation",
    "sentiment-escalation", "generic-error", "empty-as-success", "too-many-tools",
    "same-session-review", "aggregate-metrics",
}
LETTERS = ["A", "B", "C", "D"]
REQUIRED = {
    "domain", "scenario", "stem",
    "correct_choice", "correct_rationale",
    "near_miss_choice", "near_miss_rationale",
    "distractor1_choice", "distractor1_rationale",
    "distractor2_choice", "distractor2_rationale",
}


def load(src: Path) -> tuple[list[tuple[str, dict]], list[tuple[str, str]]]:
    """Return (valid items, skipped) where skipped is (filename, reason)."""
    items: list[tuple[str, dict]] = []
    skipped: list[tuple[str, str]] = []
    for path in sorted(src.glob("q*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception as exc:  # noqa: BLE001 - report and continue
            skipped.append((path.name, f"unreadable: {exc}"))
            continue
        missing = REQUIRED - set(data)
        if missing:
            skipped.append((path.name, f"missing keys: {sorted(missing)}"))
            continue
        if data["domain"] not in DOMAINS:
            skipped.append((path.name, f"bad domain {data['domain']!r}"))
            continue
        if data["scenario"] not in SCENARIOS:
            skipped.append((path.name, f"bad scenario {data['scenario']!r}"))
            continue
        items.append((path.name, data))
    return items, skipped


def balanced_positions(n: int, rng: Random) -> list[int]:
    """Even-as-possible spread of correct positions (0-3), no run longer than 2."""
    base = [i % 4 for i in range(n)]
    rng.shuffle(base)
    for i in range(2, n):
        if base[i] == base[i - 1] == base[i - 2]:
            for j in range(i + 1, n):
                if base[j] != base[i]:
                    base[i], base[j] = base[j], base[i]
                    break
    return base


def build_row(data: dict, correct_pos: int, idx: int) -> dict:
    """Place the four role-keyed choices into A-D with the correct one at correct_pos."""
    others = ["near_miss", "distractor1", "distractor2"]
    Random(SEED + idx).shuffle(others)
    slot_role: list[str | None] = [None, None, None, None]
    slot_role[correct_pos] = "correct"
    fill = iter(others)
    for k in range(4):
        if slot_role[k] is None:
            slot_role[k] = next(fill)

    slug = data.get("anti_pattern_slug")
    slug = slug if slug in SLUGS else None
    row = {
        "domain": data["domain"],
        "scenario": data["scenario"],
        "principle": data.get("principle"),
        "stem": data["stem"],
        "correct": LETTERS[correct_pos],
        "anti_pattern": data.get("anti_pattern"),
        "anti_pattern_slug": slug,
        "source": data.get("source", "original_public_docs_2026_06"),
        # Newline-separated canonical Anthropic doc URLs ("Learn more"); carried
        # through from the verified source so a regen preserves the links.
        "doc_links": data.get("doc_links"),
    }
    for k in range(4):
        role = slot_role[k]
        letter = LETTERS[k].lower()
        row[f"choice_{letter}"] = data[f"{role}_choice"]
        row[f"rationale_{letter}"] = data[f"{role}_rationale"]
    return row


def main() -> None:
    if not SRC.exists():
        print(f"source dir not found: {SRC}", file=sys.stderr)
        sys.exit(1)
    items, skipped = load(SRC)
    if not items:
        print(f"no valid questions found in {SRC}", file=sys.stderr)
        sys.exit(1)

    positions = balanced_positions(len(items), Random(SEED))
    rows = [
        build_row(data, pos, idx)
        for idx, ((_, data), pos) in enumerate(zip(items, positions))
    ]
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")

    dist = Counter(r["correct"] for r in rows)
    dom = Counter(r["domain"] for r in rows)
    print(f"wrote {len(rows)} questions -> {OUT.name}")
    print("correct-letter distribution:", dict(sorted(dist.items())))
    print("per-domain:", dict(sorted(dom.items())))
    if skipped:
        print(f"\nSKIPPED {len(skipped)} (disclosed, not silently dropped):")
        for name, why in skipped:
            print(f"  {name}: {why}")


if __name__ == "__main__":
    main()
