"""Weighted sampler: domain-selection distribution within tolerance."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from random import Random

from conftest import insert_question

import selection


def test_pick_weighted_domain_matches_blueprint() -> None:
    """Empirical domain frequencies track the D1-D5 weights within tolerance."""
    rng = Random(12345)
    available = list(selection.DOMAIN_WEIGHT)  # includes zero-weight off_blueprint
    n = 40_000
    counts: dict[str, int] = {}
    for _ in range(n):
        d = selection.pick_weighted_domain(available, rng)
        counts[d] = counts.get(d, 0) + 1

    # off_blueprint has weight 0 -> never selected.
    assert "off_blueprint" not in counts

    total_weight = sum(w for w in selection.DOMAIN_WEIGHT.values() if w > 0)
    tol = 0.02  # absolute proportion tolerance
    for domain, weight in selection.DOMAIN_WEIGHT.items():
        if weight == 0:
            continue
        expected = weight / total_weight
        observed = counts.get(domain, 0) / n
        assert abs(observed - expected) < tol, (
            f"{domain}: observed {observed:.3f} vs expected {expected:.3f}"
        )


def test_pick_weighted_domain_skips_unavailable_domains() -> None:
    rng = Random(1)
    # Only two domains present; the sampler must never return a missing one.
    available = ["agentic", "context"]
    seen = {selection.pick_weighted_domain(available, rng) for _ in range(500)}
    assert seen <= {"agentic", "context"}


def test_pick_weighted_domain_none_when_no_weighted_domain() -> None:
    rng = Random(1)
    # off_blueprint has weight 0; no positively-weighted domain available.
    assert selection.pick_weighted_domain(["off_blueprint"], rng) is None
    assert selection.pick_weighted_domain([], rng) is None


def test_next_weighted_returns_only_weighted_domain_rows(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    insert_question(conn, "a1", domain="agentic")
    insert_question(conn, "x1", domain="off_blueprint")
    conn.commit()

    rng = Random(7)
    domains = {selection.next_weighted(conn, rng)["domain"] for _ in range(100)}
    # off_blueprint is zero-weight, so weighted draws stay on agentic.
    assert domains == {"agentic"}


def test_next_weighted_falls_back_when_only_zero_weight(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    insert_question(conn, "x1", domain="off_blueprint")
    conn.commit()

    # No positively-weighted domain has questions -> global random fallback,
    # which still returns the only row rather than None.
    assert selection.next_weighted(conn, Random(1))["stem"] == "x1"
