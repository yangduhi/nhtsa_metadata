from __future__ import annotations

import csv
import re
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from nhtsa_metadata.services.scope import ScopeDecision, evaluate_scope_from_fetch_results
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult

REQUIRED_BASELINES = {
    7201: "required_anchor_2011_start",
    10001: "required_baseline_frontal_barrier",
    10003: "required_baseline_side_impactor",
}
ACTUAL_CRASH_CONFIGURATIONS = {
    "IMPACTOR INTO VEHICLE",
    "ROLLOVER",
    "VEHICLE INTO BARRIER",
    "VEHICLE INTO POLE",
    "VEHICLE INTO VEHICLE",
}
CONFIGURATION_BUCKET_ALIASES = {
    "FORWARD COLLISION WARNING PERFORMANCE TEST": "FCW_PERFORMANCE",
    "IMPACTOR INTO IMPACTOR": "IMPACTOR_INTO_IMPACTOR",
    "VEHICLE INTO BARRIER": "VTB",
    "IMPACTOR INTO VEHICLE": "ITV",
    "LANE DEPARTURE WARNING PERFORMANCE TEST": "LDW_PERFORMANCE",
    "LOW RISK DEPLOYMENT": "LRD",
    "SLED WITH VEHICLE BODY": "SLED_WITH_BODY",
    "SLED WITHOUT VEHICLE BODY": "SLED_NO_BODY",
    "STATIC AIR BAG TEST SIDE": "STATIC_SIDE_AIRBAG",
    "TRAFFIC JAM ASSIST": "TRAFFIC_JAM_ASSIST",
    "VEHICLE INTO POLE": "VTP",
    "VEHICLE INTO VEHICLE": "VTV",
}
SELECTION_BUCKET_ALIASES = {
    "VEHICLE INTO BARRIER": "VTB",
    "IMPACTOR INTO VEHICLE": "ITV",
    "VEHICLE INTO POLE": "VTP",
}
BalanceStrategy = Literal["configuration", "type-year"]
BalancePriority = Literal["type-first", "year-first", "equal-weighted"]


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
    test_type: str | None = None
    model_year: int | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    candidate_source: str = "live"


@dataclass(frozen=True)
class ManifestRow:
    test_no: int
    test_date: str
    test_year: int
    test_configuration_key: str | None
    test_configuration: str | None
    test_type: str | None
    model_year: int | None
    vehicle_make: str | None
    vehicle_model: str | None
    reason: str
    scope_status: str
    selection_priority: int
    balance_status: str


@dataclass(frozen=True)
class ManifestBuildReport:
    output: str
    count: int
    limit: int
    max_per_configuration: int
    max_discovery_pages: int
    discovery_page_size: int
    min_test_date: str
    year_from: int | None
    year_to: int | None
    balance_strategy: str
    balance_priority: str
    relax_balance: bool
    required_test_numbers: list[int]
    include_required_baselines: bool
    actual_crash_only: bool
    exclude_manifests: list[str]
    excluded_test_numbers: int
    reference_database: str | None
    discovered_live_candidates: int
    reference_candidates: int
    year_distribution: dict[str, int]
    configuration_distribution: dict[str, int]
    balance_status: str


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
        year_from: int | None = None,
        year_to: int | None = None,
        balance_strategy: BalanceStrategy = "configuration",
        balance_priority: BalancePriority = "type-first",
        relax_balance: bool = False,
        include_required_baselines: bool = True,
        actual_crash_only: bool = False,
        exclude_manifests: list[Path] | None = None,
    ) -> ManifestBuildReport:
        required_baselines = REQUIRED_BASELINES if include_required_baselines else {}
        if limit < len(required_baselines):
            raise ValueError("limit must fit required baseline tests")
        if max_per_configuration < 1:
            raise ValueError("max_per_configuration must be >= 1")
        if discovery_page_size < 1:
            raise ValueError("discovery_page_size must be >= 1")
        if balance_strategy not in {"configuration", "type-year"}:
            raise ValueError("unsupported balance_strategy")
        if balance_priority not in {"type-first", "year-first", "equal-weighted"}:
            raise ValueError("unsupported balance_priority")

        effective_min_date = (
            max(min_test_date, date(year_from, 1, 1)) if year_from else min_test_date
        )
        max_test_date = date(year_to, 12, 31) if year_to else None
        excluded_test_numbers = load_excluded_test_numbers(exclude_manifests or [])
        required = self._fetch_required_baselines(
            effective_min_date, max_test_date, required_baselines
        )
        reference_candidates = (
            load_reference_manifest_candidates(
                reference_database, effective_min_date, max_test_date
            )
            if reference_database is not None
            else []
        )
        reference_lookup = {candidate.test_no: candidate for candidate in reference_candidates}
        discovered = self._fetch_discovery_candidates(
            max_discovery_pages=max_discovery_pages,
            discovery_page_size=discovery_page_size,
            min_test_date=effective_min_date,
            max_test_date=max_test_date,
            reference_candidates=reference_candidates,
            reference_lookup=reference_lookup,
            balance_strategy=balance_strategy,
        )
        if actual_crash_only:
            required = [
                candidate for candidate in required if _is_actual_crash_candidate(candidate)
            ]
            discovered = [
                candidate for candidate in discovered if _is_actual_crash_candidate(candidate)
            ]
            reference_candidates = [
                candidate
                for candidate in reference_candidates
                if _is_actual_crash_candidate(candidate)
            ]
        if excluded_test_numbers:
            required = [
                candidate
                for candidate in required
                if candidate.test_no not in excluded_test_numbers
            ]
            discovered = [
                candidate
                for candidate in discovered
                if candidate.test_no not in excluded_test_numbers
            ]
            reference_candidates = [
                candidate
                for candidate in reference_candidates
                if candidate.test_no not in excluded_test_numbers
            ]

        if balance_strategy == "type-year":
            rows = select_type_year_manifest_rows(
                required + discovered,
                limit=limit,
                year_from=year_from,
                year_to=year_to,
                balance_priority=balance_priority,
                relax_balance=relax_balance,
                required_baselines=required_baselines,
            )
        else:
            rows = select_manifest_rows(
                required + discovered + reference_candidates,
                limit,
                max_per_configuration,
                required_baselines=required_baselines,
            )
        if len(rows) != limit:
            raise ValueError(f"manifest hard gate failed: expected {limit} rows, got {len(rows)}")
        if (
            include_required_baselines
            and {row.test_no for row in rows} & set(required_baselines) != set(required_baselines)
        ):
            raise ValueError("manifest hard gate failed: required anchors missing")
        if excluded_test_numbers and {row.test_no for row in rows} & excluded_test_numbers:
            raise ValueError("manifest hard gate failed: excluded test_no selected")
        if actual_crash_only and any(
            not _is_actual_crash_configuration(row.test_configuration) for row in rows
        ):
            raise ValueError("manifest hard gate failed: non-crash row selected")
        write_manifest(output, rows)
        year_distribution = Counter(str(row.test_year) for row in rows)
        configuration_distribution = Counter(_row_configuration_bucket(row) for row in rows)
        balance_status = _manifest_balance_status(rows, year_from, year_to)
        return ManifestBuildReport(
            output=str(output),
            count=len(rows),
            limit=limit,
            max_per_configuration=max_per_configuration,
            max_discovery_pages=max_discovery_pages,
            discovery_page_size=discovery_page_size,
            min_test_date=effective_min_date.isoformat(),
            year_from=year_from,
            year_to=year_to,
            balance_strategy=balance_strategy,
            balance_priority=balance_priority,
            relax_balance=relax_balance,
            required_test_numbers=sorted(required_baselines),
            include_required_baselines=include_required_baselines,
            actual_crash_only=actual_crash_only,
            exclude_manifests=[str(path) for path in exclude_manifests or []],
            excluded_test_numbers=len(excluded_test_numbers),
            reference_database=str(reference_database) if reference_database is not None else None,
            discovered_live_candidates=len({candidate.test_no for candidate in discovered}),
            reference_candidates=len(reference_candidates),
            year_distribution=dict(sorted(year_distribution.items())),
            configuration_distribution=dict(sorted(configuration_distribution.items())),
            balance_status=balance_status,
        )

    def _fetch_required_baselines(
        self,
        min_test_date: date,
        max_test_date: date | None,
        required_baselines: dict[int, str],
    ) -> list[ManifestCandidate]:
        candidates: list[ManifestCandidate] = []
        for test_no in sorted(required_baselines):
            result = self.client.fetch("test_summary", test_no=test_no)
            rows = _payload_rows(result)
            if rows:
                scope = evaluate_scope_from_fetch_results([result], min_test_date)
                candidate = _candidate_from_row(
                    rows[0],
                    note=required_baselines[test_no],
                    min_test_date=min_test_date,
                    max_test_date=max_test_date,
                    scope=scope,
                    candidate_source="live_required",
                )
                if candidate is not None:
                    candidates.append(candidate)
                    continue
            raise ValueError(f"required baseline test is out of scope or missing date: {test_no}")
        return candidates

    def _fetch_discovery_candidates(
        self,
        max_discovery_pages: int,
        discovery_page_size: int,
        min_test_date: date,
        max_test_date: date | None,
        reference_candidates: list[ManifestCandidate],
        reference_lookup: dict[int, ManifestCandidate],
        balance_strategy: BalanceStrategy,
    ) -> list[ManifestCandidate]:
        if balance_strategy != "type-year":
            return self._fetch_search_pages(
                max_discovery_pages,
                discovery_page_size,
                min_test_date,
                max_test_date,
                None,
                reference_lookup,
            )
        configurations = sorted(
            {
                candidate.test_configuration
                for candidate in reference_candidates
                if candidate.test_configuration
            }
        )
        del configurations
        # The live by-search endpoint currently returns date-less summary rows, and its
        # testConfiguration query is not reliable for these labels. Use bounded global
        # discovery, then stratify locally with reference DB dates.
        effective_pages = max(max_discovery_pages, 50)
        return self._fetch_search_pages(
            effective_pages,
            discovery_page_size,
            min_test_date,
            max_test_date,
            None,
            reference_lookup,
        )

    def _fetch_search_pages(
        self,
        max_discovery_pages: int,
        discovery_page_size: int,
        min_test_date: date,
        max_test_date: date | None,
        test_configuration: str | None,
        reference_lookup: dict[int, ManifestCandidate],
    ) -> list[ManifestCandidate]:
        candidates: list[ManifestCandidate] = []
        for page_number in range(max_discovery_pages):
            query: dict[str, object] = {
                "page_number": page_number,
                "count": discovery_page_size,
                "testDateFrom": min_test_date.isoformat(),
            }
            if max_test_date is not None:
                query["testDateTo"] = max_test_date.isoformat()
            if test_configuration is not None:
                query["testConfiguration"] = test_configuration
            result = self.client.fetch("search", **query)
            rows = _payload_rows(result)
            if not rows:
                break
            for row in rows:
                normalized_row = _with_reference_date(row, reference_lookup)
                candidate = _candidate_from_row(
                    normalized_row,
                    note="live_by_search",
                    min_test_date=min_test_date,
                    max_test_date=max_test_date,
                    scope=None,
                    candidate_source="live_search",
                )
                if candidate is not None:
                    candidates.append(candidate)
        return candidates


def select_manifest_rows(
    candidates: list[ManifestCandidate],
    limit: int,
    max_per_configuration: int,
    required_baselines: dict[int, str] | None = None,
) -> list[ManifestRow]:
    baselines = required_baselines if required_baselines is not None else REQUIRED_BASELINES
    selected: list[ManifestCandidate] = []
    seen: set[int] = set()
    configuration_counts: dict[str, int] = {}

    for candidate in candidates:
        if candidate.test_no not in baselines:
            continue
        if candidate.test_no in seen:
            continue
        selected.append(candidate)
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
        selected.append(candidate)
        seen.add(candidate.test_no)
        configuration_counts[bucket] = configuration_counts.get(bucket, 0) + 1
    return [
        _row(
            candidate,
            baselines.get(candidate.test_no, "stratified_configuration"),
            index,
        )
        for index, candidate in enumerate(selected, 1)
    ]


def select_type_year_manifest_rows(
    candidates: list[ManifestCandidate],
    limit: int,
    year_from: int | None,
    year_to: int | None,
    balance_priority: BalancePriority,
    relax_balance: bool,
    required_baselines: dict[int, str] | None = None,
) -> list[ManifestRow]:
    del balance_priority  # v1 implements the approved type-first behavior only.
    baselines = required_baselines if required_baselines is not None else REQUIRED_BASELINES
    unique = _dedupe_candidates(candidates)
    required = [candidate for candidate in unique if candidate.test_no in baselines]
    available = [candidate for candidate in unique if candidate.test_no not in baselines]
    selected: list[ManifestCandidate] = []
    seen: set[int] = set()
    for candidate in sorted(required, key=lambda item: item.test_no):
        selected.append(candidate)
        seen.add(candidate.test_no)

    remaining_limit = limit - len(selected)
    type_capacities = Counter(_configuration_bucket(candidate) for candidate in available)
    type_quota = _waterfill_quota(dict(type_capacities), remaining_limit)
    year_capacities = Counter(candidate.test_date.year for candidate in available)
    year_quota = _waterfill_quota(dict(year_capacities), remaining_limit)
    year_counts: Counter[int] = Counter(candidate.test_date.year for candidate in selected)
    type_counts: Counter[str] = Counter(_configuration_bucket(candidate) for candidate in selected)

    grouped: dict[str, list[ManifestCandidate]] = {}
    for candidate in available:
        grouped.setdefault(_configuration_bucket(candidate), []).append(candidate)
    for bucket in grouped:
        grouped[bucket].sort(key=lambda item: (item.test_date, item.test_no))

    for raw_bucket in sorted(type_quota, key=str):
        bucket = str(raw_bucket)
        target = type_quota[bucket]
        while type_counts[bucket] < target and len(selected) < limit:
            next_candidate = _pop_best_year_candidate(
                grouped[bucket], seen, year_counts, year_quota
            )
            if next_candidate is None:
                break
            selected.append(next_candidate)
            seen.add(next_candidate.test_no)
            type_counts[bucket] += 1
            year_counts[next_candidate.test_date.year] += 1

    if len(selected) < limit and relax_balance:
        leftovers = [candidate for candidate in available if candidate.test_no not in seen]
        while len(selected) < limit and leftovers:
            next_candidate = _pop_best_year_candidate(leftovers, seen, year_counts, year_quota)
            if next_candidate is None:
                break
            selected.append(next_candidate)
            seen.add(next_candidate.test_no)
            year_counts[next_candidate.test_date.year] += 1

    rows = []
    balance_status = _candidate_balance_status(selected, year_from, year_to)
    for index, candidate in enumerate(selected, 1):
        rows.append(
            _row(
                candidate,
                baselines.get(candidate.test_no, "type_first_live_by_search"),
                index,
                balance_status=balance_status,
            )
        )
    return rows


def write_manifest(output: Path, rows: list[ManifestRow]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def load_reference_manifest_candidates(
    database_path: Path, min_test_date: date, max_test_date: date | None = None
) -> list[ManifestCandidate]:
    """Load bounded manifest seed candidates from the legacy local SQLite catalog."""
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
    candidates: list[ManifestCandidate] = []
    for row in rows:
        test_no = _int_value(row["test_no"])
        test_date = _date_value(row["test_date"])
        if test_no is None or test_date is None or test_date < min_test_date:
            continue
        if max_test_date is not None and test_date > max_test_date:
            continue
        test_configuration = _str_value(row["crash_type"])
        candidates.append(
            ManifestCandidate(
                test_no=test_no,
                note="reference_database_seed",
                test_date=test_date,
                test_configuration_key=_configuration_key_from_text(test_configuration),
                test_configuration=test_configuration,
                model_year=_int_value(row["year"]),
                vehicle_make=_str_value(row["make"]),
                vehicle_model=_str_value(row["model"]),
                candidate_source="reference",
            )
        )
    return candidates


def load_excluded_test_numbers(manifest_paths: list[Path]) -> set[int]:
    excluded: set[int] = set()
    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            raise FileNotFoundError(f"exclude manifest not found: {manifest_path}")
        with manifest_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                test_no = _int_value(row.get("test_no"))
                if test_no is not None:
                    excluded.add(test_no)
    return excluded


def _payload_rows(result: SourceFetchResult) -> list[dict[str, object]]:
    raw_rows = result.payload.get("results")
    if not isinstance(raw_rows, list):
        return []
    return [row for row in raw_rows if isinstance(row, dict)]


def _candidate_from_row(
    row: dict[str, object],
    note: str,
    min_test_date: date,
    max_test_date: date | None,
    scope: ScopeDecision | None,
    candidate_source: str,
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
    if max_test_date is not None and test_date > max_test_date:
        return None
    test_configuration = _str_value(_first(row, "testConfiguration", "TSTCFND"))
    test_configuration_key = _str_value(row.get("testConfigurationKey"))
    return ManifestCandidate(
        test_no=test_no,
        note=note,
        test_date=test_date,
        test_configuration_key=test_configuration_key
        or _configuration_key_from_text(test_configuration),
        test_configuration=test_configuration,
        impact_angle=_first(row, "impactAngle", "IMPANG"),
        test_type=_str_value(_first(row, "testType", "TSTTYPD")),
        model_year=_int_value(_first(row, "modelYear", "vehicleModelYear", "YEAR")),
        vehicle_make=_str_value(_first(row, "vehicleMake", "make", "MAKED")),
        vehicle_model=_str_value(_first(row, "vehicleModel", "model", "MODELD")),
        candidate_source=candidate_source,
    )


def _with_reference_date(
    row: dict[str, object], reference_lookup: dict[int, ManifestCandidate]
) -> dict[str, object]:
    test_no = _int_value(_first(row, "testNo", "TSTNO"))
    if test_no is None:
        return row
    reference = reference_lookup.get(test_no)
    if reference is None:
        return row
    enriched = dict(row)
    if _first(enriched, "testDate", "TSTDAT") is None:
        enriched["testDate"] = reference.test_date.isoformat()
    if _first(enriched, "testConfiguration", "TSTCFND") is None:
        enriched["testConfiguration"] = reference.test_configuration
    if _first(enriched, "modelYear", "vehicleModelYear", "YEAR") is None:
        enriched["modelYear"] = reference.model_year
    if _first(enriched, "vehicleMake", "make", "MAKED") is None:
        enriched["vehicleMake"] = reference.vehicle_make
    if _first(enriched, "vehicleModel", "model", "MODELD") is None:
        enriched["vehicleModel"] = reference.vehicle_model
    return enriched


def _row(
    candidate: ManifestCandidate,
    selection_reason: str,
    selection_priority: int,
    balance_status: str = "balanced",
) -> ManifestRow:
    return ManifestRow(
        test_no=candidate.test_no,
        test_date=candidate.test_date.isoformat(),
        test_year=candidate.test_date.year,
        test_configuration_key=candidate.test_configuration_key,
        test_configuration=candidate.test_configuration,
        test_type=candidate.test_type,
        model_year=candidate.model_year,
        vehicle_make=candidate.vehicle_make,
        vehicle_model=candidate.vehicle_model,
        reason=selection_reason,
        scope_status="in_scope",
        selection_priority=selection_priority,
        balance_status=balance_status,
    )


def _configuration_bucket(candidate: ManifestCandidate) -> str:
    if candidate.test_configuration:
        return _selection_bucket_from_text(candidate.test_configuration) or "UNKNOWN"
    if candidate.test_configuration_key:
        return candidate.test_configuration_key.strip().upper()
    return "UNKNOWN"


def _row_configuration_bucket(row: ManifestRow) -> str:
    if row.test_configuration:
        return _selection_bucket_from_text(row.test_configuration) or "UNKNOWN"
    if row.test_configuration_key:
        return row.test_configuration_key.strip().upper()
    return "UNKNOWN"


def _configuration_key_from_text(test_configuration: str | None) -> str | None:
    if not test_configuration:
        return None
    normalized = re.sub(r"\s+", " ", test_configuration.strip().upper())
    return CONFIGURATION_BUCKET_ALIASES.get(normalized, normalized)


def _is_actual_crash_candidate(candidate: ManifestCandidate) -> bool:
    return _is_actual_crash_configuration(candidate.test_configuration)


def _is_actual_crash_configuration(test_configuration: str | None) -> bool:
    if not test_configuration:
        return False
    normalized = re.sub(r"\s+", " ", test_configuration.strip().upper())
    return normalized in ACTUAL_CRASH_CONFIGURATIONS


def _selection_bucket_from_text(test_configuration: str | None) -> str | None:
    if not test_configuration:
        return None
    normalized = re.sub(r"\s+", " ", test_configuration.strip().upper())
    return SELECTION_BUCKET_ALIASES.get(normalized, normalized)


def _dedupe_candidates(candidates: list[ManifestCandidate]) -> list[ManifestCandidate]:
    deduped: dict[int, ManifestCandidate] = {}
    for candidate in candidates:
        existing = deduped.get(candidate.test_no)
        if existing is None or _source_priority(candidate) < _source_priority(existing):
            deduped[candidate.test_no] = candidate
    return sorted(deduped.values(), key=lambda item: (item.test_date, item.test_no))


def _source_priority(candidate: ManifestCandidate) -> int:
    if candidate.candidate_source == "live_required":
        return 0
    if candidate.candidate_source == "live_search":
        return 1
    return 2


def _waterfill_quota(capacities: dict[Any, int], total: int) -> dict[Any, int]:
    active = set(capacities)
    quota = {key: 0 for key in capacities}
    remaining = total
    while active:
        share = remaining // len(active)
        capped = [key for key in active if capacities[key] <= share]
        if not capped:
            break
        for key in sorted(capped, key=str):
            quota[key] = capacities[key]
            remaining -= quota[key]
            active.remove(key)
    if active:
        ordered = sorted(active, key=str)
        base = remaining // len(ordered)
        extra = remaining % len(ordered)
        for index, key in enumerate(ordered):
            quota[key] = base + (1 if index < extra else 0)
    return quota


def _pop_best_year_candidate(
    candidates: list[ManifestCandidate],
    seen: set[int],
    year_counts: Counter[int],
    year_quota: dict[object, int],
) -> ManifestCandidate | None:
    available = [candidate for candidate in candidates if candidate.test_no not in seen]
    if not available:
        return None
    best = min(
        available,
        key=lambda item: (
            year_counts[item.test_date.year] - int(year_quota.get(item.test_date.year, 0)),
            item.test_date,
            item.test_no,
        ),
    )
    candidates.remove(best)
    return best


def _candidate_balance_status(
    candidates: list[ManifestCandidate], year_from: int | None, year_to: int | None
) -> str:
    if year_from is None or year_to is None:
        return "balanced"
    expected_years = list(range(year_from, year_to + 1))
    year_counts = Counter(candidate.test_date.year for candidate in candidates)
    if any(year_counts.get(year, 0) == 0 for year in expected_years):
        return "relaxed_missing_year"
    return "type_first_relaxed_year"


def _manifest_balance_status(
    rows: list[ManifestRow], year_from: int | None, year_to: int | None
) -> str:
    if year_from is None or year_to is None:
        return "balanced"
    expected_years = list(range(year_from, year_to + 1))
    counts = Counter(row.test_year for row in rows)
    if any(counts.get(year, 0) == 0 for year in expected_years):
        return "relaxed_missing_year"
    return "type_first_relaxed_year"


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
