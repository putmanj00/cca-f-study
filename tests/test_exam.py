"""Exam sampler allocation + appendix exclusion in the unanswered helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from random import Random

from conftest import answer_question, insert_question

import selection


def _open(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _seed_bank(conn: sqlite3.Connection, per_domain: dict[str, int]) -> None:
    for domain, n in per_domain.items():
        for i in range(n):
            insert_question(conn, f"{domain}-{i}", domain=domain)
    conn.commit()


def test_exam_allocation_matches_blueprint_for_60() -> None:
    available = {
        "agentic": 27, "tool_mcp": 22, "claude_code": 28,
        "prompt_eng": 20, "context": 21, "off_blueprint": 32,
    }
    alloc = selection.exam_allocation(available, total=60)
    assert sum(alloc.values()) == 60
    assert "off_blueprint" not in alloc
    # 27/18/20/20/15% of 60 with largest-remainder rounding.
    assert alloc == {
        "agentic": 16, "tool_mcp": 11, "claude_code": 12,
        "prompt_eng": 12, "context": 9,
    }


def test_exam_allocation_caps_at_available_bank() -> None:
    available = {"agentic": 3, "context": 100}
    alloc = selection.exam_allocation(available, total=60)
    assert alloc["agentic"] == 3
    assert alloc["context"] == 57
    assert sum(alloc.values()) == 60


def test_exam_allocation_short_bank_returns_fewer() -> None:
    alloc = selection.exam_allocation({"agentic": 2, "context": 3}, total=60)
    assert alloc == {"agentic": 2, "context": 3}


def test_exam_allocation_empty_bank() -> None:
    assert selection.exam_allocation({}, total=60) == {}
    assert selection.exam_allocation({"off_blueprint": 40}, total=60) == {}


def test_sample_exam_questions_excludes_off_blueprint(db_path: Path) -> None:
    conn = _open(db_path)
    _seed_bank(conn, {
        "agentic": 20, "tool_mcp": 15, "claude_code": 15,
        "prompt_eng": 15, "context": 15, "off_blueprint": 10,
    })
    ids = selection.sample_exam_questions(conn, Random(7), total=60)
    assert len(ids) == 60
    assert len(set(ids)) == 60  # without replacement
    domains = {
        r[0]
        for r in conn.execute(
            f"SELECT DISTINCT domain FROM question WHERE id IN ({','.join('?' * len(ids))})",
            ids,
        ).fetchall()
    }
    assert "off_blueprint" not in domains


def test_unanswered_helpers_exclude_domain(db_path: Path) -> None:
    conn = _open(db_path)
    a = insert_question(conn, "q-app", domain="off_blueprint")
    b = insert_question(conn, "q-core", domain="context")
    conn.commit()

    assert selection.unanswered_count(conn) == 2
    assert selection.unanswered_count(conn, exclude_domain="off_blueprint") == 1
    head = selection.next_unanswered(conn, exclude_domain="off_blueprint")
    assert head["id"] == b

    answer_question(conn, b)
    conn.commit()
    assert selection.unanswered_count(conn, exclude_domain="off_blueprint") == 0
    assert selection.next_unanswered(conn, exclude_domain="off_blueprint") is None
    # Explicit appendix drill still sees its questions.
    assert selection.next_unanswered(conn, domain="off_blueprint")["id"] == a
