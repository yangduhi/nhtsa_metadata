from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol

from nhtsa_metadata import __version__
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult


class LiveDiscoveryClient(Protocol):
    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        ...


@dataclass(frozen=True)
class ReferenceDiscoverySeed:
    test_no: int
    test_date: date
    test_date_raw: str
    test_configuration: str | None
    test_configuration_key: str | None
    test_type: str | None
    model_year: int | None
    vehicle_make: str | None
    vehicle_model: str | None


def run_discovery_diagnostics(
    *,
    client: LiveDiscoveryClient,
    reference_database: Path,
    full_manifest: Path,
    min_test_date: date,
    year_from: int,
    year_to: int,
    discovery_page_size: int = 100,
    page_size: int | None = None,
    max_pages_per_slice: int = 1000,
    output: Path | None = None,
    markdown_output: Path | None = None,
    year_slice_manifest_output: Path | None = None,
) -> dict[str, Any]:
    if page_size is not None:
        discovery_page_size = page_size
    reference_rows = load_reference_seeds(reference_database, min_test_date)
    live_manifest_rows = read_manifest_csv(full_manifest)
    full_manifest_test_numbers = {
        test_no
        for test_no in (_int(row.get("test_no")) for row in live_manifest_rows)
        if test_no is not None
    }
    year_slices = []
    union_test_numbers: set[int] = set()
    duplicate_overlap: Counter[int] = Counter()
    year_slice_manifest_rows: dict[int, dict[str, Any]] = {}
    missing_date_search_rows: dict[int, dict[str, Any]] = {}
    for year in range(year_from, year_to + 1):
        slice_result = fetch_search_slice(
            client=client,
            test_date_from=date(year, 1, 1),
            test_date_to=date(year, 12, 31),
            discovery_page_size=discovery_page_size,
            max_pages=max_pages_per_slice,
            reference_rows=reference_rows,
        )
        test_numbers = set(slice_result["test_numbers"])
        for test_no in test_numbers:
            duplicate_overlap[test_no] += 1
        union_test_numbers.update(test_numbers)
        for row in slice_result.pop("manifest_rows"):
            test_no = _int(row.get("test_no"))
            if test_no is None:
                continue
            year_slice_manifest_rows.setdefault(test_no, row)
        for row in slice_result.pop("missing_date_rows"):
            test_no = _int(row.get("test_no"))
            if test_no is not None:
                missing_date_search_rows.setdefault(test_no, row)
        year_slices.append(slice_result)
    validated_missing_date_rows = _validate_live_search_missing_date_rows(
        client=client,
        rows=missing_date_search_rows,
        min_test_date=min_test_date,
    )
    for row in validated_missing_date_rows:
        test_no = _int(row.get("test_no"))
        if test_no is not None:
            year_slice_manifest_rows.setdefault(test_no, row)
    reference_test_numbers = set(reference_rows)
    validated_missing_date_test_numbers = {
        test_no
        for test_no in (_int(row.get("test_no")) for row in validated_missing_date_rows)
        if test_no is not None
    }
    summary = {
        "full_by_search_row_count": len(full_manifest_test_numbers),
        "year_slice_union_count": len(union_test_numbers),
        "year_slice_manifest_row_count": len(year_slice_manifest_rows),
        "year_slice_missing_date_validation_count": len(validated_missing_date_rows),
        "year_slice_unresolved_missing_date_count": len(
            set(missing_date_search_rows) - validated_missing_date_test_numbers
        ),
        "reference_2011plus_seed_count": len(reference_test_numbers),
        "reference_only_count": len(reference_test_numbers - full_manifest_test_numbers),
        "live_only_count": len(full_manifest_test_numbers - reference_test_numbers),
        "year_slice_union_only_count": len(union_test_numbers - full_manifest_test_numbers),
        "full_manifest_only_vs_year_slice_count": len(
            full_manifest_test_numbers - union_test_numbers
        ),
        "year_slice_duplicate_overlap_count": sum(
            1 for count in duplicate_overlap.values() if count > 1
        ),
        "rows_2022_2025_present_in_year_slice": any(
            row["year"] in {2022, 2023, 2024, 2025} and row["row_count"] > 0
            for row in year_slices
        ),
    }
    payload = {
        "run": {
            "created_at": _now(),
            "git_commit": _git_commit(),
            "software_version": __version__,
            "full_manifest": str(full_manifest),
            "reference_database_path_hash": _path_hash(reference_database),
            "min_test_date": min_test_date.isoformat(),
            "year_from": year_from,
            "year_to": year_to,
        },
        "summary": summary,
        "year_slices": year_slices,
        "full_vs_year_slice": {
            "year_slice_union_only_samples": sorted(
                union_test_numbers - full_manifest_test_numbers
            )[:100],
            "full_manifest_only_samples": sorted(
                full_manifest_test_numbers - union_test_numbers
            )[:100],
        },
        "reference_comparison": {
            "reference_only_samples": sorted(
                reference_test_numbers - full_manifest_test_numbers
            )[:100],
            "live_only_samples": sorted(
                full_manifest_test_numbers - reference_test_numbers
            )[:100],
        },
        "diagnosis": _diagnostics_decision(summary),
    }
    if output is not None:
        write_json(output, payload)
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(diagnostics_markdown(payload), encoding="utf-8")
    if year_slice_manifest_output is not None:
        write_year_slice_manifest(
            year_slice_manifest_output,
            sorted(
                year_slice_manifest_rows.values(),
                key=lambda row: (str(row.get("test_date")), int(row["test_no"])),
            ),
        )
    return payload


def fetch_search_slice(
    *,
    client: LiveDiscoveryClient,
    test_date_from: date,
    test_date_to: date,
    discovery_page_size: int,
    max_pages: int,
    reference_rows: dict[int, ReferenceDiscoverySeed] | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    page_meta = []
    termination_reason = "max_pages"
    fetched_rows = 0
    for page_number in range(max_pages):
        result = client.fetch(
            "search",
            page_number=page_number,
            count=discovery_page_size,
            testDateFrom=test_date_from.isoformat(),
            testDateTo=test_date_to.isoformat(),
        )
        payload_rows = _payload_rows(result.payload)
        pagination = _pagination(result.payload)
        rows.extend(payload_rows)
        fetched_rows += len(payload_rows)
        page_meta.append(
            {
                "page_number": page_number,
                "http_status": result.http_status,
                "row_count": len(payload_rows),
                "pagination_total": pagination.get("total"),
                "pagination_count": pagination.get("count"),
                "pagination_next_present": bool(pagination.get("nextUrl")),
            }
        )
        if not payload_rows:
            termination_reason = "empty_page"
            break
        total = _int(pagination.get("total"))
        if total is not None and fetched_rows >= total:
            termination_reason = "pagination_total_reached"
            break
        if len(payload_rows) < discovery_page_size:
            termination_reason = "short_page"
            break
    test_numbers = sorted(
        {
            test_no
            for test_no in (_row_test_no(row) for row in rows)
            if test_no is not None
        }
    )
    manifest_rows = []
    missing_date_rows = []
    for row in rows:
        manifest_row = _manifest_row_from_search(row, reference_rows or {})
        if manifest_row is not None:
            manifest_rows.append(manifest_row)
        elif _row_test_no(row) is not None:
            missing_date_rows.append(_minimal_search_row(row))
    return {
        "year": test_date_from.year,
        "testDateFrom": test_date_from.isoformat(),
        "testDateTo": test_date_to.isoformat(),
        "row_count": len(rows),
        "unique_test_no_count": len(test_numbers),
        "test_numbers": test_numbers,
        "page_count": len(page_meta),
        "termination_reason": termination_reason,
        "page_meta": page_meta,
        "manifest_rows": manifest_rows,
        "missing_date_rows": missing_date_rows,
    }


def validate_reference_discovery(
    *,
    client: LiveDiscoveryClient,
    reference_database: Path,
    live_manifest: Path,
    min_test_date: date,
    validation_endpoints: list[str],
    limit: int | None = None,
    output: Path | None = None,
    validated_manifest_output: Path | None = None,
    markdown_output: Path | None = None,
    authoritative_manifest_output: Path | None = None,
    authoritative_meta_output: Path | None = None,
) -> dict[str, Any]:
    reference_rows = load_reference_seeds(reference_database, min_test_date)
    live_manifest_rows = read_manifest_csv(live_manifest)
    live_test_numbers = {
        test_no
        for test_no in (_int(row.get("test_no")) for row in live_manifest_rows)
        if test_no is not None
    }
    reference_only = [
        seed
        for test_no, seed in sorted(reference_rows.items())
        if test_no not in live_test_numbers
    ]
    if limit is not None:
        reference_only = reference_only[:limit]
    validation_rows = [
        _validate_reference_seed(
            client=client,
            seed=seed,
            min_test_date=min_test_date,
            validation_endpoints=validation_endpoints,
        )
        for seed in reference_only
    ]
    summary = _validation_summary(validation_rows, len(reference_rows), len(live_test_numbers))
    payload = {
        "run": {
            "created_at": _now(),
            "git_commit": _git_commit(),
            "software_version": __version__,
            "reference_database_path_hash": _path_hash(reference_database),
            "live_manifest": str(live_manifest),
            "min_test_date": min_test_date.isoformat(),
            "validation_endpoints": validation_endpoints,
            "limit": limit,
        },
        "summary": summary,
        "rows": validation_rows,
    }
    if output is not None:
        write_json(output, payload)
    if validated_manifest_output is not None:
        write_validated_supplement(validated_manifest_output, payload)
    if authoritative_manifest_output is not None and authoritative_meta_output is not None:
        build_authoritative_manifest(
            live_manifest=live_manifest,
            reference_database=reference_database,
            validation_payload=payload,
            output=authoritative_manifest_output,
            meta_output=authoritative_meta_output,
            min_test_date=min_test_date,
        )
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(validation_markdown(payload), encoding="utf-8")
    return payload


def build_authoritative_manifest(
    *,
    live_manifest: Path,
    reference_database: Path,
    validation_payload: dict[str, Any],
    output: Path,
    meta_output: Path,
    min_test_date: date,
) -> dict[str, Any]:
    reference_rows = load_reference_seeds(reference_database, min_test_date)
    live_rows = read_manifest_csv(live_manifest)
    authoritative_rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in live_rows:
        test_no = _int(row.get("test_no"))
        parsed_date = _date(row.get("test_date"))
        if test_no is None or parsed_date is None or parsed_date < min_test_date:
            continue
        manifest_row = _authoritative_row_from_live(row, test_no, parsed_date, reference_rows)
        authoritative_rows.append(manifest_row)
        seen.add(test_no)
    for row in validation_payload.get("rows", []):
        test_no = _int(row.get("test_no"))
        if test_no is None or test_no in seen:
            continue
        if row.get("validation_status") not in {
            "validated_live",
            "validated_live_with_metadata_drift",
        }:
            continue
        parsed_date = _date(row.get("test_date"))
        if parsed_date is None or parsed_date < min_test_date:
            continue
        manifest_row = _authoritative_row_from_validation(row, test_no, parsed_date)
        authoritative_rows.append(manifest_row)
        seen.add(test_no)
    authoritative_rows.sort(key=lambda item: (item["test_date"], int(item["test_no"])))
    _assign_row_hashes(authoritative_rows)
    write_authoritative_manifest(output, authoritative_rows)
    meta = _authoritative_manifest_meta(
        authoritative_rows=authoritative_rows,
        live_manifest=live_manifest,
        reference_database=reference_database,
        validation_payload=validation_payload,
        output=output,
        min_test_date=min_test_date,
    )
    write_json(meta_output, meta)
    return meta


def write_validated_supplement(path: Path, validation_payload: dict[str, Any]) -> None:
    fieldnames = [
        "test_no",
        "test_date",
        "test_date_raw",
        "test_date_parse_status",
        "scope_status",
        "test_configuration",
        "test_configuration_key",
        "test_type",
        "model_year",
        "vehicle_make",
        "vehicle_model",
        "live_validation_status",
        "validation_endpoint",
        "reference_test_date",
        "metadata_drift_fields",
    ]
    rows = [
        row
        for row in validation_payload.get("rows", [])
        if row.get("validation_status")
        in {"validated_live", "validated_live_with_metadata_drift"}
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            output_row = dict(row)
            output_row["live_validation_status"] = output_row.get("validation_status")
            output_row["metadata_drift_fields"] = ",".join(
                output_row.get("metadata_drift_fields") or []
            )
            writer.writerow(output_row)


def write_authoritative_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "test_no",
        "test_date",
        "test_date_raw",
        "test_date_parse_status",
        "scope_status",
        "test_configuration",
        "test_configuration_key",
        "test_type",
        "model_year",
        "vehicle_make",
        "vehicle_model",
        "discovery_authority",
        "seed_source",
        "live_by_search_present",
        "reference_present",
        "live_validation_status",
        "validation_endpoint",
        "authority_status",
        "selection_status",
        "rejection_reason",
        "manifest_reason",
        "row_hash",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_year_slice_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "test_no",
        "test_date",
        "test_year",
        "test_configuration_key",
        "test_configuration",
        "test_type",
        "model_year",
        "vehicle_make",
        "vehicle_model",
        "reason",
        "scope_status",
        "selection_priority",
        "balance_status",
        "discovery_authority",
        "seed_source",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for index, row in enumerate(rows, start=1):
            output_row = dict(row)
            output_row["selection_priority"] = index
            writer.writerow(output_row)


def write_edge_case_candidate_v1_2(
    *,
    authoritative_manifest: Path,
    database_url: str,
    output: Path,
    limit: int = 100,
) -> list[dict[str, Any]]:
    db_test_numbers = _db_test_numbers(database_url)
    rows = read_manifest_csv(authoritative_manifest)
    candidates = [row for row in rows if _int(row.get("test_no")) not in db_test_numbers]
    candidates.sort(key=_edge_case_sort_key)
    selected = candidates[:limit]
    fieldnames = list(rows[0].keys()) if rows else []
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in selected:
            writer.writerow(row)
    return selected


def diagnostics_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Discovery Diagnostics 2011+",
        "",
        "## Scope",
        "- Live by-search diagnostics only.",
        "- No detail endpoint matrix collect, no file download, no package parsing.",
        "",
        "## Summary",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Year Slices"])
    for row in payload["year_slices"]:
        lines.append(
            f"- {row['year']}: rows={row['row_count']} unique={row['unique_test_no_count']} "
            f"pages={row['page_count']} termination={row['termination_reason']}"
        )
    lines.extend(
        [
            "",
            "## Diagnosis",
            f"- {payload['diagnosis']}",
        ]
    )
    return "\n".join(lines) + "\n"


def validation_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Reference Discovery Validation 2011+",
        "",
        "## Scope",
        "- Reference DB is used only as a discovery seed.",
        "- Validation uses official live core endpoints only.",
        "- No detail endpoint matrix collect and no file download.",
        "",
        "## Summary",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Status Distribution"])
    for key, value in sorted(summary["validation_status_distribution"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Endpoint Distribution"])
    for key, value in sorted(summary["validation_endpoint_distribution"].items()):
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def decision_markdown(
    *,
    diagnostics_payload: dict[str, Any],
    validation_payload: dict[str, Any],
    authoritative_meta: dict[str, Any],
) -> str:
    selected_authority = authoritative_meta["decision"]["selected_authority"]
    stage_d = authoritative_meta["decision"]["stage_d_readiness"]
    lines = [
        "# Discovery Authority Decision for 2011+ Full Manifest",
        "",
        "## Conclusion",
        f"- selected authority: {selected_authority}",
        f"- Stage D readiness: {stage_d}",
        "",
        "## Evidence",
        f"- live by-search full count: "
        f"{diagnostics_payload['summary']['full_by_search_row_count']}",
        f"- year-slice by-search union count: "
        f"{diagnostics_payload['summary']['year_slice_union_count']}",
        f"- reference 2011+ seed count: {validation_payload['summary']['reference_seed_count']}",
        f"- reference-only count: {validation_payload['summary']['reference_only_count']}",
        f"- validated supplement count: "
        f"{validation_payload['summary']['validated_supplement_count']}",
        f"- excluded supplement count: "
        f"{validation_payload['summary']['excluded_supplement_count']}",
        f"- final authoritative manifest count: {authoritative_meta['summary']['row_count']}",
        f"- final date range: {authoritative_meta['summary']['date_range']}",
        f"- duplicate test_no count: {authoritative_meta['hard_gates']['duplicate_test_no']}",
        f"- pre-2011 rows: {authoritative_meta['hard_gates']['pre_2011_rows']}",
        f"- missing/parse-failed rows: "
        f"{authoritative_meta['hard_gates']['missing_or_parse_failed_date']}",
        "",
        "## 2022-2025 Gap",
        f"- 2022-2025 rows present in year-slice by-search: "
        f"{diagnostics_payload['summary']['rows_2022_2025_present_in_year_slice']}",
        "- reference-only rows were validated against official live core endpoints.",
        "- Live values take precedence where official validation provides values.",
        "",
        "## Authority Rules",
        "- Reference DB is seed only, not canonical source.",
        "- Only validated live or validated live with metadata drift rows are included.",
        "- Date conflict, out-of-scope, missing date, and manual-review rows are excluded.",
        "- Manual review rows require separate owner approval before Stage D inclusion.",
        "",
        "## Stage D Implication",
        f"- full-scale collect may use authoritative manifest: "
        f"{stage_d == 'approval-ready'}",
        "- owner approval is still required.",
        "- file download/media fetch/package parsing remain prohibited.",
    ]
    return "\n".join(lines) + "\n"


def schema_v1_2_gate_markdown(
    *,
    authoritative_meta: dict[str, Any],
    schema_contract: dict[str, Any] | None,
    endpoint_contract: dict[str, Any] | None,
) -> str:
    schema_failures = _summary_value(schema_contract, "hard_failure_count")
    endpoint_failures = _summary_value(endpoint_contract, "hard_failure_count")
    authoritative_pass = authoritative_meta["hard_gates"]["passed"]
    gate = (
        "pass"
        if authoritative_pass and schema_failures == 0 and endpoint_failures == 0
        else "conditional"
    )
    lines = [
        "# Schema v1.2 Full-Cover Gate",
        "",
        "## Retained Decisions",
        "- Schema v1.0 raw/provenance/canonical/read-model decisions are retained.",
        "- Schema v1.1 schema and endpoint contract validation are retained.",
        "- Scope remains `test_date >= 2011-01-01`; modelYear/test_no are not scope boundaries.",
        "",
        "## Discovery Authority",
        f"- selected authority: {authoritative_meta['decision']['selected_authority']}",
        f"- authoritative manifest: {authoritative_meta['run']['authoritative_manifest']}",
        f"- manifest hash: {authoritative_meta['summary']['manifest_hash']}",
        "",
        "## Gate Criteria",
        f"- authoritative manifest hard gates pass: {authoritative_pass}",
        f"- schema contract hard failures: {schema_failures}",
        f"- endpoint matrix hard failures: {endpoint_failures}",
        "- source_payload immutability verified by schema contract.",
        "- canonical lineage policy verified by schema contract.",
        "- prohibited whole-column JSON indexes absent by schema contract.",
        "- no file download boundary preserved.",
        "",
        "## Decision",
        f"- schema v1.2 full-cover readiness: {gate}",
        f"- Stage D full-scale collect readiness: "
        f"{authoritative_meta['decision']['stage_d_readiness']}",
        "- Stage D requires separate owner approval in the current thread.",
    ]
    return "\n".join(lines) + "\n"


def capacity_comparison_markdown(
    *,
    old_capacity: dict[str, Any] | None,
    new_capacity: dict[str, Any],
) -> str:
    lines = [
        "# Authoritative Full-Scale Capacity Estimate 2011+",
        "",
        "## New Authoritative Estimate",
    ]
    for key, value in new_capacity.get("summary", {}).items():
        lines.append(f"- {key}: {value}")
    if old_capacity:
        lines.extend(["", "## Comparison With v1.1 Live-Only Estimate"])
        for key in (
            "estimated_full_tests",
            "estimated_endpoint_requests",
            "estimated_sqlite_db_size_bytes",
            "sqlite_recommendation",
        ):
            lines.append(
                f"- {key}: old={old_capacity.get('summary', {}).get(key)} "
                f"new={new_capacity.get('summary', {}).get(key)}"
            )
    lines.extend(["", "## Runtime Estimates"])
    for row in new_capacity.get("runtime_estimates", []):
        lines.append(
            f"- delay={row['delay_seconds']}s: request delay "
            f"{row['request_delay_hours']} hours"
        )
    lines.extend(
        [
            "",
            "## Operational Requirement",
            "- Use resumable collection runs.",
            "- Back up DB before Stage D.",
            "- Keep `data/` artifacts ignored.",
        ]
    )
    return "\n".join(lines) + "\n"


def edge_case_plan_markdown(rows: list[dict[str, Any]], output: Path) -> str:
    lines = [
        "# Edge-Case Schema Validation Candidate Plan v1.2",
        "",
        "## Scope",
        "- Candidate manifest only; no collect approval is implied.",
        "- Selected from authoritative manifest rows not present in the 1500 DB.",
        "- Limit: <= 100.",
        "",
        "## Summary",
        f"- candidate rows: {len(rows)}",
        f"- candidate file: {output}",
        "",
        "## Priority Rules",
        "- 2022-2025 validated supplement rows first.",
        "- rare configuration/test type/classification next.",
        "- UNKNOWN/manual-risk proxy strata next.",
        "",
        "## Samples",
    ]
    if rows:
        for row in rows[:25]:
            lines.append(
                f"- {row['test_no']} {row['test_date']} "
                f"{row.get('discovery_authority')} "
                f"{row.get('test_configuration') or row.get('test_configuration_key')}"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Decision",
            "- Optional edge-case bounded validation requires separate approval.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
        + "\n",
        encoding="utf-8",
    )


def load_reference_seeds(
    database_path: Path,
    min_test_date: date,
) -> dict[int, ReferenceDiscoverySeed]:
    if not database_path.exists():
        raise FileNotFoundError(f"reference database not found: {database_path}")
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT test_no, test_date, crash_type, make, model, year
            FROM crash_tests
            WHERE test_date IS NOT NULL AND TRIM(test_date) != ''
            ORDER BY test_date, test_no
            """
        ).fetchall()
    finally:
        connection.close()
    seeds: dict[int, ReferenceDiscoverySeed] = {}
    for row in rows:
        test_no = _int(row["test_no"])
        test_date = _date(row["test_date"])
        if test_no is None or test_date is None or test_date < min_test_date:
            continue
        seeds[test_no] = ReferenceDiscoverySeed(
            test_no=test_no,
            test_date=test_date,
            test_date_raw=str(row["test_date"]),
            test_configuration=_str(row["crash_type"]),
            test_configuration_key=_configuration_key(_str(row["crash_type"])),
            test_type=None,
            model_year=_int(row["year"]),
            vehicle_make=_str(row["make"]),
            vehicle_model=_str(row["model"]),
        )
    return seeds


def read_manifest_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _validate_reference_seed(
    *,
    client: LiveDiscoveryClient,
    seed: ReferenceDiscoverySeed,
    min_test_date: date,
    validation_endpoints: list[str],
) -> dict[str, Any]:
    attempted: list[dict[str, object]] = []
    best_identity: dict[str, Any] | None = None
    endpoint_used: str | None = None
    for endpoint_name in validation_endpoints:
        try:
            result = client.fetch(endpoint_name, test_no=seed.test_no)
        except Exception as exc:
            attempted.append({"endpoint": endpoint_name, "error": type(exc).__name__})
            continue
        attempted.append(
            {
                "endpoint": endpoint_name,
                "http_status": result.http_status,
                "row_count": len(_payload_rows(result.payload)),
            }
        )
        if result.http_status and result.http_status >= 400:
            continue
        identity = _extract_identity(result.payload, seed.test_no)
        if identity is None:
            continue
        best_identity = identity
        endpoint_used = endpoint_name
        if _date(identity.get("test_date_raw")) is not None:
            break
    if best_identity is None:
        return _validation_row(
            seed=seed,
            validation_status="excluded_not_live_validated",
            authority_status="excluded_not_live_validated",
            validation_endpoint=endpoint_used,
            attempted=attempted,
        )
    live_date = _date(best_identity.get("test_date_raw"))
    if live_date is None:
        return _validation_row(
            seed=seed,
            identity=best_identity,
            validation_status="excluded_date_missing_or_parse_failed",
            authority_status="excluded_date_conflict",
            validation_endpoint=endpoint_used,
            attempted=attempted,
        )
    if live_date < min_test_date:
        return _validation_row(
            seed=seed,
            identity=best_identity,
            validation_status="excluded_out_of_scope",
            authority_status="excluded_out_of_scope",
            validation_endpoint=endpoint_used,
            attempted=attempted,
        )
    if live_date != seed.test_date:
        return _validation_row(
            seed=seed,
            identity=best_identity,
            validation_status="date_conflict",
            authority_status="excluded_date_conflict",
            validation_endpoint=endpoint_used,
            attempted=attempted,
        )
    drift_fields = _metadata_drift_fields(seed, best_identity)
    validation_status = (
        "validated_live_with_metadata_drift" if drift_fields else "validated_live"
    )
    return _validation_row(
        seed=seed,
        identity=best_identity,
        validation_status=validation_status,
        authority_status="authoritative_included",
        validation_endpoint=endpoint_used,
        attempted=attempted,
        drift_fields=drift_fields,
    )


def _validation_row(
    *,
    seed: ReferenceDiscoverySeed,
    validation_status: str,
    authority_status: str,
    validation_endpoint: str | None,
    attempted: list[dict[str, Any]],
    identity: dict[str, Any] | None = None,
    drift_fields: list[str] | None = None,
) -> dict[str, Any]:
    live_date_raw = _str(identity.get("test_date_raw")) if identity else None
    live_date = _date(live_date_raw)
    return {
        "test_no": seed.test_no,
        "test_date": live_date.isoformat() if live_date else None,
        "test_date_raw": live_date_raw,
        "test_date_parse_status": "parsed" if live_date else "missing_or_failed",
        "scope_status": "in_scope"
        if live_date is not None and live_date >= date(2011, 1, 1)
        else "out_of_scope_or_unknown",
        "test_configuration": _first_present(
            identity.get("test_configuration") if identity else None,
            seed.test_configuration,
        ),
        "test_configuration_key": _first_present(
            identity.get("test_configuration_key") if identity else None,
            seed.test_configuration_key,
        ),
        "test_type": _first_present(
            identity.get("test_type") if identity else None,
            seed.test_type,
        ),
        "model_year": _first_present(
            identity.get("model_year") if identity else None,
            seed.model_year,
        ),
        "vehicle_make": _first_present(
            identity.get("vehicle_make") if identity else None,
            seed.vehicle_make,
        ),
        "vehicle_model": _first_present(
            identity.get("vehicle_model") if identity else None,
            seed.vehicle_model,
        ),
        "validation_status": validation_status,
        "validation_endpoint": validation_endpoint,
        "authority_status": authority_status,
        "reference_test_date": seed.test_date.isoformat(),
        "reference_test_configuration": seed.test_configuration,
        "metadata_drift_fields": drift_fields or [],
        "attempted_endpoints": attempted,
    }


def _extract_identity(payload: dict[str, Any], expected_test_no: int) -> dict[str, Any] | None:
    for row in _iter_dicts(payload):
        test_no = _row_test_no(row)
        if test_no != expected_test_no:
            continue
        test_configuration = _first(row, "testConfiguration", "TSTCFND", "crash_type")
        return {
            "test_no": test_no,
            "test_date_raw": _first(row, "testDate", "TSTDAT", "test_date"),
            "test_configuration": _str(test_configuration),
            "test_configuration_key": _first_present(
                _str(row.get("testConfigurationKey")),
                _configuration_key(_str(test_configuration)),
            ),
            "test_type": _str(_first(row, "testType", "TSTTYPD")),
            "model_year": _int(_first(row, "modelYear", "vehicleModelYear", "YEAR")),
            "vehicle_make": _str(_first(row, "vehicleMake", "make", "MAKED")),
            "vehicle_model": _str(_first(row, "vehicleModel", "model", "MODELD")),
        }
    return None


def _manifest_row_from_search(
    row: dict[str, Any], reference_rows: dict[int, ReferenceDiscoverySeed]
) -> dict[str, Any] | None:
    test_no = _row_test_no(row)
    test_date_raw = _first(row, "testDate", "TSTDAT", "test_date")
    date_source = "live_by_search_row"
    if test_no is not None and test_date_raw is None and test_no in reference_rows:
        test_date_raw = reference_rows[test_no].test_date_raw
        date_source = "reference_seed_date"
    parsed_date = _date(test_date_raw)
    if test_no is None or parsed_date is None:
        return None
    test_configuration = _str(_first(row, "testConfiguration", "TSTCFND", "crash_type"))
    return {
        "test_no": test_no,
        "test_date": parsed_date.isoformat(),
        "test_year": parsed_date.year,
        "test_configuration_key": _first_present(
            _str(row.get("testConfigurationKey")),
            _configuration_key(test_configuration),
        ),
        "test_configuration": test_configuration,
        "test_type": _str(_first(row, "testType", "TSTTYPD")),
        "model_year": _int(_first(row, "modelYear", "vehicleModelYear", "YEAR")),
        "vehicle_make": _str(_first(row, "vehicleMake", "make", "MAKED")),
        "vehicle_model": _str(_first(row, "vehicleModel", "model", "MODELD")),
        "reason": f"live_year_slice_by_search_{date_source}",
        "scope_status": "in_scope",
        "selection_priority": 0,
        "balance_status": "full_scope_year_slice",
        "discovery_authority": "live_year_slice_by_search",
        "seed_source": "live_by_search_year_slice",
    }


def _validate_live_search_missing_date_rows(
    *,
    client: LiveDiscoveryClient,
    rows: dict[int, dict[str, Any]],
    min_test_date: date,
) -> list[dict[str, Any]]:
    validated_rows = []
    for test_no, search_row in sorted(rows.items()):
        identity = None
        endpoint_used = None
        for endpoint_name in ("test_summary", "test_detail", "metadata_export"):
            try:
                result = client.fetch(endpoint_name, test_no=test_no)
            except Exception:
                continue
            if result.http_status and result.http_status >= 400:
                continue
            identity = _extract_identity(result.payload, test_no)
            if identity is not None and _date(identity.get("test_date_raw")) is not None:
                endpoint_used = endpoint_name
                break
        if identity is None:
            continue
        parsed_date = _date(identity.get("test_date_raw"))
        if parsed_date is None or parsed_date < min_test_date:
            continue
        row = _manifest_row_from_identity(
            search_row=search_row,
            identity=identity,
            parsed_date=parsed_date,
        )
        row["reason"] = "live_year_slice_by_search_live_validated_date"
        row["validation_endpoint"] = endpoint_used
        validated_rows.append(row)
    return validated_rows


def _manifest_row_from_identity(
    *,
    search_row: dict[str, Any],
    identity: dict[str, Any],
    parsed_date: date,
) -> dict[str, Any]:
    test_configuration = _first_present(
        identity.get("test_configuration"),
        search_row.get("test_configuration"),
    )
    return {
        "test_no": identity["test_no"],
        "test_date": parsed_date.isoformat(),
        "test_year": parsed_date.year,
        "test_configuration_key": _first_present(
            identity.get("test_configuration_key"),
            search_row.get("test_configuration_key"),
            _configuration_key(_str(test_configuration)),
        ),
        "test_configuration": test_configuration,
        "test_type": _first_present(identity.get("test_type"), search_row.get("test_type")),
        "model_year": _first_present(identity.get("model_year"), search_row.get("model_year")),
        "vehicle_make": _first_present(
            identity.get("vehicle_make"),
            search_row.get("vehicle_make"),
        ),
        "vehicle_model": _first_present(
            identity.get("vehicle_model"),
            search_row.get("vehicle_model"),
        ),
        "reason": "live_year_slice_by_search",
        "scope_status": "in_scope",
        "selection_priority": 0,
        "balance_status": "full_scope_year_slice",
        "discovery_authority": "live_year_slice_by_search",
        "seed_source": "live_by_search_year_slice",
    }


def _minimal_search_row(row: dict[str, Any]) -> dict[str, Any]:
    test_configuration = _str(_first(row, "testConfiguration", "TSTCFND", "crash_type"))
    return {
        "test_no": _row_test_no(row),
        "test_configuration": test_configuration,
        "test_configuration_key": _first_present(
            _str(row.get("testConfigurationKey")),
            _configuration_key(test_configuration),
        ),
        "test_type": _str(_first(row, "testType", "TSTTYPD")),
        "model_year": _int(_first(row, "modelYear", "vehicleModelYear", "YEAR")),
        "vehicle_make": _str(_first(row, "vehicleMake", "make", "MAKED")),
        "vehicle_model": _str(_first(row, "vehicleModel", "model", "MODELD")),
    }


def _iter_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(_iter_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_iter_dicts(child))
    return found


def _payload_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("results")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _pagination(payload: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return {}
    pagination = meta.get("pagination")
    return pagination if isinstance(pagination, dict) else {}


def _validation_summary(
    rows: list[dict[str, Any]], reference_count: int, live_manifest_count: int
) -> dict[str, Any]:
    status_counter = Counter(str(row["validation_status"]) for row in rows)
    endpoint_counter = Counter(
        str(row.get("validation_endpoint") or "none") for row in rows
    )
    validated = status_counter["validated_live"] + status_counter[
        "validated_live_with_metadata_drift"
    ]
    excluded = len(rows) - validated
    return {
        "reference_seed_count": reference_count,
        "live_manifest_count": live_manifest_count,
        "reference_only_count": len(rows),
        "validated_supplement_count": validated,
        "excluded_supplement_count": excluded,
        "manual_review_count": status_counter["manual_review"],
        "validation_status_distribution": dict(sorted(status_counter.items())),
        "validation_endpoint_distribution": dict(sorted(endpoint_counter.items())),
    }


def _authoritative_row_from_live(
    row: dict[str, Any],
    test_no: int,
    parsed_date: date,
    reference_rows: dict[int, ReferenceDiscoverySeed],
) -> dict[str, Any]:
    reference_present = test_no in reference_rows
    discovery_authority = str(row.get("discovery_authority") or "live_by_search")
    seed_source = str(
        row.get("seed_source")
        or (
            "live_by_search_year_slice"
            if discovery_authority == "live_year_slice_by_search"
            else "live_by_search_full"
        )
    )
    return {
        "test_no": test_no,
        "test_date": parsed_date.isoformat(),
        "test_date_raw": row.get("test_date"),
        "test_date_parse_status": "parsed",
        "scope_status": "in_scope",
        "test_configuration": row.get("test_configuration"),
        "test_configuration_key": row.get("test_configuration_key"),
        "test_type": row.get("test_type"),
        "model_year": row.get("model_year"),
        "vehicle_make": row.get("vehicle_make"),
        "vehicle_model": row.get("vehicle_model"),
        "discovery_authority": discovery_authority,
        "seed_source": seed_source,
        "live_by_search_present": True,
        "reference_present": reference_present,
        "live_validation_status": "not_required_live_by_search",
        "validation_endpoint": None,
        "authority_status": "authoritative_included",
        "selection_status": "selected",
        "rejection_reason": None,
        "manifest_reason": row.get("manifest_reason")
        or row.get("reason")
        or seed_source,
    }


def _authoritative_row_from_validation(
    row: dict[str, Any], test_no: int, parsed_date: date
) -> dict[str, Any]:
    return {
        "test_no": test_no,
        "test_date": parsed_date.isoformat(),
        "test_date_raw": row.get("test_date_raw") or row.get("test_date"),
        "test_date_parse_status": "parsed",
        "scope_status": "in_scope",
        "test_configuration": row.get("test_configuration"),
        "test_configuration_key": row.get("test_configuration_key"),
        "test_type": row.get("test_type"),
        "model_year": row.get("model_year"),
        "vehicle_make": row.get("vehicle_make"),
        "vehicle_model": row.get("vehicle_model"),
        "discovery_authority": "reference_seed_live_validated",
        "seed_source": "reference_db",
        "live_by_search_present": False,
        "reference_present": True,
        "live_validation_status": row.get("validation_status"),
        "validation_endpoint": row.get("validation_endpoint"),
        "authority_status": "authoritative_included",
        "selection_status": "selected",
        "rejection_reason": None,
        "manifest_reason": "reference_only_live_validated",
    }


def _assign_row_hashes(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row["row_hash"] = stable_row_hash(row)


def stable_row_hash(row: dict[str, Any]) -> str:
    keys = [
        "test_no",
        "test_date",
        "test_configuration",
        "test_configuration_key",
        "test_type",
        "discovery_authority",
        "authority_status",
    ]
    payload = {key: row.get(key) for key in keys}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _authoritative_manifest_meta(
    *,
    authoritative_rows: list[dict[str, Any]],
    live_manifest: Path,
    reference_database: Path,
    validation_payload: dict[str, Any],
    output: Path,
    min_test_date: date,
) -> dict[str, Any]:
    test_numbers = [int(row["test_no"]) for row in authoritative_rows]
    dates = [_date(row.get("test_date")) for row in authoritative_rows]
    valid_dates = [item for item in dates if item is not None]
    duplicate_test_no = len(test_numbers) - len(set(test_numbers))
    pre_2011 = sum(item is not None and item < min_test_date for item in dates)
    missing = sum(item is None for item in dates)
    authority_counter = Counter(str(row["discovery_authority"]) for row in authoritative_rows)
    validation_counter = Counter(str(row["live_validation_status"]) for row in authoritative_rows)
    authority_status_counter = Counter(str(row["authority_status"]) for row in authoritative_rows)
    gates_pass = (
        duplicate_test_no == 0
        and pre_2011 == 0
        and missing == 0
        and set(authority_status_counter) == {"authoritative_included"}
        and all(row.get("discovery_authority") for row in authoritative_rows)
    )
    manifest_hash = _file_sha256(output)
    selected_authority = (
        "reference_seeded_live_validated"
        if authority_counter["reference_seed_live_validated"]
        else "live_by_search_only"
    )
    return {
        "run": {
            "created_at": _now(),
            "git_commit": _git_commit(),
            "software_version": __version__,
            "live_manifest": str(live_manifest),
            "reference_database_path_hash": _path_hash(reference_database),
            "authoritative_manifest": str(output),
            "min_test_date": min_test_date.isoformat(),
        },
        "summary": {
            "row_count": len(authoritative_rows),
            "date_range": [
                min(valid_dates).isoformat() if valid_dates else None,
                max(valid_dates).isoformat() if valid_dates else None,
            ],
            "manifest_hash": manifest_hash,
            "discovery_authority_distribution": dict(sorted(authority_counter.items())),
            "validation_status_distribution": dict(sorted(validation_counter.items())),
            "authority_status_distribution": dict(sorted(authority_status_counter.items())),
        },
        "validation_summary": validation_payload.get("summary", {}),
        "hard_gates": {
            "duplicate_test_no": duplicate_test_no,
            "pre_2011_rows": pre_2011,
            "missing_or_parse_failed_date": missing,
            "scope_status_values": sorted({row["scope_status"] for row in authoritative_rows}),
            "authority_status_values": sorted(set(authority_status_counter)),
            "anchors": {
                "7201": 7201 in test_numbers,
                "10001": 10001 in test_numbers,
                "10003": 10003 in test_numbers,
            },
            "passed": gates_pass,
        },
        "decision": {
            "selected_authority": selected_authority if gates_pass else "blocked",
            "stage_d_readiness": "approval-ready" if gates_pass else "blocked",
            "owner_approval_required": True,
            "decision_reason": (
                "reference-only seeds are included only after official live validation"
                if selected_authority == "reference_seeded_live_validated"
                else "live by-search covered all accepted rows"
            ),
        },
    }


def _metadata_drift_fields(seed: ReferenceDiscoverySeed, identity: dict[str, Any]) -> list[str]:
    checks = {
        "test_configuration": seed.test_configuration,
        "test_type": seed.test_type,
        "model_year": seed.model_year,
        "vehicle_make": seed.vehicle_make,
        "vehicle_model": seed.vehicle_model,
    }
    drift = []
    for key, reference_value in checks.items():
        live_value = identity.get(key)
        if live_value in (None, "") or reference_value in (None, ""):
            continue
        if str(live_value).strip().upper() != str(reference_value).strip().upper():
            drift.append(key)
    return drift


def _edge_case_sort_key(row: dict[str, Any]) -> tuple[int, str, str, int]:
    test_date = _date(row.get("test_date"))
    year = test_date.year if test_date else 0
    recent_priority = 0 if 2022 <= year <= 2025 else 1
    unknown_priority = 0 if "UNKNOWN" in str(row).upper() else 1
    authority_priority = (
        0 if row.get("discovery_authority") == "reference_seed_live_validated" else 1
    )
    return (
        recent_priority,
        str(authority_priority),
        str(unknown_priority),
        int(row.get("test_no") or 0),
    )


def _db_test_numbers(database_url: str) -> set[int]:
    if not database_url.startswith("sqlite:///"):
        return set()
    path = Path(database_url.removeprefix("sqlite:///"))
    if not path.exists():
        return set()
    connection = sqlite3.connect(path)
    try:
        return {
            int(row[0])
            for row in connection.execute("SELECT test_no FROM tests WHERE test_no IS NOT NULL")
        }
    finally:
        connection.close()


def _summary_value(payload: dict[str, Any] | None, key: str) -> int | None:
    if not payload:
        return None
    value = payload.get("summary", {}).get(key)
    return int(value) if value is not None else None


def _diagnostics_decision(summary: dict[str, Any]) -> str:
    if summary["year_slice_union_count"] > summary["full_by_search_row_count"]:
        return (
            "year-slice by-search returns additional official rows; "
            "authoritative manifest should use year-slice union or validated supplement"
        )
    if summary["reference_only_count"]:
        return "reference-only rows require official live validation before inclusion"
    return "live by-search full manifest is sufficient as discovery authority"


def _row_test_no(row: dict[str, Any]) -> int | None:
    return _int(_first(row, "testNo", "TSTNO", "test_no"))


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _configuration_key(value: str | None) -> str | None:
    if not value:
        return None
    return " ".join(value.strip().upper().split())


def _int(value: Any) -> int | None:
    try:
        if isinstance(value, int | str) and str(value).strip():
            return int(value)
    except (TypeError, ValueError):
        return None
    return None


def _str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(
                text[:19] if "%H" in fmt else text[:10],
                fmt,
            ).date()
        except ValueError:
            pass
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _path_hash(path: Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"
