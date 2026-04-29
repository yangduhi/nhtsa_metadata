from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from nhtsa_metadata.services.scope import ScopeDecision, evaluate_scope_from_fetch_results
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult

REQUIRED_BASELINES = {
    10001: "required_baseline_frontal_barrier",
    10003: "required_baseline_side_impactor",
}
CONFIGURATION_BUCKET_ALIASES = {
    "VEHICLE INTO BARRIER": "VTB",
    "IMPACTOR INTO VEHICLE": "ITV",
    "VEHICLE INTO POLE": "VTP",
}


class DiscoveryClient(Protocol):
    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        ...


@dataclass(frozen=True)
class ManifestCandidate:
    test_no: int
    note: str
    test_date: date
    test_configuration_key: str | None
    test_configuration: str | None
    impact_angle: object | None = None


@dataclass(frozen=True)
class ManifestRow:
    test_no: int
    test_date: str
    test_configuration_key: str | None
    test_configuration: str | None
    reason: str
    scope_status: str


@dataclass(frozen=True)
class ManifestBuildReport:
    output: str
    count: int
    limit: int
    max_per_configuration: int
    max_discovery_pages: int
    discovery_page_size: int
    min_test_date: str
    required_test_numbers: list[int]
    reference_database: str | None


class StratifiedManifestBuilder:
    def __init__(self, client: DiscoveryClient) -> None:
        self.client = client

    def build(
        self,
        output: Path,
        limit: int = 40,
        max_per_configuration: int = 5,
        max_discovery_pages: int = 5,
        discovery_page_size: int = 100,
        min_test_date: date = date(2011, 1, 1),
        reference_database: Path | None = None,
    ) -> ManifestBuildReport:
        if limit < len(REQUIRED_BASELINES):
            raise ValueError("limit must fit required baseline tests")
        if max_per_configuration < 1:
            raise ValueError("max_per_configuration must be >= 1")
        required = self._fetch_required_baselines(min_test_date)
        discovered = self._fetch_discovery_candidates(
            max_discovery_pages, discovery_page_size, min_test_date
        )
        reference_candidates = (
            load_reference_manifest_candidates(reference_database, min_test_date)
            if reference_database is not None
            else []
        )
        rows = select_manifest_rows(
            required + discovered + reference_candidates, limit, max_per_configuration
        )
        write_manifest(output, rows)
        return ManifestBuildReport(
            output=str(output),
            count=len(rows),
            limit=limit,
            max_per_configuration=max_per_configuration,
            max_discovery_pages=max_discovery_pages,
            discovery_page_size=discovery_page_size,
            min_test_date=min_test_date.isoformat(),
            required_test_numbers=sorted(REQUIRED_BASELINES),
            reference_database=str(reference_database) if reference_database is not None else None,
        )

    def _fetch_required_baselines(self, min_test_date: date) -> list[ManifestCandidate]:
        candidates: list[ManifestCandidate] = []
        for test_no in sorted(REQUIRED_BASELINES):
            result = self.client.fetch("test_summary", test_no=test_no)
            rows = _payload_rows(result)
            if rows:
                scope = evaluate_scope_from_fetch_results([result], min_test_date)
                candidate = _candidate_from_row(
                    rows[0],
                    note=REQUIRED_BASELINES[test_no],
                    min_test_date=min_test_date,
                    scope=scope,
                )
                if candidate is not None:
                    candidates.append(candidate)
                    continue
            raise ValueError(f"required baseline test is out of scope or missing date: {test_no}")
        return candidates

    def _fetch_discovery_candidates(
        self, max_discovery_pages: int, discovery_page_size: int, min_test_date: date
    ) -> list[ManifestCandidate]:
        candidates: list[ManifestCandidate] = []
        for page_number in range(max_discovery_pages):
            result = self.client.fetch(
                "search",
                page_number=page_number,
                count=discovery_page_size,
                testDateFrom=min_test_date.isoformat(),
            )
            rows = _payload_rows(result)
            for row in rows:
                candidate = _candidate_from_row(
                    row,
                    note="stratified discovery",
                    min_test_date=min_test_date,
                    scope=None,
                )
                if candidate is not None:
                    candidates.append(candidate)
            pagination = result.meta.pagination
            if pagination is None:
                break
            accumulated = len(candidates)
            total = pagination.total or 0
            if not pagination.next_url and (total == 0 or accumulated >= total):
                break
        return candidates


def select_manifest_rows(
    candidates: list[ManifestCandidate],
    limit: int,
    max_per_configuration: int,
) -> list[ManifestRow]:
    selected: list[ManifestRow] = []
    seen: set[int] = set()
    configuration_counts: dict[str, int] = {}

    for candidate in candidates:
        if candidate.test_no not in REQUIRED_BASELINES:
            continue
        if candidate.test_no in seen:
            continue
        selected.append(_row(candidate, REQUIRED_BASELINES[candidate.test_no]))
        seen.add(candidate.test_no)
        configuration_counts[_configuration_bucket(candidate)] = (
            configuration_counts.get(_configuration_bucket(candidate), 0) + 1
        )

    for candidate in candidates:
        if len(selected) >= limit:
            break
        if candidate.test_no in seen:
            continue
        bucket = _configuration_bucket(candidate)
        if configuration_counts.get(bucket, 0) >= max_per_configuration:
            continue
        selected.append(_row(candidate, "stratified_configuration"))
        seen.add(candidate.test_no)
        configuration_counts[bucket] = configuration_counts.get(bucket, 0) + 1
    return selected


def write_manifest(output: Path, rows: list[ManifestRow]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "test_no",
                "test_date",
                "test_configuration_key",
                "test_configuration",
                "reason",
                "scope_status",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def load_reference_manifest_candidates(
    database_path: Path, min_test_date: date
) -> list[ManifestCandidate]:
    """Load bounded manifest seed candidates from the legacy local SQLite catalog."""
    if not database_path.exists():
        raise FileNotFoundError(f"reference database not found: {database_path}")
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT test_no, test_date, crash_type
            FROM crash_tests
            WHERE test_date IS NOT NULL AND TRIM(test_date) != ''
            ORDER BY test_date, test_no
            """
        ).fetchall()
    finally:
        connection.close()
    candidates: list[ManifestCandidate] = []
    for row in rows:
        test_no = _int_value(row["test_no"])
        test_date = _date_value(row["test_date"])
        if test_no is None or test_date is None or test_date < min_test_date:
            continue
        test_configuration = _str_value(row["crash_type"])
        candidates.append(
            ManifestCandidate(
                test_no=test_no,
                note="reference_database_seed",
                test_date=test_date,
                test_configuration_key=None,
                test_configuration=test_configuration,
            )
        )
    return candidates


def _payload_rows(result: SourceFetchResult) -> list[dict[str, object]]:
    raw_rows = result.payload.get("results")
    if not isinstance(raw_rows, list):
        return []
    return [row for row in raw_rows if isinstance(row, dict)]


def _candidate_from_row(
    row: dict[str, object],
    note: str,
    min_test_date: date,
    scope: ScopeDecision | None,
) -> ManifestCandidate | None:
    test_no = _int_value(_first(row, "testNo", "TSTNO"))
    if test_no is None:
        return None
    test_date = (
        scope.test_date
        if scope is not None
        else _date_value(_first(row, "testDate", "TSTDAT"))
    )
    if test_date is None or test_date < min_test_date:
        return None
    return ManifestCandidate(
        test_no=test_no,
        note=note,
        test_date=test_date,
        test_configuration_key=_str_value(row.get("testConfigurationKey")),
        test_configuration=_str_value(_first(row, "testConfiguration", "TSTCFND")),
        impact_angle=_first(row, "impactAngle", "IMPANG"),
    )


def _row(candidate: ManifestCandidate, selection_reason: str) -> ManifestRow:
    return ManifestRow(
        test_no=candidate.test_no,
        test_date=candidate.test_date.isoformat(),
        test_configuration_key=candidate.test_configuration_key,
        test_configuration=candidate.test_configuration,
        reason=selection_reason,
        scope_status="in_scope",
    )


def _configuration_bucket(candidate: ManifestCandidate) -> str:
    if candidate.test_configuration_key:
        return candidate.test_configuration_key.strip().upper()
    if candidate.test_configuration:
        normalized = re.sub(r"\s+", " ", candidate.test_configuration.strip().upper())
        return CONFIGURATION_BUCKET_ALIASES.get(normalized, normalized)
    return "UNKNOWN"


def _first(row: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _int_value(value: object | None) -> int | None:
    try:
        if isinstance(value, int | str):
            return int(value)
        return None
    except (TypeError, ValueError):
        return None


def _str_value(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date_value(value: object | None) -> date | None:
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
