"""Shared fixtures: build a throwaway study.db from the real schema.

Tests exercise the pure selection helpers against a temp-file database (not the
app's data/study.db), opening fresh connections to simulate process restarts.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import db


def insert_question(
    conn: sqlite3.Connection,
    stem: str,
    domain: str = "agentic",
    anti_pattern: str | None = None,
) -> int:
    """Insert one minimal valid question; return its id."""
    cur = conn.execute(
        """
        INSERT INTO question (
          domain, scenario, principle, stem,
          choice_a, choice_b, choice_c, choice_d, correct,
          rationale_a, rationale_b, rationale_c, rationale_d,
          anti_pattern, source
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            domain, "customer_support", "p", stem,
            "a", "b", "c", "d", "A",
            "ra", "rb", "rc", "rd", anti_pattern, "test",
        ),
    )
    return int(cur.lastrowid)


def answer_question(conn: sqlite3.Connection, question_id: int, correct: int = 1) -> None:
    """Record one attempt, moving the question out of the unanswered set."""
    conn.execute(
        "INSERT INTO attempt (question_id, selected, correct) VALUES (?, ?, ?)",
        (question_id, "A", correct),
    )


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """A temp-file sqlite database with the production schema, no rows."""
    path = tmp_path / "study.db"
    conn = sqlite3.connect(path)
    conn.executescript(db.SCHEMA)
    conn.commit()
    conn.close()
    return path
