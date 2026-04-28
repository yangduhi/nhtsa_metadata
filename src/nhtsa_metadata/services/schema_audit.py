from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    Barrier,
    CrashTest,
    MediaAsset,
    SourceFieldCatalog,
    SourcePayload,
    SourcePayloadObservation,
    TestParticipant,
    Vehicle,
)
from nhtsa_metadata.sources.nhtsa_crash.field_catalog import normalize_field_path


@dataclass(frozen=True)
class SchemaAuditReport:
    test_type_distribution: list[dict[str, object]]
    test_configuration_distribution: list[dict[str, object]]
    participant_patterns: list[dict[str, object]]
    empty_endpoints: list[dict[str, object]]
    media_asset_kinds: list[dict[str, object]]
    canonical_duplicate_groups: dict[str, list[dict[str, object]]]
    unmapped_fields: list[dict[str, object]]
    endpoint_payload_observation_coverage: list[dict[str, object]]


class SchemaAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def report(self) -> SchemaAuditReport:
        tests = list(self.session.scalars(select(CrashTest).order_by(CrashTest.test_no)))
        vehicles = list(self.session.scalars(select(Vehicle)))
        barriers = list(self.session.scalars(select(Barrier)))
        participants = list(self.session.scalars(select(TestParticipant)))
        payloads = list(self.session.scalars(select(SourcePayload)))
        observations = list(self.session.scalars(select(SourcePayloadObservation)))
        fields = list(self.session.scalars(select(SourceFieldCatalog)))
        assets = list(self.session.scalars(select(MediaAsset)))
        test_no_by_id = {test.id: test.test_no for test in tests}

        return SchemaAuditReport(
            test_type_distribution=_counter_rows(test.test_type for test in tests),
            test_configuration_distribution=_counter_rows(
                _configuration_key(test) for test in tests
            ),
            participant_patterns=_participant_patterns(participants, test_no_by_id),
            empty_endpoints=_empty_endpoints(payloads),
            media_asset_kinds=_media_asset_kinds(assets, test_no_by_id),
            canonical_duplicate_groups={
                "vehicles": _vehicle_duplicates(vehicles),
                "test_participants": _participant_duplicates(participants, test_no_by_id),
                "barriers": _barrier_duplicates(barriers),
            },
            unmapped_fields=_unmapped_fields(fields),
            endpoint_payload_observation_coverage=_endpoint_coverage(payloads, observations),
        )


def report_to_dict(report: SchemaAuditReport) -> dict[str, object]:
    return {
        "test_type_distribution": report.test_type_distribution,
        "test_configuration_distribution": report.test_configuration_distribution,
        "participant_patterns": report.participant_patterns,
        "empty_endpoints": report.empty_endpoints,
        "media_asset_kinds": report.media_asset_kinds,
        "canonical_duplicate_groups": report.canonical_duplicate_groups,
        "unmapped_fields": report.unmapped_fields,
        "endpoint_payload_observation_coverage": report.endpoint_payload_observation_coverage,
    }


def _configuration_key(test: CrashTest) -> str | None:
    if test.test_configuration_key:
        return test.test_configuration_key
    return test.test_configuration


def _counter_rows(values: Iterable[object]) -> list[dict[str, object]]:
    counter = Counter(str(value) for value in values if value)
    return [
        {"value": value, "count": count}
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _participant_patterns(
    participants: list[TestParticipant], test_no_by_id: dict[int, int]
) -> list[dict[str, object]]:
    grouped: dict[int, Counter[str]] = defaultdict(Counter)
    for participant in participants:
        test_no = test_no_by_id.get(participant.test_id)
        if test_no is None:
            continue
        grouped[test_no][participant.participant_kind] += 1
    return [
        {
            "test_no": test_no,
            "participant_kinds": [
                {"participant_kind": kind, "count": count}
                for kind, count in sorted(counts.items())
            ],
        }
        for test_no, counts in sorted(grouped.items())
    ]


def _empty_endpoints(payloads: list[SourcePayload]) -> list[dict[str, object]]:
    return [
        {
            "test_no": payload.test_no,
            "endpoint_name": payload.endpoint_name,
            "http_status": payload.http_status,
            "api_status": payload.api_status,
        }
        for payload in sorted(payloads, key=lambda item: (item.test_no or 0, item.endpoint_name))
        if payload.count_returned == 0
    ]


def _media_asset_kinds(
    assets: list[MediaAsset], test_no_by_id: dict[int, int]
) -> list[dict[str, object]]:
    counter: Counter[tuple[int, str]] = Counter()
    for asset in assets:
        test_no = test_no_by_id.get(asset.test_id)
        if test_no is not None:
            counter[(test_no, asset.asset_kind)] += 1
    return [
        {"test_no": test_no, "asset_kind": asset_kind, "count": count}
        for (test_no, asset_kind), count in sorted(counter.items())
    ]


def _vehicle_duplicates(vehicles: list[Vehicle]) -> list[dict[str, object]]:
    return _duplicate_rows(
        vehicles,
        lambda row: (row.test_no, row.source_vehicle_no),
        lambda row: row.source_endpoint_name,
        lambda key, rows, endpoints: {
            "test_no": key[0],
            "source_vehicle_no": key[1],
            "count": len(rows),
            "source_endpoints": endpoints,
        },
    )


def _participant_duplicates(
    participants: list[TestParticipant], test_no_by_id: dict[int, int]
) -> list[dict[str, object]]:
    return _duplicate_rows(
        participants,
        lambda row: (
            test_no_by_id.get(row.test_id),
            row.participant_kind,
            row.source_vehicle_no,
            row.display_name,
        ),
        lambda row: row.source_endpoint_name,
        lambda key, rows, endpoints: {
            "test_no": key[0],
            "participant_kind": key[1],
            "source_vehicle_no": key[2],
            "display_name": key[3],
            "count": len(rows),
            "source_endpoints": endpoints,
        },
    )


def _barrier_duplicates(barriers: list[Barrier]) -> list[dict[str, object]]:
    return _duplicate_rows(
        barriers,
        lambda row: (row.test_no, row.source_barrier_no, row.rigidity, row.shape, row.angle_raw),
        lambda row: row.source_endpoint_name,
        lambda key, rows, endpoints: {
            "test_no": key[0],
            "source_barrier_no": key[1],
            "rigidity": key[2],
            "shape": key[3],
            "angle_raw": key[4],
            "count": len(rows),
            "source_endpoints": endpoints,
        },
    )


def _duplicate_rows(
    rows: list[Any],
    key_func: Any,
    endpoint_func: Any,
    row_func: Any,
) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[Any]] = defaultdict(list)
    for row in rows:
        key = key_func(row)
        grouped[key].append(row)
    duplicates = []
    for key, group in grouped.items():
        if len(group) <= 1:
            continue
        endpoints = sorted(
            {endpoint for endpoint in (endpoint_func(row) for row in group) if endpoint}
        )
        duplicates.append(row_func(key, group, endpoints))
    return duplicates


def _unmapped_fields(fields: list[SourceFieldCatalog]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str | None, str, str], dict[str, object]] = {}
    for field in fields:
        if field.mapping_status != "unmapped":
            continue
        key = (
            field.endpoint_name,
            field.section_name,
            normalize_field_path(field.field_path),
            field.observed_type,
        )
        if key not in grouped:
            grouped[key] = {
                "endpoint_name": field.endpoint_name,
                "section_name": field.section_name,
                "field_path": normalize_field_path(field.field_path),
                "observed_type": field.observed_type,
                "seen_count": 0,
                "non_null_count": 0,
            }
        grouped[key]["seen_count"] = _as_int(grouped[key]["seen_count"]) + field.seen_count
        grouped[key]["non_null_count"] = (
            _as_int(grouped[key]["non_null_count"]) + field.non_null_count
        )
    return sorted(
        grouped.values(),
        key=lambda row: (
            -_as_int(row["seen_count"]),
            str(row["endpoint_name"]),
            str(row["field_path"]),
        ),
    )


def _endpoint_coverage(
    payloads: list[SourcePayload], observations: list[SourcePayloadObservation]
) -> list[dict[str, object]]:
    payload_by_id = {payload.id: payload for payload in payloads}
    payload_counts: Counter[str] = Counter(payload.endpoint_name for payload in payloads)
    observation_counts: Counter[str] = Counter()
    for observation in observations:
        payload = payload_by_id.get(observation.source_payload_id)
        if payload is not None:
            observation_counts[payload.endpoint_name] += 1
    endpoints = sorted(set(payload_counts) | set(observation_counts))
    return [
        {
            "endpoint_name": endpoint,
            "source_payloads": payload_counts[endpoint],
            "source_payload_observations": observation_counts[endpoint],
        }
        for endpoint in endpoints
    ]


def _as_int(value: object) -> int:
    return value if isinstance(value, int) else 0
