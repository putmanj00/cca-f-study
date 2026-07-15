"""Question-selection helpers: unanswered set, resume cursor, weighted sampler.

Pure functions over a ``sqlite3.Connection`` so they can be unit-tested against a
temporary database without spinning up the FastAPI app. ``app.py`` wires these
into the ``/drill`` route.

Resume model (no separate store): the "unanswered set" is every question with no
recorded ``attempt`` row, served in a fixed ``(domain, id)`` order. The next
unanswered question is therefore always the lowest ``(domain, id)`` with no
attempt — a cursor *derived* from the attempt table, so it survives a process
restart for free and "continues where you left off".
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from random import Random
from typing import Optional

# Domain weights for the blueprint-aligned weighted sampler, matching the
# published CCA-F Exam Guide v0.2 (2026-06-30; see
# docs/exam-guide-v0.2-alignment.md). ``off_blueprint`` holds questions on
# topics the guide lists as out of scope (caching internals, streaming,
# pricing, token counting, ...) — still drillable by domain filter but
# excluded from weighted sampling.
DOMAIN_WEIGHT: dict[str, int] = {
    "agentic": 27,      # D1 Agentic Architecture & Orchestration
    "tool_mcp": 18,     # D2 Tool Design & MCP Integration
    "claude_code": 20,  # D3 Claude Code Configuration & Workflows
    "prompt_eng": 20,   # D4 Prompt Engineering & Structured Output
    "context": 15,      # D5 Context Management & Reliability
    "off_blueprint": 0,
}


# Canonical anti-pattern catalog from the exam blueprint. The slug is the
# structured ``anti_pattern_slug`` id; the label is the short trap description.
# Free-text ``anti_pattern`` prose stays as-is; the slug is the aggregatable tag.
ANTI_PATTERN_LABEL: dict[str, str] = {
    "loop-termination-nl": "Parse natural language for loop termination",
    "iteration-cap": "Arbitrary iteration cap as primary stop",
    "prompt-vs-hook": "Prompt-based enforcement of a critical rule",
    "confidence-escalation": "Self-reported confidence score for escalation",
    "sentiment-escalation": "Sentiment-based escalation",
    "generic-error": 'Generic error ("Operation failed")',
    "empty-as-success": "Empty results treated as success",
    "too-many-tools": "18+ tools per agent",
    "same-session-review": "Same-session self-review",
    "aggregate-metrics": "Aggregate accuracy only",
}


def anti_pattern_stats(conn: sqlite3.Connection) -> list[dict]:
    """Per-anti-pattern accuracy (slug-tagged questions only), worst-first.

    Only questions carrying a structured ``anti_pattern_slug`` and at least one
    attempt appear; free-text-only questions are excluded (they are surfaced for
    manual tagging by the migration's review report instead).
    """
    rows = conn.execute(
        """
        SELECT q.anti_pattern_slug AS slug,
               COUNT(a.id)                AS attempts,
               COALESCE(SUM(a.correct),0) AS correct
        FROM question q
        JOIN attempt a ON a.question_id = q.id
        WHERE q.anti_pattern_slug IS NOT NULL AND q.anti_pattern_slug != ''
        GROUP BY q.anti_pattern_slug
        HAVING attempts > 0
        ORDER BY (1.0 * COALESCE(SUM(a.correct),0) / COUNT(a.id)) ASC,
                 attempts DESC
        """
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        attempts = int(r["attempts"])
        correct = int(r["correct"])
        pct = (correct / attempts * 100) if attempts else 0.0
        bucket = "ok" if pct >= 80 else "warn" if pct >= 60 else "bad"
        out.append({
            "slug": r["slug"],
            "label": ANTI_PATTERN_LABEL.get(r["slug"], r["slug"]),
            "attempts": attempts,
            "correct": correct,
            "pct": pct,
            "pct_str": f"{pct:.0f}%",
            "bucket": bucket,
        })
    return out


def _domain_clause(
    domain: Optional[str], params: list, exclude_domain: Optional[str] = None
) -> str:
    clause = ""
    if domain:
        params.append(domain)
        clause += " AND q.domain = ?"
    if exclude_domain and exclude_domain != domain:
        params.append(exclude_domain)
        clause += " AND q.domain != ?"
    return clause


def unanswered_count(
    conn: sqlite3.Connection,
    domain: Optional[str] = None,
    exclude_domain: Optional[str] = None,
) -> int:
    """Count questions with no recorded attempt, optionally within one domain."""
    params: list = []
    sql = (
        "SELECT COUNT(*) FROM question q "
        "WHERE NOT EXISTS (SELECT 1 FROM attempt a WHERE a.question_id = q.id)"
        + _domain_clause(domain, params, exclude_domain)
    )
    return int(conn.execute(sql, params).fetchone()[0])


def next_unanswered(
    conn: sqlite3.Connection,
    domain: Optional[str] = None,
    exclude_domain: Optional[str] = None,
) -> Optional[sqlite3.Row]:
    """Return the next unanswered question in fixed ``(domain, id)`` order.

    This is the resume cursor: calling it again without answering returns the
    same row (stable head); answering it removes the row from the set so the
    following call returns the next question. Returns ``None`` when the set is
    empty.
    """
    params: list = []
    sql = (
        "SELECT q.* FROM question q "
        "WHERE NOT EXISTS (SELECT 1 FROM attempt a WHERE a.question_id = q.id)"
        + _domain_clause(domain, params, exclude_domain)
        + " ORDER BY q.domain, q.id LIMIT 1"
    )
    return conn.execute(sql, params).fetchone()


def pick_weighted_domain(
    available: Sequence[str],
    rng: Random,
    weights: Mapping[str, int] = DOMAIN_WEIGHT,
) -> Optional[str]:
    """Pick a domain weighted by exam blueprint.

    Restricted to ``available`` domains with a positive weight, so a domain with
    no questions (or the zero-weight ``off_blueprint`` study domain) is never
    chosen. Returns ``None`` if no domain qualifies.
    """
    pool = [(d, weights.get(d, 0)) for d in available if weights.get(d, 0) > 0]
    if not pool:
        return None
    domains, w = zip(*pool)
    return rng.choices(domains, weights=w, k=1)[0]


def exam_allocation(
    available: Mapping[str, int],
    total: int = 60,
    weights: Mapping[str, int] = DOMAIN_WEIGHT,
) -> dict[str, int]:
    """Allocate ``total`` exam slots across positively-weighted domains.

    Largest-remainder allocation over the blueprint weights, capped by each
    domain's available bank size. Zero-weight domains (``off_blueprint``) never
    receive a slot. May return fewer than ``total`` slots when the bank is too
    small to fill the allocation.
    """
    pool = {
        d: w for d, w in weights.items() if w > 0 and available.get(d, 0) > 0
    }
    if not pool:
        return {}
    weight_sum = sum(pool.values())
    exact = {d: total * w / weight_sum for d, w in pool.items()}
    alloc = {d: min(int(exact[d]), available[d]) for d in pool}
    capacity = sum(min(available[d], total) for d in pool)
    while sum(alloc.values()) < min(total, capacity):
        candidates = [d for d in pool if alloc[d] < available[d]]
        if not candidates:
            break
        best = max(candidates, key=lambda d: (exact[d] - alloc[d], weights[d]))
        alloc[best] += 1
    return alloc


def sample_exam_questions(
    conn: sqlite3.Connection, rng: Random, total: int = 60
) -> list[int]:
    """Sample question ids for a simulated exam: blueprint-weighted by domain,
    without replacement, off_blueprint excluded, shuffled into exam order.
    """
    available = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT domain, COUNT(*) FROM question GROUP BY domain"
        ).fetchall()
    }
    ids: list[int] = []
    for domain, n in exam_allocation(available, total).items():
        domain_ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM question WHERE domain = ?", (domain,)
            ).fetchall()
        ]
        ids.extend(rng.sample(domain_ids, n))
    rng.shuffle(ids)
    return ids


def next_weighted(conn: sqlite3.Connection, rng: Random) -> Optional[sqlite3.Row]:
    """Pick a domain by blueprint weight (among domains that have questions),
    then a random question within it.

    Falls back to a global random question if no positively-weighted domain has
    questions. Returns ``None`` only when the bank is empty.
    """
    available = [
        r[0] for r in conn.execute("SELECT DISTINCT domain FROM question").fetchall()
    ]
    domain = pick_weighted_domain(available, rng)
    if domain is None:
        return conn.execute(
            "SELECT * FROM question ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
    return conn.execute(
        "SELECT * FROM question WHERE domain = ? ORDER BY RANDOM() LIMIT 1",
        (domain,),
    ).fetchone()
