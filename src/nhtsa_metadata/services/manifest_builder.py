from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult

REQUIRED_BASELINES = {
    10001: "required_baseline_frontal_barrier",
    10003: "required_baseline_side_impactor",
}


class DiscoveryClient(Protocol):
    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        ...


@dataclass(frozen=True)
class ManifestCandidate:
    test_no: int
    note: str
    test_type: str | None
    test_configuration_key: str | None
    test_configuration: str | None
    impact_angle: object | None = None


@dataclass(frozen=True)
class ManifestRow:
    test_no: int
    note: str
    test_type: str | None
    test_configuration_key: str | None
    test_configuration: str | None
    selection_reason: str


@dataclass(frozen=True)
class ManifestBuildReport:
    output: str
    count: int
    limit: int
    max_per_configuration: int
    max_discovery_pages: int
    discovery_page_size: int
    required_test_numbers: list[int]


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
    ) -> ManifestBuildReport:
        if limit < len(REQUIRED_BASELINES):
            raise ValueError("limit must fit required baseline tests")
        if max_per_configuration < 1:
            raise ValueError("max_per_configuration must be >= 1")
        required = self._fetch_required_baselines()
        discovered = self._fetch_discovery_candidates(max_discovery_pages, discovery_page_size)
        rows = select_manifest_rows(required + discovered, limit, max_per_configuration)
        write_manifest(output, rows)
        return ManifestBuildReport(
            output=str(output),
            count=len(rows),
            limit=limit,
            max_per_configuration=max_per_configuration,
            max_discovery_pages=max_discovery_pages,
            discovery_page_size=discovery_page_size,
            required_test_numbers=sorted(REQUIRED_BASELINES),
        )

    def _fetch_required_baselines(self) -> list[ManifestCandidate]:
        candidates: list[ManifestCandidate] = []
        for test_no in sorted(REQUIRED_BASELINES):
            result = self.client.fetch("test_summary", test_no=test_no)
            rows = _payload_rows(result)
            if rows:
                candidate = _candidate_from_row(rows[0], note=REQUIRED_BASELINES[test_no])
                if candidate is not None:
                    candidates.append(candidate)
                    continue
                candidates.append(_fallback_required_candidate(test_no))
            else:
                candidates.append(_fallback_required_candidate(test_no))
        return candidates

    def _fetch_discovery_candidates(
        self, max_discovery_pages: int, discovery_page_size: int
    ) -> list[ManifestCandidate]:
        candidates: list[ManifestCandidate] = []
        for page_number in range(max_discovery_pages):
            result = self.client.fetch(
                "test_results", page_number=page_number, count=discovery_page_size
            )
            rows = _payload_rows(result)
            for row in rows:
                candidate = _candidate_from_row(row, note="stratified discovery")
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
                "note",
                "test_type",
                "test_configuration_key",
                "test_configuration",
                "selection_reason",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _payload_rows(result: SourceFetchResult) -> list[dict[str, object]]:
    raw_rows = result.payload.get("results")
    if not isinstance(raw_rows, list):
        return []
    return [row for row in raw_rows if isinstance(row, dict)]


def _candidate_from_row(row: dict[str, object], note: str) -> ManifestCandidate | None:
    test_no = _int_value(_first(row, "testNo", "TSTNO"))
    if test_no is None:
        return None
    return ManifestCandidate(
        test_no=test_no,
        note=note,
        test_type=_str_value(_first(row, "testType", "TSTTYPD")),
        test_configuration_key=_str_value(row.get("testConfigurationKey")),
        test_configuration=_str_value(_first(row, "testConfiguration", "TSTCFND")),
        impact_angle=_first(row, "impactAngle", "IMPANG"),
    )


def _fallback_required_candidate(test_no: int) -> ManifestCandidate:
    return ManifestCandidate(
        test_no=test_no,
        note=REQUIRED_BASELINES[test_no],
        test_type=None,
        test_configuration_key=None,
        test_configuration=None,
    )


def _row(candidate: ManifestCandidate, selection_reason: str) -> ManifestRow:
    return ManifestRow(
        test_no=candidate.test_no,
        note=candidate.note,
        test_type=candidate.test_type,
        test_configuration_key=candidate.test_configuration_key,
        test_configuration=candidate.test_configuration,
        selection_reason=selection_reason,
    )


def _configuration_bucket(candidate: ManifestCandidate) -> str:
    if candidate.test_configuration_key:
        return candidate.test_configuration_key.strip().upper()
    if candidate.test_configuration:
        return re.sub(r"\s+", " ", candidate.test_configuration.strip().upper())
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
