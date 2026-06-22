"""SQLite connection helpers and schema for the CCA-F study app."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Default is the bundled DB; ``CCA_DB_PATH`` lets a process run against a copy
# (e.g. a throwaway resume smoke test) without touching real attempt history.
_DEFAULT_DB = Path(__file__).parent / "data" / "study.db"
DB_PATH = Path(os.environ["CCA_DB_PATH"]) if os.environ.get("CCA_DB_PATH") else _DEFAULT_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS question (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  domain          TEXT NOT NULL CHECK(domain IN (
                    'agentic','claude_code','prompt_eng','tool_mcp','context',
                    'cli_reference'
                  )),
  scenario        TEXT NOT NULL CHECK(scenario IN (
                    'customer_support','code_generation','multi_agent_research',
                    'dev_productivity','cicd','data_extraction',
                    'cli_lookup'
                  )),
  principle       TEXT,
  stem            TEXT NOT NULL,
  choice_a        TEXT NOT NULL,
  choice_b        TEXT NOT NULL,
  choice_c        TEXT NOT NULL,
  choice_d        TEXT NOT NULL,
  correct         TEXT NOT NULL CHECK(correct IN ('A','B','C','D')),
  rationale_a     TEXT NOT NULL,
  rationale_b     TEXT NOT NULL,
  rationale_c     TEXT NOT NULL,
  rationale_d     TEXT NOT NULL,
  anti_pattern    TEXT,
  anti_pattern_slug TEXT,
  source          TEXT,
  created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attempt (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id     INTEGER NOT NULL REFERENCES question(id),
  selected        TEXT NOT NULL CHECK(selected IN ('A','B','C','D')),
  correct         INTEGER NOT NULL,
  attempted_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_question_domain ON question(domain);
CREATE INDEX IF NOT EXISTS idx_question_anti_pattern_slug ON question(anti_pattern_slug);
CREATE INDEX IF NOT EXISTS idx_attempt_question ON attempt(question_id);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


if __name__ == "__main__":
    init_schema()
    print(f"Initialized {DB_PATH}")
