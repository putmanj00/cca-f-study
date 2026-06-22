"""Per-anti-pattern stats: slug-tagged + attempted only, worst-first."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from conftest import answer_question, insert_question

import selection


def _tag(conn: sqlite3.Connection, question_id: int, slug: str) -> None:
    conn.execute(
        "UPDATE question SET anti_pattern_slug = ? WHERE id = ?", (slug, question_id)
    )


def test_stats_aggregate_by_slug_worst_first(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # generic-error: 1/2 correct (50%); too-many-tools: 2/2 correct (100%).
    ge1 = insert_question(conn, "ge1")
    ge2 = insert_question(conn, "ge2")
    tmt = insert_question(conn, "tmt")
    for q in (ge1, ge2):
        _tag(conn, q, "generic-error")
    _tag(conn, tmt, "too-many-tools")
    answer_question(conn, ge1, correct=1)
    answer_question(conn, ge2, correct=0)
    answer_question(conn, tmt, correct=1)
    answer_question(conn, tmt, correct=1)
    conn.commit()

    stats = selection.anti_pattern_stats(conn)
    assert [s["slug"] for s in stats] == ["generic-error", "too-many-tools"]
    worst = stats[0]
    assert worst["attempts"] == 2 and worst["correct"] == 1
    assert worst["pct_str"] == "50%" and worst["bucket"] == "bad"
    assert stats[1]["pct_str"] == "100%" and stats[1]["bucket"] == "ok"
    # Label resolves from the blueprint catalog, not the raw slug.
    assert worst["label"] == selection.ANTI_PATTERN_LABEL["generic-error"]


def test_stats_exclude_untagged_questions(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Free-text anti_pattern but no slug -> must not appear in slug stats.
    q = insert_question(conn, "free", anti_pattern="some free-text prose")
    answer_question(conn, q, correct=0)
    conn.commit()
    assert selection.anti_pattern_stats(conn) == []


def test_stats_exclude_slug_with_no_attempts(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    q = insert_question(conn, "tagged_unanswered")
    _tag(conn, q, "iteration-cap")
    conn.commit()
    # Tagged but never attempted -> excluded (HAVING attempts > 0).
    assert selection.anti_pattern_stats(conn) == []
