"""Idempotently seed the question table from all seed_data*.json files."""

from __future__ import annotations

import json
from pathlib import Path

from db import connect, init_schema

BASE_DIR = Path(__file__).parent
SEED_GLOB = "seed_data*.json"

FIELDS = (
    "domain", "scenario", "principle", "stem",
    "choice_a", "choice_b", "choice_c", "choice_d",
    "correct",
    "rationale_a", "rationale_b", "rationale_c", "rationale_d",
    "anti_pattern", "anti_pattern_slug", "source",
)


def _seed_files() -> list[Path]:
    return sorted(BASE_DIR.glob(SEED_GLOB))


def seed() -> tuple[int, int, list[str]]:
    init_schema()
    inserted = 0
    skipped = 0
    files: list[str] = []
    placeholders = ", ".join("?" for _ in FIELDS)
    columns = ", ".join(FIELDS)
    with connect() as conn:
        for path in _seed_files():
            files.append(path.name)
            data = json.loads(path.read_text())
            for row in data:
                existing = conn.execute(
                    "SELECT 1 FROM question WHERE stem = ?", (row["stem"],)
                ).fetchone()
                if existing:
                    skipped += 1
                    continue
                values = tuple(row.get(f) for f in FIELDS)
                conn.execute(
                    f"INSERT INTO question ({columns}) VALUES ({placeholders})",
                    values,
                )
                inserted += 1
        conn.commit()
    return inserted, skipped, files


if __name__ == "__main__":
    inserted, skipped, files = seed()
    print(f"Loaded files: {files}")
    print(f"Inserted: {inserted}, skipped (already present): {skipped}")
