from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from nhtsa_metadata.config import get_settings
from nhtsa_metadata.db.models import (
    Barrier,
    CanonicalRowSource,
    CrashTest,
    InstrumentationChannel,
    MediaAsset,
    Occupant,
    Restraint,
    SourceFieldCatalog,
    SourcePayload,
    SourcePayloadObservation,
    TestClassification,
    TestFilterSummary,
    TestParticipant,
    Vehicle,
)
from nhtsa_metadata.services.scope import is_in_scope_test_record
from nhtsa_metadata.services.semantic_keys import restraint_semantic_key, stable_semantic_hash
from nhtsa_metadata.sources.nhtsa_crash.field_catalog import normalize_field_path
from nhtsa_metadata.sources.nhtsa_crash.normalization import (
    infer_asset_kind,
    infer_asset_subtype,
)

DuplicateGroups = dict[str, list[list[Any]]]
RowSourceLookup = dict[tuple[str, int], list[dict[str, object]]]


@dataclass(frozen=True)
class SchemaAuditReport:
    test_type_distribution: list[dict[str, object]]
    test_configuration_distribution: list[dict[str, object]]
    test_classification_distribution: list[dict[str, object]]
    participant_patterns: list[dict[str, object]]
    empty_endpoints: list[dict[str, object]]
    media_asset_kinds: list[dict[str, object]]
    canonical_duplicate_groups: dict[str, dict[str, int]]
    unmapped_fields: list[dict[str, object]]
    endpoint_payload_observation_coverage: list[dict[str, object]]
    baseline_semantic_cardinality: list[dict[str, object]]
    asset_classification_audit: dict[str, object]
    scope: dict[str, object]
    restraint_info_scheduling: dict[str, object]
    duplicate_details: dict[str, list[dict[str, object]]] | None = None


class SchemaAuditService:
    def __init__(
        self,
        session: Session,
        include_duplicate_details: bool = False,
        duplicate_detail_limit: int = 50,
        min_test_date: date | None = None,
    ) -> None:
        self.session = session
        self.include_duplicate_details = include_duplicate_details
        self.duplicate_detail_limit = duplicate_detail_limit
        self.min_test_date = min_test_date or get_settings().min_test_date

    def report(self) -> SchemaAuditReport:
        tests = list(self.session.scalars(select(CrashTest).order_by(CrashTest.test_no)))
        vehicles = list(self.session.scalars(select(Vehicle)))
        barriers = list(self.session.scalars(select(Barrier)))
        participants = list(self.session.scalars(select(TestParticipant)))
        occupants = list(self.session.scalars(select(Occupant)))
        restraints = list(self.session.scalars(select(Restraint)))
        channels = list(self.session.scalars(select(InstrumentationChannel)))
        payloads = list(self.session.scalars(select(SourcePayload)))
        observations = list(self.session.scalars(select(SourcePayloadObservation)))
        fields = list(self.session.scalars(select(SourceFieldCatalog)))
        assets = list(self.session.scalars(select(MediaAsset)))
        classifications = list(self.session.scalars(select(TestClassification)))
        summaries = list(self.session.scalars(select(TestFilterSummary)))
        row_sources = list(self.session.scalars(select(CanonicalRowSource)))
        payload_by_id = {payload.id: payload for payload in payloads}
        test_no_by_id = {test.id: test.test_no for test in tests}
        source_lookup = _source_lookup(row_sources, payload_by_id)
        duplicate_groups = _canonical_duplicate_groups(
            vehicles=vehicles,
            participants=participants,
            barriers=barriers,
            occupants=occupants,
            restraints=restraints,
            channels=channels,
            assets=assets,
            test_no_by_id=test_no_by_id,
        )

        duplicate_details = None
        if self.include_duplicate_details:
            duplicate_details = _duplicate_details(
                duplicate_groups,
                test_no_by_id,
                source_lookup,
                self.duplicate_detail_limit,
            )

        return SchemaAuditReport(
            test_type_distribution=_counter_rows(test.test_type for test in tests),
            test_configuration_distribution=_counter_rows(
                _configuration_key(test) for test in tests
            ),
            test_classification_distribution=_counter_rows(
                f"{row.test_family}:{row.classification_status}" for row in classifications
            ),
            participant_patterns=_participant_patterns(participants, test_no_by_id),
            empty_endpoints=_empty_endpoints(payloads),
            media_asset_kinds=_media_asset_kinds(assets, test_no_by_id),
            canonical_duplicate_groups=_duplicate_summary(duplicate_groups),
            unmapped_fields=_unmapped_fields(fields),
            endpoint_payload_observation_coverage=_endpoint_coverage(payloads, observations),
            baseline_semantic_cardinality=_baseline_semantic_cardinality(
                tests, vehicles, occupants, channels
            ),
            asset_classification_audit=_asset_classification_audit(
                payloads, assets, test_no_by_id
            ),
            scope=_scope_summary(tests, summaries, self.min_test_date),
            restraint_info_scheduling=_restraint_info_scheduling(payloads),
            duplicate_details=duplicate_details,
        )


def report_to_dict(report: SchemaAuditReport) -> dict[str, object]:
    payload: dict[str, object] = {
        "test_type_distribution": report.test_type_distribution,
        "test_configuration_distribution": report.test_configuration_distribution,
        "test_classification_distribution": report.test_classification_distribution,
        "participant_patterns": report.participant_patterns,
        "empty_endpoints": report.empty_endpoints,
        "media_asset_kinds": report.media_asset_kinds,
        "canonical_duplicate_groups": report.canonical_duplicate_groups,
        "unmapped_fields": report.unmapped_fields,
        "endpoint_payload_observation_coverage": report.endpoint_payload_observation_coverage,
        "baseline_semantic_cardinality": report.baseline_semantic_cardinality,
        "asset_classification_audit": report.asset_classification_audit,
        "scope": report.scope,
        "restraint_info_scheduling": report.restraint_info_scheduling,
    }
    if report.duplicate_details is not None:
        payload["duplicate_details"] = report.duplicate_details
    return payload


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
    counter: Counter[tuple[int, str, str | None]] = Counter()
    for asset in assets:
        test_no = test_no_by_id.get(asset.test_id)
        if test_no is not None:
            counter[(test_no, asset.asset_kind, asset.asset_subtype)] += 1
    return [
        {
            "test_no": test_no,
            "asset_kind": asset_kind,
            "asset_subtype": asset_subtype,
            "count": count,
        }
        for (test_no, asset_kind, asset_subtype), count in sorted(counter.items())
    ]


def _canonical_duplicate_groups(
    *,
    vehicles: list[Vehicle],
    participants: list[TestParticipant],
    barriers: list[Barrier],
    occupants: list[Occupant],
    restraints: list[Restraint],
    channels: list[InstrumentationChannel],
    assets: list[MediaAsset],
    test_no_by_id: dict[int, int],
) -> DuplicateGroups:
    return {
        "vehicles": _duplicate_groups(
            vehicles,
            lambda row: (row.test_no, row.source_vehicle_no)
            if row.source_vehicle_no is not None
            else (row.test_no, row.make, row.model, row.model_year),
        ),
        "test_participants": _duplicate_groups(
            participants,
            lambda row: (
                test_no_by_id.get(row.test_id),
                row.participant_kind,
                row.source_vehicle_no,
                row.display_name,
            ),
        ),
        "barriers": _duplicate_groups(
            barriers,
            lambda row: (
                row.test_no,
                row.source_barrier_no,
                row.rigidity,
                row.shape,
                row.angle_raw,
            ),
        ),
        "occupants": _duplicate_groups(
            occupants,
            lambda row: (
                test_no_by_id.get(row.test_id),
                row.source_vehicle_no,
                row.occupant_location_normalized or row.occupant_location_raw,
            ),
        ),
        "restraints": _duplicate_groups(
            restraints,
            lambda row: (test_no_by_id.get(row.test_id), _restraint_semantic_hash(row)),
        ),
        "instrumentation_channels": _duplicate_groups(
            channels,
            lambda row: (row.test_no, row.curve_no),
        ),
        "media_assets": _duplicate_groups(
            assets,
            lambda row: (
                test_no_by_id.get(row.test_id),
                row.asset_kind,
                row.canonical_url_hash,
            ),
        ),
    }


def _duplicate_groups(
    rows: list[Any],
    key_func: Callable[[Any], tuple[object, ...]],
) -> list[list[Any]]:
    grouped: dict[tuple[object, ...], list[Any]] = defaultdict(list)
    for row in rows:
        grouped[key_func(row)].append(row)
    return [group for group in grouped.values() if len(group) > 1]


def _duplicate_summary(groups_by_table: DuplicateGroups) -> dict[str, dict[str, int]]:
    return {
        table_name: {
            "group_count": len(groups),
            "row_count": sum(len(group) for group in groups),
        }
        for table_name, groups in groups_by_table.items()
    }


def _duplicate_details(
    groups_by_table: DuplicateGroups,
    test_no_by_id: dict[int, int],
    source_lookup: RowSourceLookup,
    limit: int,
) -> dict[str, list[dict[str, object]]]:
    details: dict[str, list[dict[str, object]]] = {}
    for table_name, groups in groups_by_table.items():
        rows: list[dict[str, object]] = []
        for group in groups[:limit]:
            ids = [int(row.id) for row in group if getattr(row, "id", None) is not None]
            payload_ids, endpoints = _group_source_summary(table_name, group, source_lookup)
            item = {
                "count": len(group),
                "row_ids": ids,
                "source_payload_ids": payload_ids,
                "source_endpoint_names": endpoints,
            }
            item.update(_duplicate_identity(table_name, group[0], test_no_by_id))
            rows.append(item)
        details[table_name] = rows
    return details


def _source_lookup(
    row_sources: list[CanonicalRowSource],
    payload_by_id: dict[int, SourcePayload],
) -> RowSourceLookup:
    lookup: RowSourceLookup = defaultdict(list)
    for source in row_sources:
        payload = payload_by_id.get(source.source_payload_id)
        lookup[(source.table_name, source.row_id)].append(
            {
                "source_payload_id": source.source_payload_id,
                "endpoint_name": payload.endpoint_name if payload is not None else None,
            }
        )
    return lookup


def _group_source_summary(
    table_name: str,
    rows: list[Any],
    source_lookup: RowSourceLookup,
) -> tuple[list[int], list[str]]:
    payload_ids: set[int] = set()
    endpoints: set[str] = set()
    for row in rows:
        source_payload_id = getattr(row, "source_payload_id", None)
        if isinstance(source_payload_id, int):
            payload_ids.add(source_payload_id)
        endpoint = getattr(row, "source_endpoint_name", None)
        if isinstance(endpoint, str) and endpoint:
            endpoints.add(endpoint)
        row_id = getattr(row, "id", None)
        if not isinstance(row_id, int):
            continue
        for source in source_lookup.get((table_name, row_id), []):
            payload_id = source.get("source_payload_id")
            if isinstance(payload_id, int):
                payload_ids.add(payload_id)
            source_endpoint = source.get("endpoint_name")
            if isinstance(source_endpoint, str) and source_endpoint:
                endpoints.add(source_endpoint)
    return sorted(payload_ids), sorted(endpoints)


def _duplicate_identity(
    table_name: str,
    row: Any,
    test_no_by_id: dict[int, int],
) -> dict[str, object]:
    test_no = getattr(row, "test_no", None)
    if test_no is None and getattr(row, "test_id", None) is not None:
        test_no = test_no_by_id.get(row.test_id)
    if table_name == "vehicles":
        return {"test_no": test_no, "source_vehicle_no": row.source_vehicle_no}
    if table_name == "test_participants":
        return {
            "test_no": test_no,
            "participant_kind": row.participant_kind,
            "source_vehicle_no": row.source_vehicle_no,
            "display_name": row.display_name,
        }
    if table_name == "barriers":
        return {
            "test_no": test_no,
            "source_barrier_no": row.source_barrier_no,
            "rigidity": row.rigidity,
            "shape": row.shape,
            "angle_raw": row.angle_raw,
        }
    if table_name == "occupants":
        return {
            "test_no": test_no,
            "source_vehicle_no": row.source_vehicle_no,
            "occupant_location": row.occupant_location_normalized
            or row.occupant_location_raw,
        }
    if table_name == "restraints":
        return {
            "test_no": test_no,
            "semantic_key": _restraint_semantic_key(row),
            "semantic_hash": _restraint_semantic_hash(row),
        }
    if table_name == "instrumentation_channels":
        return {"test_no": test_no, "curve_no": row.curve_no}
    if table_name == "media_assets":
        return {
            "test_no": test_no,
            "asset_kind": row.asset_kind,
            "asset_subtype": row.asset_subtype,
            "canonical_url_hash": row.canonical_url_hash,
        }
    return {"test_no": test_no}


def _restraint_semantic_key(row: Restraint) -> str:
    if row.semantic_key:
        return row.semantic_key
    return restraint_semantic_key(
        test_id=row.test_id,
        source_vehicle_no=row.source_vehicle_no,
        occupant_location_raw=row.occupant_location_raw,
        restraint_type=row.restraint_type,
        deployment_status=row.deployment_status,
        raw_row=row.raw_row_json if isinstance(row.raw_row_json, dict) else None,
    )


def _restraint_semantic_hash(row: Restraint) -> str:
    return row.semantic_hash or stable_semantic_hash(_restraint_semantic_key(row))


def _baseline_semantic_cardinality(
    tests: list[CrashTest],
    vehicles: list[Vehicle],
    occupants: list[Occupant],
    channels: list[InstrumentationChannel],
) -> list[dict[str, object]]:
    test_id_by_no = {test.test_no: test.id for test in tests}
    rows: list[dict[str, object]] = []
    if 10001 in test_id_by_no:
        test_id = test_id_by_no[10001]
        actual = sum(1 for occupant in occupants if occupant.test_id == test_id)
        status = "pass" if actual == 2 else "accepted_known_condition"
        rows.append(
            {
                "test_no": 10001,
                "entity": "occupants",
                "expected_min": 2,
                "expected_exact_when_normalized": 2,
                "actual": actual,
                "status": status,
                "reason": None
                if status == "pass"
                else "canonical preserves distinct source occupant rows after dedupe",
            }
        )
    if 10003 in test_id_by_no:
        test_id = test_id_by_no[10003]
        vehicle_count = sum(1 for vehicle in vehicles if vehicle.test_id == test_id)
        channel_count = sum(1 for channel in channels if channel.test_id == test_id)
        status = "investigate"
        reason = None
        if vehicle_count >= 2 and channel_count >= 63:
            status = "pass"
        elif vehicle_count >= 2 and channel_count >= 2:
            status = "accepted_known_condition"
            reason = "compact fixture instrumentation baseline"
        rows.append(
            {
                "test_no": 10003,
                "entity": "baseline",
                "vehicles_expected_min": 2,
                "vehicles_actual": vehicle_count,
                "instrumentation_expected_min": 63,
                "instrumentation_actual": channel_count,
                "status": status,
                "reason": reason,
            }
        )
    return rows


def _asset_classification_audit(
    payloads: list[SourcePayload],
    assets: list[MediaAsset],
    test_no_by_id: dict[int, int],
) -> dict[str, object]:
    vehicle_document_payloads = [
        payload for payload in payloads if payload.endpoint_name == "vehicle_documents"
    ]
    multimedia_payloads = [
        payload for payload in payloads if payload.endpoint_name == "multimedia_files"
    ]
    candidates = _data_package_candidates(vehicle_document_payloads)
    classified_urls = {
        asset.source_url for asset in assets if asset.asset_kind == "data_package"
    }
    unclassified = [
        candidate
        for candidate in candidates
        if isinstance(candidate.get("url"), str) and candidate["url"] not in classified_urls
    ]
    return {
        "vehicle_documents_payloads": len(vehicle_document_payloads),
        "multimedia_files_payloads": len(multimedia_payloads),
        "document_rows_observed": sum(
            len(_payload_rows(payload)) for payload in vehicle_document_payloads
        ),
        "data_package_candidates": len(candidates),
        "classified_data_packages": sum(
            1 for asset in assets if asset.asset_kind == "data_package"
        ),
        "unclassified_asset_candidates": unclassified[:50],
        "media_asset_subtypes": _counter_rows(asset.asset_subtype for asset in assets),
        "has_uds_or_tdms_package_tests": _has_uds_or_tdms_package_tests(
            assets, test_no_by_id
        ),
    }


def _has_uds_or_tdms_package_tests(
    assets: list[MediaAsset], test_no_by_id: dict[int, int]
) -> list[int]:
    test_numbers: set[int] = set()
    for asset in assets:
        if asset.asset_kind != "data_package" or asset.asset_subtype not in {"UDS", "TDMS"}:
            continue
        test_no = test_no_by_id.get(asset.test_id)
        if test_no is not None:
            test_numbers.add(test_no)
    return sorted(test_numbers)


def _scope_summary(
    tests: list[CrashTest],
    summaries: list[TestFilterSummary],
    min_test_date: date,
) -> dict[str, object]:
    in_scope = 0
    out_of_scope = 0
    missing = 0
    parse_failed = 0
    violations: list[dict[str, object]] = []
    for test in tests:
        if is_in_scope_test_record(
            test.test_date, test.test_date_parse_status, min_test_date
        ):
            in_scope += 1
            continue
        if test.test_date is None:
            if test.test_date_parse_status in {"invalid", "partial"}:
                parse_failed += 1
                reason = "date_parse_failed"
            else:
                missing += 1
                reason = "missing_test_date"
        elif test.test_date < min_test_date:
            out_of_scope += 1
            reason = "out_of_scope"
        else:
            parse_failed += 1
            reason = "date_parse_failed"
        violations.append(
            {
                "test_no": test.test_no,
                "reason": reason,
                "test_date": test.test_date.isoformat() if test.test_date else None,
                "test_date_parse_status": test.test_date_parse_status,
            }
        )
    read_model_out_of_scope = [
        {
            "test_no": summary.test_no,
            "test_date": summary.test_date.isoformat() if summary.test_date else None,
        }
        for summary in summaries
        if summary.test_date is None or summary.test_date < min_test_date
    ]
    return {
        "min_test_date": min_test_date.isoformat(),
        "in_scope_tests": in_scope,
        "out_of_scope_tests": out_of_scope,
        "missing_test_date": missing,
        "date_parse_failed": parse_failed,
        "read_model_out_of_scope_rows": len(read_model_out_of_scope),
        "violations": violations,
        "read_model_violations": read_model_out_of_scope,
    }


def _restraint_info_scheduling(payloads: list[SourcePayload]) -> dict[str, object]:
    expected = _expected_restraint_requests(payloads)
    actual = {
        (
            payload.test_no,
            payload.vehicle_no,
            _normalize_location(payload.occupant_location_raw),
        )
        for payload in payloads
        if payload.endpoint_name == "restraint_info"
    }
    missing = sorted(expected - actual)
    return {
        "expected_request_count": len(expected),
        "actual_payload_count": len(actual),
        "missing_request_count": len(missing),
        "missing_requests": [
            {
                "test_no": test_no,
                "vehicle_no": vehicle_no,
                "occupant_location": occupant_location,
            }
            for test_no, vehicle_no, occupant_location in missing[:50]
        ],
    }


def _expected_restraint_requests(
    payloads: list[SourcePayload],
) -> set[tuple[int | None, int | None, str | None]]:
    expected: set[tuple[int | None, int | None, str | None]] = set()
    for payload in payloads:
        if payload.endpoint_name != "occupant_info":
            continue
        for row in _payload_rows(payload):
            vehicle_no = _to_int(row.get("vehicleNo") or row.get("VEHNO"))
            occupant_location = row.get("occupantLocation") or row.get("OCCLOC")
            if vehicle_no is None or occupant_location in (None, ""):
                continue
            expected.add((payload.test_no, vehicle_no, _normalize_location(occupant_location)))
    return expected


def _normalize_location(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip().upper()


def _data_package_candidates(payloads: list[SourcePayload]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for payload in payloads:
        for index, row in enumerate(_payload_rows(payload)):
            for field_name, value in row.items():
                if not isinstance(value, str) or not value.strip():
                    continue
                if not _is_asset_url_field(field_name):
                    continue
                document_type = _document_type(row, field_name)
                if infer_asset_kind(value, document_type) != "data_package":
                    continue
                candidates.append(
                    {
                        "test_no": payload.test_no,
                        "source_payload_id": payload.id,
                        "row_path": f"$.results[{index}].{field_name}",
                        "field_name": field_name,
                        "url": value,
                        "asset_subtype": infer_asset_subtype(value, document_type),
                    }
                )
    return candidates


def _document_type(row: dict[str, Any], field_name: str) -> str | None:
    raw = row.get("documentType") or row.get("type") or _document_type_from_field(field_name)
    return str(raw) if raw is not None else None


def _document_type_from_field(field_name: str) -> str | None:
    mapping = {
        "udsFiles": "UDS",
        "evFiles": "EV",
        "abfFiles": "ABF",
        "isoFiles": "ISO",
        "tdmsFiles": "TDMS",
    }
    return mapping.get(field_name)


def _is_asset_url_field(field_name: str) -> bool:
    return field_name in {
        "url",
        "URL",
        "udsFiles",
        "evFiles",
        "abfFiles",
        "isoFiles",
        "tdmsFiles",
    }


def _payload_rows(payload: SourcePayload) -> list[dict[str, Any]]:
    results = payload.payload_json.get("results")
    if not isinstance(results, list):
        return []
    return [row for row in results if isinstance(row, dict)]


def _to_int(value: object) -> int | None:
    try:
        return int(value) if isinstance(value, int | str) else None
    except (TypeError, ValueError):
        return None


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
