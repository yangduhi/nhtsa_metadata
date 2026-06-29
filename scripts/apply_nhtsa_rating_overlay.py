#!/usr/bin/env python
"""Import NHTSA SafetyRatings candidate CSV artifacts into the SQLite overlay table."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine

from nhtsa_metadata.services.safety_ratings_overlay import (
    ensure_safety_rating_overlay_schema,
    safety_rating_overlay_summary,
    upsert_safety_rating_overlay_rows,
)

DEFAULT_DB = Path("D:/vscode/nhtsa_metadata/data/nhtsa_test_metadata_2011.sqlite")
DEFAULT_CANDIDATE_CSV = Path(
    "D:/vscode/nhtsa_metadata/artifacts/nhtsa_rating_match_v8_deep/candidate_rows.csv"
)


def read_candidate_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def import_overlay(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.db)
    candidate_csv = Path(args.candidate_csv)
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    if not candidate_csv.exists():
        raise FileNotFoundError(candidate_csv)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    rows = read_candidate_rows(candidate_csv)
    ensure_safety_rating_overlay_schema(engine)
    upsert_safety_rating_overlay_rows(
        engine,
        rows,
        generated_at=args.generated_at,
        replace_existing=args.replace,
    )
    summary = safety_rating_overlay_summary(engine)
    return {
        "database_path": str(db_path),
        "candidate_csv": str(candidate_csv),
        "input_rows": len(rows),
        "replace_existing": args.replace,
        "overlay_summary": summary,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite DB path to mutate")
    parser.add_argument(
        "--candidate-csv",
        default=str(DEFAULT_CANDIDATE_CSV),
        help="candidate_rows.csv produced by build_nhtsa_rating_match_candidates.py",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing overlay candidate rows before importing",
    )
    parser.add_argument("--generated-at", default=None, help="Override generated_at for all rows")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    result = import_overlay(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
