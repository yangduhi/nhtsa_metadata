from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "docs" / "phase_reports"
MANIFEST_PATH = REPORT_DIR / "phase_report_manifest.csv"
INDEX_PATH = (
    REPORT_DIR
    / "2026-05-03__documentation-management__current__phase-report-index.md"
)
SKIPPED = {
    "2026-05-03__documentation-management__current__phase-report-index.md",
    "2026-05-03__documentation-management__current__phase-report-management.md",
}


def test_phase_report_manifest_covers_reports() -> None:
    rows = list(csv.DictReader(MANIFEST_PATH.open(encoding="utf-8", newline="")))
    assert rows

    registered = {row["path"] for row in rows}
    expected = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in REPORT_DIR.glob("*.md")
        if path.name not in SKIPPED
    }
    assert registered == expected


def test_phase_report_manifest_is_sorted_and_informative() -> None:
    rows = list(csv.DictReader(MANIFEST_PATH.open(encoding="utf-8", newline="")))
    assert len(rows) == 49
    sort_keys = [row["sort_key"] for row in rows]
    assert sort_keys == sorted(sort_keys)
    for row in rows:
        assert row["date"]
        assert row["stage"]
        assert row["status"]
        assert row["title"]
        assert row["summary"]
        assert (REPO_ROOT / row["path"]).exists()


def test_phase_report_manifest_preserves_legacy_status_decisions() -> None:
    rows = {
        Path(row["path"]).name: row
        for row in csv.DictReader(MANIFEST_PATH.open(encoding="utf-8", newline=""))
    }

    assert rows["2026-04-28__bootstrap-phase-5__pass__phase-5-report.md"]["status"] == "pass"
    assert (
        rows[
            "2026-04-30__discovery-authority__blocked__"
            "discovery-authority-problem-statement-2011-plus.md"
        ]["status"]
        == "blocked"
    )
    assert (
        rows[
            "2026-04-30__full-scale-planning__superseded__"
            "full-scale-schema-capacity-estimate.md"
        ]["status"]
        == "superseded"
    )
    assert (
        rows[
            "2026-04-30__schema-v1-x__accepted__"
            "schema-v1-0-finalization-decision.md"
        ]["status"]
        == "accepted"
    )


def test_phase_report_index_is_the_docs_entrypoint() -> None:
    index = INDEX_PATH.read_text(encoding="utf-8")
    assert "# 2026-05-03 | Documentation Management | CURRENT | Phase Report Index" in index
    assert "## Reading Order" in index
    assert "## Daily Timeline" in index
    assert "2026-04-30__schema-v1-x__accepted__schema-v1-0-finalization-decision.md" in index
    assert (
        "2026-04-30__full-scale-planning__accepted__"
        "full-scale-2011plus-crawler-approval-package.md"
    ) in index


def test_docs_markdown_h1_titles_are_standardized() -> None:
    for path in (REPO_ROOT / "docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        first_h1 = next(line for line in text.splitlines() if line.startswith("# "))
        assert " | " in first_h1, path
        assert first_h1.startswith("# 20"), path
