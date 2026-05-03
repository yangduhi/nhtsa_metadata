from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "docs" / "phase_reports"
INDEX_PATH = (
    REPORT_DIR
    / "2026-05-03__documentation-management__current__phase-report-index.md"
)
MANIFEST_PATH = REPORT_DIR / "phase_report_manifest.csv"

PHASE_REPORT_MANAGEMENT_NAME = (
    "2026-05-03__documentation-management__current__phase-report-management.md"
)
SKIP_NAMES = {
    ".gitkeep",
    "INDEX.md",
    "README.md",
    INDEX_PATH.name,
    PHASE_REPORT_MANAGEMENT_NAME,
    "phase_report_manifest.csv",
}
SECTION_HEADERS = ("Conclusion", "Decision", "Status", "Summary", "Result", "Scope")
STANDARD_NAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})__"
    r"(?P<stage>[a-z0-9-]+)__"
    r"(?P<status>[a-z0-9-]+)__"
    r"(?P<topic>[a-z0-9-]+)\.md$"
)
STANDARD_H1_RE = re.compile(
    r"^# (?P<date>\d{4}-\d{2}-\d{2}) \| "
    r"(?P<stage>.+?) \| "
    r"(?P<status>.+?) \| "
    r"(?P<title>.+)$"
)
STANDARD_TOPIC_ORDER = {
    "phase-0-report": 0,
    "phase-1-report": 1,
    "phase-2-report": 2,
    "phase-3-report": 3,
    "phase-4-report": 4,
    "phase-5-report": 5,
    "phase-6-report": 6,
    "phase-7-report": 7,
    "phase-8-report": 8,
    "project-ops-hardening-report": 20,
    "2011-plus-scope-gate-report": 30,
    "semantic-cardinality-remediation": 40,
    "live-pilot-remediation-report": 50,
    "100test-2011plus-manifest-plan": 60,
    "100test-2011plus-acceptance-matrix": 70,
    "500-test-2011-plus-actual-crash-expansion-report": 80,
    "1000-test-2011-plus-live-manifest-review": 90,
    "1000-test-2011-plus-live-pilot-report": 100,
    "1000-test-2011-plus-balanced-candidate-report": 110,
    "1000-test-2011-plus-endpoint-completeness-report": 120,
    "1000-test-2011-plus-schema-optimization-report": 130,
    "1000-test-2011-plus-schema-backlog-report": 140,
    "1000-test-2011-plus-full-scale-readiness-gate": 150,
    "schema-v1-0-index-and-read-model-plan": 200,
    "schema-v1-0-conflict-resolution-policy": 210,
    "schema-v1-0-backlog-triage": 220,
    "schema-v1-0-backlog-summary": 230,
    "schema-v1-0-finalization-decision": 240,
    "schema-v1-1-full-cover-decision": 250,
    "schema-v1-2-full-cover-gate": 260,
    "discovery-authority-problem-statement-2011-plus": 300,
    "discovery-diagnostics-2011-plus": 310,
    "full-2011-plus-manifest-dry-run-review": 320,
    "discovery-authority-decision-for-2011-plus-full-manifest": 330,
    "reference-discovery-validation-2011-plus": 340,
    "full-scale-schema-capacity-estimate": 350,
    "authoritative-full-scale-capacity-estimate-2011-plus": 360,
    "full-scale-2011plus-crawler-approval-package": 370,
    "endpoint-matrix-contract-2011-plus": 380,
    "full-coverage-gap-2011-plus": 390,
    "schema-contract-validation-2011-plus": 400,
    "manual-domain-review-backlog-2011-plus": 410,
    "edge-case-schema-validation-candidate-plan-v1-2": 420,
    "edge-case-schema-validation-candidate-plan": 430,
}
STATUS_OVERRIDES = {
    "discovery_authority_problem_statement_2011plus.md": "blocked",
    "phase_5_ingestion_rebuild.md": "pass",
    "full_scale_schema_capacity_estimate.md": "superseded",
    "schema_v1_0_conflict_resolution_policy.md": "recorded",
    "schema_v1_0_backlog_triage.md": "recorded",
    "schema_v1_0_backlog_summary.md": "accepted",
    "schema_v1_0_finalization_decision.md": "accepted",
    "manual_domain_review_backlog_2011plus.md": "recorded",
}


def main() -> None:
    reports = []
    for path in sorted(REPORT_DIR.glob("*.md")):
        if path.name in SKIP_NAMES:
            continue
        text = path.read_text(encoding="utf-8")
        standard = parse_standard_report(path, text)
        if standard:
            reports.append(standard)
            continue
        reports.append(
            {
                "sort_key": sort_key(path.name),
                "date": infer_date(path.name),
                "stage": infer_stage(path.name),
                "status": infer_status(path.name, text),
                "title": extract_title(path.name, text),
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "summary": extract_summary(text),
            }
        )

    reports.sort(key=lambda row: (row["sort_key"], row["path"]))
    write_manifest(reports)
    write_index(reports)


def sort_key(name: str) -> str:
    standard = STANDARD_NAME_RE.match(name)
    if standard:
        order = STANDARD_TOPIC_ORDER.get(standard.group("topic"), 900)
        return f"{standard.group('date')}.{order:03d}"

    order = 900
    match = re.match(r"phase_(\d+)_", name)
    if match:
        return f"2026-04-28.{int(match.group(1)):03d}"

    prefixes = [
        ("project_ops", 20),
        ("scope_gate", 30),
        ("semantic_cardinality", 40),
        ("live_pilot", 50),
        ("100test_2011plus_manifest", 60),
        ("100test_2011plus_acceptance", 70),
        ("500test", 80),
        ("1000test_2011plus_live_manifest", 90),
        ("1000test_2011plus_live_pilot", 100),
        ("1000test_2011plus_balanced", 110),
        ("1000test_2011plus_endpoint", 120),
        ("1000test_2011plus_schema_optimization", 130),
        ("1000test_2011plus_schema_backlog", 140),
        ("1000test_2011plus_full_scale", 150),
        ("schema_v1_0_index", 200),
        ("schema_v1_0_conflict", 210),
        ("schema_v1_0_backlog_triage", 220),
        ("schema_v1_0_backlog_summary", 230),
        ("schema_v1_0_finalization", 240),
        ("schema_v1_1", 250),
        ("schema_v1_2", 260),
        ("discovery_authority_problem", 300),
        ("discovery_diagnostics", 310),
        ("full_2011plus_manifest", 320),
        ("discovery_authority_decision", 330),
        ("reference_discovery_validation", 340),
        ("full_scale_schema_capacity", 350),
        ("full_scale_capacity_estimate_authoritative", 360),
        ("full_scale_2011plus_crawler_approval", 370),
        ("endpoint_matrix_contract", 380),
        ("full_coverage_gap", 390),
        ("schema_contract_validation", 400),
        ("manual_domain_review", 410),
        ("edge_case_schema_validation_candidate_plan_v1_2", 420),
        ("edge_case_schema_validation_candidate_plan", 430),
    ]
    for prefix, value in prefixes:
        if name.startswith(prefix):
            order = value
            break
    return f"{infer_date(name)}.{order:03d}"


def infer_date(name: str) -> str:
    if name.startswith("phase_"):
        return "2026-04-28"
    if name.startswith(("project_ops", "scope_gate", "semantic_cardinality", "live_pilot")):
        return "2026-04-29"
    return "2026-04-30"


def infer_stage(name: str) -> str:
    if name.startswith("phase_"):
        match = re.match(r"phase_(\d+)_", name)
        return f"Bootstrap phase {match.group(1)}" if match else "Bootstrap"
    if name.startswith("100test"):
        return "100-test pilot"
    if name.startswith("500test"):
        return "500-test expansion"
    if name.startswith("1000test"):
        return "1000-test expansion"
    if name.startswith("schema_v1_"):
        return "Schema v1.x"
    if name.startswith(("discovery", "reference_discovery")):
        return "Discovery authority"
    if name.startswith("full_scale") or name.startswith("full_2011plus"):
        return "Full-scale planning"
    if name.startswith("edge_case"):
        return "Edge-case validation"
    if name.startswith("endpoint"):
        return "Endpoint contract"
    if name.startswith("manual"):
        return "Manual review"
    if name.startswith("scope"):
        return "Scope gate"
    if name.startswith("semantic"):
        return "Semantic remediation"
    if name.startswith("live"):
        return "Live pilot"
    if name.startswith("project_ops"):
        return "Operations"
    return "Phase report"


def infer_status(name: str, text: str) -> str:
    if name in STATUS_OVERRIDES:
        return STATUS_OVERRIDES[name]

    metadata_status = extract_metadata_value(text, "status")
    if metadata_status:
        return metadata_status

    lower = text.lower()
    if "accepted_with_documented_exceptions" in text:
        return "accepted_with_documented_exceptions"
    if "stage d full-scale collect: blocked" in lower:
        return "blocked"
    if "full-scale collect: blocked" in lower:
        return "blocked"
    if "full_scale_blocked: true" in lower or "full_scale_blocked=true" in lower:
        return "blocked"
    if "accepted" in lower:
        return "accepted"
    if "pass" in lower:
        return "pass"
    if "requires separate approval" in lower or "not approved" in lower:
        return "approval_required"
    return "recorded"


def extract_title(name: str, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            standard = STANDARD_H1_RE.match(line)
            if standard:
                return standard.group("title").strip()
            return line[2:].strip()
    return name.removesuffix(".md").replace("_", " ")


def parse_standard_report(path: Path, text: str) -> dict[str, str] | None:
    name_match = STANDARD_NAME_RE.match(path.name)
    if not name_match:
        return None

    h1 = extract_standard_h1(text)
    stage = h1["stage"] if h1 else unslug(name_match.group("stage"))
    status = name_match.group("status").replace("-", "_")
    title = h1["title"] if h1 else unslug(name_match.group("topic"))
    return {
        "sort_key": sort_key(path.name),
        "date": name_match.group("date"),
        "stage": stage,
        "status": status,
        "title": title,
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "summary": extract_summary(text),
    }


def extract_standard_h1(text: str) -> dict[str, str] | None:
    for line in text.splitlines():
        match = STANDARD_H1_RE.match(line)
        if match:
            return {
                "date": match.group("date"),
                "stage": match.group("stage").strip(),
                "status": match.group("status").strip().lower(),
                "title": match.group("title").strip(),
            }
    return None


def unslug(value: str) -> str:
    return value.replace("-", " ").title()


def extract_metadata_value(text: str, key: str) -> str | None:
    in_metadata = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower() == "## report metadata":
            in_metadata = True
            continue
        if in_metadata and stripped.startswith("## "):
            break
        if in_metadata and stripped.lower().startswith(f"- {key}:"):
            return stripped.split(":", 1)[1].strip() or None
    return None


def extract_summary(text: str) -> str:
    lines = text.splitlines()
    for header in SECTION_HEADERS:
        summary = bullets_after_header(lines, header)
        if summary:
            return summary
    bullets = [line.strip("- ").strip() for line in lines if line.startswith("- ")]
    if bullets:
        return " / ".join(bullets[:3])
    return "No summary bullets recorded; open the report for detail."


def bullets_after_header(lines: list[str], header: str) -> str:
    pattern = f"## {header}".lower()
    in_section = False
    bullets: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower() == pattern:
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return " / ".join(bullets[:3])


def write_manifest(reports: list[dict[str, str]]) -> None:
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sort_key", "date", "stage", "status", "title", "path", "summary"],
        )
        writer.writeheader()
        writer.writerows(reports)


def write_index(reports: list[dict[str, str]]) -> None:
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for report in reports:
        by_date[report["date"]].append(report)

    lines = [
        "# 2026-05-03 | Documentation Management | CURRENT | Phase Report Index",
        "",
        "This index is generated from tracked reports in `docs/phase_reports/`.",
        "Run `python scripts/build_phase_report_index.py` after adding or renaming a report.",
        "",
        "## Reading Order",
        "",
        "| date | stage | status | report | what changed |",
        "| --- | --- | --- | --- | --- |",
    ]
    for report in reports:
        lines.append(
            "| {date} | {stage} | {status} | [{title}]({link}) | {summary} |".format(
                date=report["date"],
                stage=escape_cell(report["stage"]),
                status=escape_cell(report["status"]),
                title=escape_cell(report["title"]),
                link=Path(report["path"]).name,
                summary=escape_cell(report["summary"]),
            )
        )

    lines.extend(["", "## Daily Timeline", ""])
    for date in sorted(by_date):
        lines.extend([f"### {date}", ""])
        for report in by_date[date]:
            lines.append(
                "- [{title}]({link}) - {stage}; {status}; {summary}".format(
                    title=report["title"],
                    link=Path(report["path"]).name,
                    stage=report["stage"],
                    status=report["status"],
                    summary=report["summary"],
                )
            )
        lines.append("")

    INDEX_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


if __name__ == "__main__":
    main()
