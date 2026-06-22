"""Unanswered set computation + resume cursor across restart."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from conftest import answer_question, insert_question

import selection


def _open(db_path: Path) -> sqlite3.Connection:
    """Open a fresh connection — each open stands in for a process restart."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def test_unanswered_count_total_and_by_domain(db_path: Path) -> None:
    conn = _open(db_path)
    insert_question(conn, "q1", domain="agentic")
    insert_question(conn, "q2", domain="agentic")
    insert_question(conn, "q3", domain="context")
    conn.commit()

    assert selection.unanswered_count(conn) == 3
    assert selection.unanswered_count(conn, domain="agentic") == 2
    assert selection.unanswered_count(conn, domain="context") == 1
    assert selection.unanswered_count(conn, domain="tool_mcp") == 0


def test_next_unanswered_is_stable_head(db_path: Path) -> None:
    """Viewing without answering must return the same question (resume head)."""
    conn = _open(db_path)
    first = insert_question(conn, "q1", domain="agentic")
    insert_question(conn, "q2", domain="agentic")
    conn.commit()

    assert selection.next_unanswered(conn)["id"] == first
    # Called again with no attempt recorded -> identical head.
    assert selection.next_unanswered(conn)["id"] == first


def test_resume_advances_in_order_across_restart(db_path: Path) -> None:
    # Seed five questions in one domain so (domain, id) order == insertion order.
    setup = _open(db_path)
    ids = [insert_question(setup, f"q{i}", domain="agentic") for i in range(5)]
    setup.commit()
    setup.close()
    assert ids == sorted(ids)

    served: list[int] = []
    for _ in range(5):
        conn = _open(db_path)  # "restart" — no in-memory cursor carried over
        row = selection.next_unanswered(conn)
        assert row is not None
        served.append(row["id"])
        answer_question(conn, row["id"])
        conn.commit()
        conn.close()

    # Each restart resumed exactly where the last left off, in ascending order.
    assert served == ids

    # Set now exhausted.
    conn = _open(db_path)
    assert selection.next_unanswered(conn) is None
    assert selection.unanswered_count(conn) == 0


def test_resume_respects_domain_filter(db_path: Path) -> None:
    conn = _open(db_path)
    a1 = insert_question(conn, "a1", domain="agentic")
    insert_question(conn, "c1", domain="context")
    conn.commit()

    # Answer the agentic one; only the context question remains unanswered.
    answer_question(conn, a1)
    conn.commit()

    assert selection.next_unanswered(conn, domain="agentic") is None
    assert selection.unanswered_count(conn, domain="agentic") == 0
    assert selection.next_unanswered(conn, domain="context")["stem"] == "c1"
