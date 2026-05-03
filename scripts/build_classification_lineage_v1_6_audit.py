from __future__ import annotations

import argparse
from pathlib import Path

from nhtsa_metadata.services.classification_accounting import read_classification_fixture
from nhtsa_metadata.services.classification_lineage import (
    build_lineage_audit_rows,
    write_lineage_audit,
)

FIXTURE_DIR = Path("tests/fixtures/classification")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    args = parser.parse_args()

    evidence_rows = read_classification_fixture(
        args.fixture_dir / "classification_evidence_v1_4_2.csv"
    )
    lineage_rows = build_lineage_audit_rows(evidence_rows)
    write_lineage_audit(args.fixture_dir / "classification_lineage_audit_v1_6.csv", lineage_rows)


if __name__ == "__main__":
    main()
