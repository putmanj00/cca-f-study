"""Per-question "Learn more" doc links: schema, parsing, render, bank integrity."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from collections import Counter
from pathlib import Path

import jinja2

import app
import db

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "seed_data_v11_exam_guide_v0_2.json"


def _load_assemble():
    spec = importlib.util.spec_from_file_location(
        "assemble_new_bank", ROOT / "scripts" / "assemble_new_bank.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- label humanization -----------------------------------------------------

def test_doc_link_label_humanizes_slug() -> None:
    assert app._doc_link_label(
        "https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons"
    ) == "Handling stop reasons"
    # trailing slash + query/hash are stripped before the final segment
    assert app._doc_link_label(
        "https://code.claude.com/docs/en/sub-agents/?x=1#top"
    ) == "Sub agents"


def test_doc_link_label_uppercases_known_acronyms() -> None:
    assert app._doc_link_label(
        "https://claude.com/blog/agent-capabilities-api"
    ) == "Agent capabilities API"


# --- newline parsing --------------------------------------------------------

def test_doc_links_list_parses_and_skips_blanks() -> None:
    raw = "https://a.test/one\n\n  https://b.test/two  \n"
    parsed = app._doc_links_list(raw)
    assert [p["url"] for p in parsed] == ["https://a.test/one", "https://b.test/two"]
    assert parsed[0]["label"] == "One"


def test_doc_links_list_empty_is_empty() -> None:
    assert app._doc_links_list(None) == []
    assert app._doc_links_list("") == []


# --- schema + row enrichment ------------------------------------------------

def test_schema_has_doc_links_and_row_enriches(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        INSERT INTO question (
          domain, scenario, principle, stem,
          choice_a, choice_b, choice_c, choice_d, correct,
          rationale_a, rationale_b, rationale_c, rationale_d, doc_links
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "agentic", "customer_support", "p", "stem-with-links",
            "a", "b", "c", "d", "A", "ra", "rb", "rc", "rd",
            "https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools",
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM question WHERE stem = ?", ("stem-with-links",)).fetchone()
    q = app._row_to_question(row)
    assert len(q["doc_links_list"]) == 1
    assert q["doc_links_list"][0]["url"].endswith("/define-tools")
    assert q["doc_links_list"][0]["label"] == "Define tools"


def test_doc_links_column_nullable(db_path: Path) -> None:
    # A row with no doc_links must still insert and enrich to an empty list.
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    from conftest import insert_question

    qid = insert_question(conn, "no-links")
    conn.commit()
    row = conn.execute("SELECT * FROM question WHERE id = ?", (qid,)).fetchone()
    assert app._row_to_question(row)["doc_links_list"] == []


# --- template render --------------------------------------------------------

def _render_partial(q: dict) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    return env.get_template("_doc_links.html").render(q=q)


def test_partial_renders_learn_more_links() -> None:
    html = _render_partial(
        {"doc_links_list": [
            {"url": "https://platform.claude.com/docs/en/x", "label": "Define tools"},
        ]}
    )
    assert "Learn more" in html
    assert 'href="https://platform.claude.com/docs/en/x"' in html
    assert "Define tools" in html
    assert 'target="_blank"' in html and 'rel="noopener noreferrer"' in html


def test_partial_renders_nothing_without_links() -> None:
    assert _render_partial({"doc_links_list": []}).strip() == ""


# --- assemble regen preserves doc_links -------------------------------------

def test_assemble_build_row_preserves_doc_links() -> None:
    asm = _load_assemble()
    data = {
        "domain": "agentic", "scenario": "customer_support", "stem": "s",
        "correct_choice": "cc", "correct_rationale": "cr",
        "near_miss_choice": "nc", "near_miss_rationale": "nr",
        "distractor1_choice": "d1c", "distractor1_rationale": "d1r",
        "distractor2_choice": "d2c", "distractor2_rationale": "d2r",
        "doc_links": "https://platform.claude.com/docs/en/a\nhttps://code.claude.com/docs/en/b",
    }
    row = asm.build_row(data, correct_pos=0, idx=0)
    assert row["doc_links"] == data["doc_links"]
    # absent in source -> None (nullable), never raises
    del data["doc_links"]
    assert asm.build_row(data, correct_pos=1, idx=1)["doc_links"] is None


# --- shipped bank integrity -------------------------------------------------

def test_bank_every_question_has_doc_links() -> None:
    rows = json.loads(BANK.read_text())
    assert len(rows) == 142
    for r in rows:
        urls = [u for u in (r.get("doc_links") or "").splitlines() if u.strip()]
        assert urls, f"no doc_links: {r['stem'][:50]}"
        assert len(urls) <= 3, f">3 doc_links: {r['stem'][:50]}"
        for u in urls:
            assert u.startswith("https://"), u
            assert any(h in u for h in ("claude.com", "anthropic.com")), u


def test_bank_letter_balance_unchanged() -> None:
    rows = json.loads(BANK.read_text())
    dist = Counter(r["correct"] for r in rows)
    assert dict(sorted(dist.items())) == {"A": 37, "B": 36, "C": 35, "D": 34}
