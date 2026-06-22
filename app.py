"""CCA-F study app: FastAPI + SQLite + Jinja2 + HTMX."""

from __future__ import annotations

import sqlite3
import random
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from db import connect, init_schema
from selection import (
    DOMAIN_WEIGHT,
    anti_pattern_stats,
    next_unanswered,
    next_weighted,
    unanswered_count,
)

BASE_DIR = Path(__file__).parent

DOMAINS = (
    "agentic", "claude_code", "prompt_eng", "tool_mcp", "context",
    "cli_reference",
)
SCENARIOS = (
    "customer_support", "code_generation", "multi_agent_research",
    "dev_productivity", "cicd", "data_extraction",
    "cli_lookup",
)
CHOICES = ("A", "B", "C", "D")

app = FastAPI(title="CCA-F Study App")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
def _startup() -> None:
    init_schema()


_LABEL_ACRONYMS = {"api", "mcp", "sdk", "cli", "ci", "cd", "pr", "json", "url", "llm"}


def _doc_link_label(url: str) -> str:
    """Humanize a doc URL's final path segment into a readable link label."""
    seg = url.split("#")[0].split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    words = seg.replace("_", " ").replace("-", " ").split()
    if not words:
        return url
    out = [
        w.upper() if w.lower() in _LABEL_ACRONYMS else (w.capitalize() if i == 0 else w)
        for i, w in enumerate(words)
    ]
    return " ".join(out)


def _doc_links_list(raw: Optional[str]) -> list[dict]:
    """Parse the newline-separated ``doc_links`` field into {url, label} dicts."""
    return [
        {"url": u, "label": _doc_link_label(u)}
        for u in (line.strip() for line in (raw or "").splitlines())
        if u
    ]


def _row_to_question(row: sqlite3.Row) -> dict:
    q = dict(row)
    q["choices"] = [
        ("A", q["choice_a"]),
        ("B", q["choice_b"]),
        ("C", q["choice_c"]),
        ("D", q["choice_d"]),
    ]
    q["rationales"] = {
        "A": q["rationale_a"],
        "B": q["rationale_b"],
        "C": q["rationale_c"],
        "D": q["rationale_d"],
    }
    q["doc_links_list"] = _doc_links_list(q.get("doc_links"))
    return q


def _new_choice_order() -> str:
    order = list(CHOICES)
    random.SystemRandom().shuffle(order)
    return "".join(order)


def _valid_choice_order(choice_order: str) -> bool:
    return len(choice_order) == len(CHOICES) and set(choice_order) == set(CHOICES)


def _apply_choice_order(q: dict, choice_order: Optional[str] = None) -> dict:
    order = choice_order if choice_order and _valid_choice_order(choice_order) else _new_choice_order()
    q["choice_order"] = order
    q["display_choices"] = [
        (display, original, q[f"choice_{original.lower()}"])
        for display, original in zip(CHOICES, order)
    ]
    q["display_rationales"] = {
        display: q["rationales"][original]
        for display, original in zip(CHOICES, order)
    }
    q["display_correct"] = CHOICES[order.index(q["correct"])]
    return q


def _selected_original(selected: str, choice_order: str) -> str:
    if selected not in CHOICES or not _valid_choice_order(choice_order):
        raise ValueError("Invalid selected choice or choice order")
    return choice_order[CHOICES.index(selected)]


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"ok": True})


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    with connect() as conn:
        total_questions = conn.execute("SELECT COUNT(*) FROM question").fetchone()[0]
        answered_questions = conn.execute(
            "SELECT COUNT(DISTINCT question_id) FROM attempt"
        ).fetchone()[0]
    return templates.TemplateResponse(
        request, "index.html",
        {
            "domains": DOMAINS,
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "unanswered_questions": total_questions - answered_questions,
        },
    )


@app.get("/drill", response_class=HTMLResponse)
def drill(
    request: Request,
    domain: Optional[str] = None,
    only: Optional[str] = None,
    weighted: Optional[str] = None,
) -> HTMLResponse:
    if domain and domain not in DOMAINS:
        domain = None
    if only != "unanswered":
        only = None
    is_weighted = weighted in {"1", "true", "yes"}
    remaining: Optional[int] = None
    with connect() as conn:
        if is_weighted:
            # Blueprint-weighted sampler ignores the domain filter by design.
            domain = None
            row = next_weighted(conn, random.SystemRandom())
        elif only == "unanswered":
            row = next_unanswered(conn, domain)
            remaining = unanswered_count(conn, domain)
        else:
            row = conn.execute(
                """
                SELECT q.* FROM question q
                {where}
                ORDER BY (SELECT COUNT(*) FROM attempt WHERE question_id = q.id),
                         RANDOM()
                LIMIT 1
                """.format(where="WHERE q.domain = ?" if domain else ""),
                (domain,) if domain else (),
            ).fetchone()
    if not row:
        if only == "unanswered":
            message = (
                "All questions answered — none left unanswered"
                + (f" in {domain}" if domain else "")
                + ". Try Review Wrong or drill all questions."
            )
        else:
            message = "No questions found. Run `python seed.py`."
        return templates.TemplateResponse(
            request, "empty.html", {"message": message},
        )
    return templates.TemplateResponse(
        request, "question.html",
        {
            "q": _apply_choice_order(_row_to_question(row)),
            "domain": domain,
            "only": only,
            "weighted": "1" if is_weighted else "",
            "remaining": remaining,
            "mode": "drill",
        },
    )


class AnswerPayload(BaseModel):
    question_id: int = Field(..., ge=1)
    selected: str = Field(..., pattern="^[ABCD]$")
    choice_order: str = Field(default="ABCD", pattern="^[ABCD]{4}$")
    domain: Optional[str] = None
    only: Optional[str] = None
    weighted: Optional[str] = None
    mode: str = Field(default="drill")


@app.post("/answer", response_class=HTMLResponse)
def answer(
    request: Request,
    question_id: int = Form(...),
    selected: str = Form(...),
    choice_order: str = Form("ABCD"),
    domain: Optional[str] = Form(None),
    only: Optional[str] = Form(None),
    weighted: Optional[str] = Form(None),
    mode: str = Form("drill"),
) -> HTMLResponse:
    payload = AnswerPayload(
        question_id=question_id, selected=selected, choice_order=choice_order,
        domain=domain, only=only if only == "unanswered" else None,
        weighted=weighted if weighted == "1" else None, mode=mode,
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM question WHERE id = ?", (payload.question_id,)
        ).fetchone()
        if not row:
            return HTMLResponse("Question not found", status_code=404)
        try:
            original_selected = _selected_original(payload.selected, payload.choice_order)
        except ValueError:
            return HTMLResponse("Invalid choice order", status_code=400)
        is_correct = 1 if row["correct"] == original_selected else 0
        conn.execute(
            "INSERT INTO attempt (question_id, selected, correct) VALUES (?, ?, ?)",
            (payload.question_id, original_selected, is_correct),
        )
        conn.commit()
    return templates.TemplateResponse(
        request, "result.html",
        {
            "q": _apply_choice_order(_row_to_question(row), payload.choice_order),
            "selected": payload.selected,
            "is_correct": bool(is_correct),
            "domain": payload.domain,
            "only": payload.only,
            "weighted": payload.weighted or "",
            "mode": payload.mode,
        },
    )


@app.get("/review", response_class=HTMLResponse)
def review(request: Request) -> HTMLResponse:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT q.* FROM question q
            JOIN (
              SELECT question_id, MAX(attempted_at) AS last_at
              FROM attempt
              GROUP BY question_id
            ) latest ON latest.question_id = q.id
            JOIN attempt a
              ON a.question_id = q.id AND a.attempted_at = latest.last_at
            WHERE a.correct = 0
            ORDER BY RANDOM()
            LIMIT 1
            """
        ).fetchone()
    if not row:
        return templates.TemplateResponse(
            request, "empty.html",
            {"message": "No wrong answers yet. Drill some questions first."},
        )
    return templates.TemplateResponse(
        request, "question.html",
        {
            "q": _apply_choice_order(_row_to_question(row)),
            "domain": None,
            "mode": "review",
        },
    )


@app.get("/questions", response_class=HTMLResponse)
def questions(
    request: Request,
    domain: Optional[str] = None,
    status: Optional[str] = None,
) -> HTMLResponse:
    if domain and domain not in DOMAINS:
        domain = None
    if status not in {"answered", "unanswered", "wrong", None}:
        status = None

    where = "WHERE q.domain = ?" if domain else ""
    params = (domain,) if domain else ()
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT q.id, q.domain, q.scenario, q.principle, q.stem,
                   COUNT(a.id) AS attempts,
                   COALESCE(SUM(a.correct), 0) AS correct_attempts,
                   (
                     SELECT a2.correct
                     FROM attempt a2
                     WHERE a2.question_id = q.id
                     ORDER BY a2.attempted_at DESC, a2.id DESC
                     LIMIT 1
                   ) AS last_correct
            FROM question q
            LEFT JOIN attempt a ON a.question_id = q.id
            {where}
            GROUP BY q.id
            ORDER BY q.domain, q.id
            """,
            params,
        ).fetchall()

    question_rows = []
    for row in rows:
        q = dict(row)
        q["attempts"] = q["attempts"] or 0
        q["correct_attempts"] = q["correct_attempts"] or 0
        q["answered"] = q["attempts"] > 0
        q["last_correct_bool"] = None if q["last_correct"] is None else bool(q["last_correct"])
        if status == "answered" and not q["answered"]:
            continue
        if status == "unanswered" and q["answered"]:
            continue
        if status == "wrong" and q["last_correct_bool"] is not False:
            continue
        question_rows.append(q)

    return templates.TemplateResponse(
        request, "questions.html",
        {
            "questions": question_rows,
            "domains": DOMAINS,
            "domain": domain,
            "status": status,
        },
    )


@app.get("/question/{question_id}", response_class=HTMLResponse)
def question_detail(request: Request, question_id: int) -> HTMLResponse:
    with connect() as conn:
        row = conn.execute("SELECT * FROM question WHERE id = ?", (question_id,)).fetchone()
    if not row:
        return HTMLResponse("Question not found", status_code=404)
    return templates.TemplateResponse(
        request, "question.html",
        {
            "q": _apply_choice_order(_row_to_question(row)),
            "domain": None,
            "mode": "question_list",
        },
    )


@app.get("/add", response_class=HTMLResponse)
def add_get(request: Request, added: Optional[int] = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "add.html",
        {
            "domains": DOMAINS,
            "scenarios": SCENARIOS,
            "choices": CHOICES,
            "added": added,
        },
    )


@app.post("/add")
def add_post(
    domain: str = Form(...),
    scenario: str = Form(...),
    principle: str = Form(""),
    stem: str = Form(...),
    choice_a: str = Form(...),
    choice_b: str = Form(...),
    choice_c: str = Form(...),
    choice_d: str = Form(...),
    correct: str = Form(...),
    rationale_a: str = Form(...),
    rationale_b: str = Form(...),
    rationale_c: str = Form(...),
    rationale_d: str = Form(...),
    anti_pattern: str = Form(""),
    source: str = Form("manual"),
) -> RedirectResponse:
    if domain not in DOMAINS:
        return RedirectResponse(url="/add?added=0", status_code=303)
    if scenario not in SCENARIOS:
        return RedirectResponse(url="/add?added=0", status_code=303)
    if correct not in CHOICES:
        return RedirectResponse(url="/add?added=0", status_code=303)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO question (
              domain, scenario, principle, stem,
              choice_a, choice_b, choice_c, choice_d, correct,
              rationale_a, rationale_b, rationale_c, rationale_d,
              anti_pattern, source
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                domain, scenario, principle or None, stem,
                choice_a, choice_b, choice_c, choice_d, correct,
                rationale_a, rationale_b, rationale_c, rationale_d,
                anti_pattern or None, source or None,
            ),
        )
        conn.commit()
    return RedirectResponse(url="/add?added=1", status_code=303)


# DOMAIN_WEIGHT is the single source of truth in selection.py (imported above)
# so the weighted sampler and this stats display can never drift apart.
PASS_THRESHOLD = 72  # %
DOMAIN_LABEL = {
    "agentic": "Agentic Architecture & Orchestration",
    "tool_mcp": "Tool Design & MCP Integration",
    "claude_code": "Claude Code Configuration & Workflows",
    "prompt_eng": "Prompt Engineering & Structured Output",
    "context": "Context Management & Reliability",
    "cli_reference": "Claude Code CLI Reference (v2.1.153)",
}


def _pct(correct: int, attempts: int) -> float:
    return (correct / attempts * 100) if attempts else 0.0


def _bucket(pct: float, attempts: int) -> str:
    if attempts == 0:
        return "none"
    if pct >= 80:
        return "ok"
    if pct >= 60:
        return "warn"
    return "bad"


@app.get("/stats", response_class=HTMLResponse)
def stats(request: Request) -> HTMLResponse:
    with connect() as conn:
        domain_rows = conn.execute(
            """
            SELECT q.domain,
                   COUNT(a.id)                AS attempts,
                   COALESCE(SUM(a.correct),0) AS correct,
                   (SELECT COUNT(*) FROM question WHERE domain = q.domain) AS bank_size
            FROM question q
            LEFT JOIN attempt a ON a.question_id = q.id
            GROUP BY q.domain
            ORDER BY q.domain
            """
        ).fetchall()
        principle_rows = conn.execute(
            """
            SELECT q.principle,
                   q.domain,
                   COUNT(a.id) AS attempts,
                   COALESCE(SUM(a.correct),0) AS correct
            FROM question q
            JOIN attempt a ON a.question_id = q.id
            WHERE q.principle IS NOT NULL AND q.principle != ''
            GROUP BY q.principle, q.domain
            HAVING attempts > 0
            ORDER BY (1.0 * COALESCE(SUM(a.correct),0) / COUNT(a.id)) ASC,
                     attempts DESC
            LIMIT 10
            """
        ).fetchall()
        recent_rows = conn.execute(
            """
            SELECT a.correct, q.domain, q.id AS question_id
            FROM attempt a
            JOIN question q ON q.id = a.question_id
            ORDER BY a.attempted_at DESC
            LIMIT 20
            """
        ).fetchall()
        overall = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(correct),0) AS c FROM attempt"
        ).fetchone()
        total_questions = conn.execute(
            "SELECT COUNT(*) FROM question"
        ).fetchone()[0]
        sources = conn.execute(
            "SELECT source, COUNT(*) FROM question GROUP BY source ORDER BY source"
        ).fetchall()
        anti_patterns = anti_pattern_stats(conn)

    domains = []
    for r in domain_rows:
        attempts = r["attempts"] or 0
        correct = r["correct"] or 0
        pct = _pct(correct, attempts)
        domains.append({
            "key": r["domain"],
            "label": DOMAIN_LABEL.get(r["domain"], r["domain"]),
            "attempts": attempts,
            "correct": correct,
            "pct": pct,
            "pct_str": f"{pct:.0f}%",
            "bucket": _bucket(pct, attempts),
            "bank_size": r["bank_size"],
            "target_weight": DOMAIN_WEIGHT.get(r["domain"], 0),
        })

    principles = []
    for r in principle_rows:
        attempts = r["attempts"]
        correct = r["correct"]
        pct = _pct(correct, attempts)
        principles.append({
            "principle": r["principle"],
            "domain": r["domain"],
            "attempts": attempts,
            "correct": correct,
            "pct": pct,
            "pct_str": f"{pct:.0f}%",
            "bucket": _bucket(pct, attempts),
        })

    recent = list(reversed([
        {"correct": bool(r["correct"]), "domain": r["domain"], "question_id": r["question_id"]}
        for r in recent_rows
    ]))

    weakest = sorted(
        [d for d in domains if d["attempts"] > 0],
        key=lambda d: (d["pct"], -d["attempts"]),
    )[:3]

    total_attempts = overall["n"] or 0
    total_correct = overall["c"] or 0
    total_pct = _pct(total_correct, total_attempts)

    return templates.TemplateResponse(
        request, "stats.html",
        {
            "domains": domains,
            "principles": principles,
            "recent": recent,
            "weakest": weakest,
            "total_attempts": total_attempts,
            "total_correct": total_correct,
            "total_pct": total_pct,
            "total_pct_str": f"{total_pct:.0f}%",
            "pass_threshold": PASS_THRESHOLD,
            "passing": total_pct >= PASS_THRESHOLD and total_attempts > 0,
            "total_questions": total_questions,
            "sources": [{"name": s[0] or "unknown", "count": s[1]} for s in sources],
            "anti_patterns": anti_patterns,
        },
    )
