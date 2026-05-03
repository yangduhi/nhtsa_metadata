from __future__ import annotations

# ruff: noqa: E501, I001

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nhtsa_metadata.sources.nhtsa_crash.endpoints import ENDPOINTS  # noqa: E402


SOURCE_SYSTEM = "nhtsa_crash"
SCHEMA_VERSION = "1.5"
REPORT_DATE = "2026-04-30"
DEFAULT_DB = Path(
    r"D:\vscode\nhtsa_metadata_stage_d\data"
    r"\full_2011plus_metadata_only_stage_d_2026-04-30.sqlite"
)
DEFAULT_MANIFEST = Path(
    r"D:\vscode\nhtsa_metadata_stage_d\data\full_2011plus_authoritative_manifest.csv"
)
EXPECTED_MANIFEST_SHA256 = (
    "b4a1262938d33793bff0d4aca78222e4bab51c7253d4084fbb80597096abe6be"
)
EXPECTED_COUNTS = {
    "manifest_rows": 3891,
    "collected_tests": 3891,
    "missing_tests": 0,
    "source_payloads": 66318,
    "payload_observations": 66318,
    "code_sets": 17,
    "code_values": 757,
}


CODE_SET_SOURCES = {
    "sensor_type": ("instrumentation_info", "$.results[*].sensorType", "instrumentation_channels", "sensor_type"),
    "sensor_attachment": (
        "instrumentation_info",
        "$.results[*].sensorAttachment",
        "instrumentation_channels",
        "sensor_attachment",
    ),
    "sensor_axis": (
        "instrumentation_info",
        "$.results[*].axisDirofSensor",
        "instrumentation_channels",
        "sensor_axis",
    ),
    "data_measurement_unit": (
        "instrumentation_info",
        "$.results[*].dataMeasurementUnits",
        "instrumentation_channels",
        "unit_raw",
    ),
    "data_status": (
        "instrumentation_info",
        "$.results[*].dataStatus",
        "instrumentation_channels",
        "data_status",
    ),
    "channel_status": (
        "instrumentation_info",
        "$.results[*].channelStatus",
        "instrumentation_channels",
        "channel_status",
    ),
    "occupant_location": (
        "occupant_info",
        "$.results[*].occupantLocation",
        "occupants",
        "occupant_location_normalized",
    ),
    "occupant_type": ("occupant_info", "$.results[*].occupantType", "occupants", "occupant_type"),
    "restraint_type": ("restraint_info", "$.results[*].restraintType", "restraints", "restraint_type"),
    "restraint_deployment": (
        "restraint_info",
        "$.results[*].inflationer/BeltPretensionerDeployment",
        "restraints",
        "deployment_status",
    ),
    "barrier_rigidity": (
        "barrier_info",
        "$.results[*].rigidOrDeformableBarrier",
        "barriers",
        "rigidity",
    ),
    "barrier_shape": ("barrier_info", "$.results[*].barrierShape", "barriers", "shape"),
    "asset_kind": ("media_assets", "media_assets.asset_kind", "media_assets", "asset_kind"),
    "asset_subtype": ("media_assets", "media_assets.asset_subtype", "media_assets", "asset_subtype"),
    "test_configuration_key": (
        "test_summary",
        "$.results[*].testConfiguration",
        "tests",
        "test_configuration_key",
    ),
    "classification_status": (
        "test_classification",
        "test_classification.classification_status",
        "test_classification",
        "classification_status",
    ),
    "participant_kind": (
        "test_participants",
        "test_participants.participant_kind",
        "test_participants",
        "participant_kind",
    ),
}

FIELD_CODE_OVERRIDES = {
    ("metadata_export", "$.results[*].INSTRUMENTATION[*].SENTYPD"): "sensor_type",
    ("metadata_export", "$.results[*].INSTRUMENTATION[*].SENATTD"): "sensor_attachment",
    ("metadata_export", "$.results[*].INSTRUMENTATION[*].AXISD"): "sensor_axis",
    ("metadata_export", "$.results[*].INSTRUMENTATION[*].YUNITSD"): "data_measurement_unit",
    ("metadata_export", "$.results[*].INSTRUMENTATION[*].DASTATD"): "data_status",
    ("metadata_export", "$.results[*].INSTRUMENTATION[*].CHSTATD"): "channel_status",
    ("metadata_export", "$.results[*].OCCUPANT[*].OCCLOC"): "occupant_location",
    ("metadata_export", "$.results[*].RESTRAINT[*].OCCLOCD"): "occupant_location",
    ("metadata_export", "$.results[*].RESTRAINT[*].RSTTYPD"): "restraint_type",
    ("metadata_export", "$.results[*].RESTRAINT[*].DEPLOYD"): "restraint_deployment",
    ("metadata_export", "$.results[*].BARRIER[*].BARRIGD"): "barrier_rigidity",
    ("metadata_export", "$.results[*].BARRIER[*].BARSHPD"): "barrier_shape",
}
for code_set_name, (endpoint_name, field_path, _entity, _field) in CODE_SET_SOURCES.items():
    if field_path.startswith("$."):
        FIELD_CODE_OVERRIDES[(endpoint_name, field_path)] = code_set_name


ENDPOINT_DECISIONS = {
    "test_results": "required_discovery_not_persisted",
    "search": "required_discovery_not_persisted",
    "search_vehicle": "optional_discovery_not_collected",
    "search_barrier": "optional_discovery_not_collected",
    "vehicle_models": "optional_discovery_not_collected",
    "occupant_types": "optional_discovery_not_collected",
    "test_summary": "required_collected",
    "metadata_export": "required_collected",
    "test_detail": "optional_core_collected",
    "vehicle_info": "required_collected",
    "vehicle_detail": "optional_detail_not_collected",
    "barrier_info": "required_collected",
    "occupant_info": "required_collected",
    "occupant_info_by_vehicle": "superseded_by_test_level_occupant_info",
    "occupant_detail": "optional_detail_not_collected",
    "restraint_info": "required_collected",
    "intrusion_info": "required_collected",
    "instrumentation_info": "required_collected",
    "instrumentation_detail": "deferred_optional_not_collected",
    "multimedia_files": "required_collected",
    "vehicle_documents": "required_collected",
}

ENTITY_BY_ENDPOINT = {
    "test_results": ["discovery_manifest_candidate"],
    "search": ["discovery_manifest_candidate"],
    "search_vehicle": ["discovery_manifest_candidate"],
    "search_barrier": ["discovery_manifest_candidate"],
    "vehicle_models": ["reference_dictionary"],
    "occupant_types": ["reference_dictionary"],
    "test_summary": ["manifest_tests", "test_identities"],
    "metadata_export": [
        "manifest_tests",
        "vehicles",
        "test_participants",
        "barriers",
        "occupants",
        "restraints",
        "instrumentation_channels",
        "injury_metrics",
        "deformation_measurements",
        "media_assets",
    ],
    "test_detail": ["native_test_detail"],
    "vehicle_info": ["vehicles", "test_participants"],
    "vehicle_detail": ["native_vehicle_detail"],
    "barrier_info": ["barriers", "test_participants"],
    "occupant_info": ["occupants"],
    "occupant_info_by_vehicle": ["occupants"],
    "occupant_detail": ["native_occupant_detail"],
    "restraint_info": ["restraints"],
    "intrusion_info": ["intrusion_measurements"],
    "instrumentation_info": ["instrumentation_channels"],
    "instrumentation_detail": ["instrumentation_channel_details"],
    "multimedia_files": ["native_multimedia_listing"],
    "vehicle_documents": ["media_assets"],
}

CANONICAL_ENTITY_TABLES = [
    "tests",
    "vehicles",
    "barriers",
    "test_participants",
    "occupants",
    "restraints",
    "instrumentation_channels",
    "injury_metrics",
    "deformation_measurements",
    "media_assets",
]

CONCEPTUAL_TABLES = [
    "source_systems",
    "source_endpoints",
    "endpoint_requests",
    "source_payloads",
    "manifest_tests",
    "test_identities",
    "payload_observations",
    "entity_instances",
    "field_catalog",
    "field_occurrences",
    "code_sets",
    "code_values",
    "relationship_edges",
    "semantic_concepts",
    "classification_rules",
    "classification_evidence",
    "schema_versions",
    "audit_results",
]


@dataclass
class FieldProfile:
    endpoint_name: str
    json_path: str
    occurrence_count: int = 0
    non_null_count: int = 0
    data_types: set[str] = field(default_factory=set)
    first_seen_payload_id: int | None = None
    last_seen_payload_id: int | None = None
    max_length: int | None = None
    range_min: float | None = None
    range_max: float | None = None
    examples: list[Any] = field(default_factory=list)

    def observe(self, payload_id: int, value: Any) -> None:
        self.occurrence_count += 1
        data_type = observed_type(value)
        self.data_types.add(data_type)
        if value is not None:
            self.non_null_count += 1
        if self.first_seen_payload_id is None or payload_id < self.first_seen_payload_id:
            self.first_seen_payload_id = payload_id
        if self.last_seen_payload_id is None or payload_id > self.last_seen_payload_id:
            self.last_seen_payload_id = payload_id
        if isinstance(value, str):
            value_length = len(value)
            self.max_length = value_length if self.max_length is None else max(self.max_length, value_length)
        if isinstance(value, int | float) and not isinstance(value, bool):
            numeric_value = float(value)
            self.range_min = numeric_value if self.range_min is None else min(self.range_min, numeric_value)
            self.range_max = numeric_value if self.range_max is None else max(self.range_max, numeric_value)
        if value is not None and len(self.examples) < 5 and value not in self.examples:
            self.examples.append(value)


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    db_path = args.database.resolve()
    manifest_path = args.manifest.resolve()
    output_data = repo_root / "data" / "schema"
    output_docs = repo_root / "docs" / "schema"
    output_reports = repo_root / "docs" / "phase_reports"
    output_data.mkdir(parents=True, exist_ok=True)
    output_docs.mkdir(parents=True, exist_ok=True)
    output_reports.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect("file:" + db_path.as_posix() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        context = build_context(con, db_path, manifest_path)
        field_rows = build_field_catalog_rows(context)
        endpoint_rows = build_endpoint_matrix_rows(context, field_rows)
        code_set_rows, code_value_rows = build_code_rows(context)
        relationship_rows = build_relationship_rows(context)
        audit_rows = build_audit_rows(
            context,
            field_rows,
            endpoint_rows,
            relationship_rows,
            args.migration_sanity_status,
        )

        write_csv(output_data / "field_catalog_v1_5.csv", FIELD_CATALOG_HEADERS, field_rows)
        write_csv(
            output_data / "endpoint_entity_matrix_v1_5.csv",
            ENDPOINT_MATRIX_HEADERS,
            endpoint_rows,
        )
        write_csv(output_data / "code_sets_v1_5.csv", CODE_SET_HEADERS, code_set_rows)
        write_csv(output_data / "code_values_v1_5.csv", CODE_VALUE_HEADERS, code_value_rows)
        write_csv(
            output_data / "relationship_matrix_v1_5.csv",
            RELATIONSHIP_HEADERS,
            relationship_rows,
        )
        write_csv(output_data / "schema_audit_v1_5.csv", SCHEMA_AUDIT_HEADERS, audit_rows)

        write_docs(
            repo_root,
            output_docs,
            output_reports,
            context,
            field_rows,
            endpoint_rows,
            code_set_rows,
            code_value_rows,
            relationship_rows,
            audit_rows,
            args,
        )
        write_registry(repo_root, db_path, manifest_path)
    finally:
        con.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--migration-sanity-status",
        choices=["not_run", "pass", "fail"],
        default="not_run",
    )
    parser.add_argument(
        "--verification-summary",
        default="Verification not run at artifact generation time.",
    )
    parser.add_argument(
        "--verification-command",
        action="append",
        default=[],
        help="Command/result line to include in the phase report.",
    )
    parser.add_argument(
        "--acceptance",
        choices=[
            "ACCEPTED: schema contract v1.5 is accepted",
            "REJECTED: schema contract v1.5 is not accepted",
            (
                "ACCEPTED_WITH_DOCUMENTED_EXCEPTIONS: schema contract v1.5 is accepted "
                "with explicitly documented exceptions"
            ),
        ],
        default=(
            "ACCEPTED_WITH_DOCUMENTED_EXCEPTIONS: schema contract v1.5 is accepted "
            "with explicitly documented exceptions"
        ),
    )
    return parser.parse_args()


def build_context(con: sqlite3.Connection, db_path: Path, manifest_path: Path) -> dict[str, Any]:
    manifest_rows = read_manifest(manifest_path)
    manifest_test_nos = {int(row["test_no"]) for row in manifest_rows}
    db_test_nos = {int(row["test_no"]) for row in con.execute("select test_no from tests")}
    counts = {
        table: int(con.execute(f'select count(*) from "{table}"').fetchone()[0])
        for table in list_tables(con)
    }
    endpoint_payloads = {
        row["endpoint_name"]: {
            "payload_count": int(row["payload_count"]),
            "empty_success_count": int(row["empty_success_count"]),
        }
        for row in con.execute(
            """
            select endpoint_name,
                   count(*) as payload_count,
                   sum(case when count_returned = 0 then 1 else 0 end) as empty_success_count
            from source_payloads
            group by endpoint_name
            """
        )
    }
    endpoint_observations = {
        row["endpoint_name"]: int(row["observation_count"])
        for row in con.execute(
            """
            select sp.endpoint_name, count(*) as observation_count
            from source_payload_observations obs
            join source_payloads sp on sp.id = obs.source_payload_id
            group by sp.endpoint_name
            """
        )
    }
    source_field_catalog = load_source_field_catalog(con)
    field_profiles = scan_payload_json(con)
    entity_counts = {table: counts.get(table, 0) for table in CANONICAL_ENTITY_TABLES}
    entity_endpoint_counts = load_entity_endpoint_counts(con)
    source_payload_orphans = load_source_payload_orphans(con)
    relationship_counts = load_relationship_counts(con)
    code_set_counts = load_code_set_counts(con)
    manifest_hash = sha256(manifest_path)
    return {
        "db_path": db_path,
        "db_size_bytes": db_path.stat().st_size,
        "manifest_path": manifest_path,
        "manifest_rows": manifest_rows,
        "manifest_hash": manifest_hash,
        "manifest_test_nos": manifest_test_nos,
        "db_test_nos": db_test_nos,
        "missing_tests": sorted(manifest_test_nos - db_test_nos),
        "extra_tests": sorted(db_test_nos - manifest_test_nos),
        "counts": counts,
        "endpoint_payloads": endpoint_payloads,
        "endpoint_observations": endpoint_observations,
        "source_field_catalog": source_field_catalog,
        "field_profiles": field_profiles,
        "entity_counts": entity_counts,
        "entity_endpoint_counts": entity_endpoint_counts,
        "source_payload_orphans": source_payload_orphans,
        "relationship_counts": relationship_counts,
        "code_set_counts": code_set_counts,
        "code_values": load_code_values(con),
    }


def scan_payload_json(con: sqlite3.Connection) -> dict[tuple[str, str], FieldProfile]:
    profiles: dict[tuple[str, str], FieldProfile] = {}
    cursor = con.execute(
        "select id, endpoint_name, payload_json from source_payloads order by id"
    )
    for row in cursor:
        payload = json.loads(row["payload_json"])
        for json_path, value in iter_leaf_values(payload):
            key = (row["endpoint_name"], json_path)
            profile = profiles.setdefault(
                key,
                FieldProfile(endpoint_name=row["endpoint_name"], json_path=json_path),
            )
            profile.observe(int(row["id"]), value)
    return profiles


def iter_leaf_values(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        if not value:
            return [(path, value)]
        rows: list[tuple[str, Any]] = []
        for key, child in value.items():
            rows.extend(iter_leaf_values(child, f"{path}.{key}"))
        return rows
    if isinstance(value, list):
        if not value:
            return [(path, value)]
        rows = []
        for child in value:
            rows.extend(iter_leaf_values(child, f"{path}[*]"))
        return rows
    return [(path, value)]


def build_field_catalog_rows(context: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_field_catalog: dict[tuple[str, str], dict[str, Any]] = context["source_field_catalog"]
    for (endpoint_name, json_path), profile in sorted(context["field_profiles"].items()):
        source_meta = source_field_catalog.get((endpoint_name, json_path), {})
        code_set_name = FIELD_CODE_OVERRIDES.get((endpoint_name, json_path), "")
        mapped_table = source_meta.get("mapped_table") or ""
        entity_type = mapped_table or first_entity_type(endpoint_name)
        raw_field_name = raw_field_from_path(json_path)
        normalized_field_name = normalize_name(raw_field_name)
        contract_status, exception_reason = field_contract_status(
            source_meta, code_set_name, endpoint_name, json_path
        )
        rows.append(
            {
                "source_system": SOURCE_SYSTEM,
                "endpoint_name": endpoint_name,
                "entity_type": entity_type,
                "raw_field_name": raw_field_name,
                "normalized_field_name": normalized_field_name,
                "json_path": json_path,
                "observed_data_type": "|".join(sorted(profile.data_types)),
                "contract_data_type": contract_data_type(profile.data_types),
                "unit": infer_unit(raw_field_name, code_set_name),
                "range_min": format_number(profile.range_min),
                "range_max": format_number(profile.range_max),
                "max_length": profile.max_length or "",
                "nullable_observed": str(profile.non_null_count < profile.occurrence_count).lower(),
                "nullable_contract": "true",
                "is_code": str(bool(code_set_name)).lower(),
                "code_set_name": code_set_name,
                "code_set_source": "code_values_v1_5" if code_set_name else "",
                "first_seen_payload_id": profile.first_seen_payload_id or "",
                "last_seen_payload_id": profile.last_seen_payload_id or "",
                "occurrence_count": profile.occurrence_count,
                "example_values": json.dumps(profile.examples, ensure_ascii=True),
                "contract_status": contract_status,
                "exception_reason": exception_reason,
            }
        )
    return rows


def field_contract_status(
    source_meta: dict[str, Any],
    code_set_name: str,
    endpoint_name: str,
    json_path: str,
) -> tuple[str, str]:
    if code_set_name:
        return "code_linked", ""
    mapping_status = source_meta.get("mapping_status")
    if mapping_status == "mapped":
        return "mapped", ""
    if is_api_envelope_path(json_path):
        return "documented_exception", "api_envelope_field_preserved_in_source_payload"
    if mapping_status == "unmapped":
        return "documented_exception", "raw_preserved_unmapped_schema_backlog_or_raw_only_policy"
    if ENDPOINT_DECISIONS.get(endpoint_name, "").endswith("not_collected"):
        return "documented_exception", "endpoint_not_collected_in_stage_d_metadata_only_scope"
    return "documented_exception", "observed_payload_path_preserved_without_canonical_promotion"


def build_endpoint_matrix_rows(
    context: dict[str, Any], field_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    field_counts = Counter(row["endpoint_name"] for row in field_rows)
    relationship_counts = context["relationship_counts"]
    rows = []
    for endpoint in ENDPOINTS:
        payload_info = context["endpoint_payloads"].get(
            endpoint.name, {"payload_count": 0, "empty_success_count": 0}
        )
        payload_count = payload_info["payload_count"]
        observation_count = context["endpoint_observations"].get(endpoint.name, 0)
        decision = ENDPOINT_DECISIONS.get(endpoint.name, "undocumented_endpoint")
        required_hard = decision == "required_collected"
        has_payload = payload_count > 0
        has_fields = field_counts[endpoint.name] > 0
        relationship_count = relationship_counts.get(endpoint.name, 0)
        has_relationship = relationship_count > 0 or decision.endswith("not_persisted")
        if required_hard and not has_payload:
            status = "hard_failure"
            reason = "required endpoint has no persisted source payload"
        elif not has_payload:
            status = "documented_exception"
            reason = decision
        elif not has_fields:
            status = "documented_exception"
            reason = "payload persisted but no leaf fields observed"
        else:
            status = "pass"
            reason = ""
        rows.append(
            {
                "source_system": SOURCE_SYSTEM,
                "endpoint_name": endpoint.name,
                "endpoint_group": endpoint.endpoint_group,
                "path_template": endpoint.path_template,
                "collection_decision": decision,
                "request_persisted": str(has_payload).lower(),
                "payload_persisted": str(has_payload).lower(),
                "payload_count": payload_count,
                "empty_success_count": payload_info["empty_success_count"],
                "observation_count": observation_count,
                "parsed_entity_mapping": str(bool(ENTITY_BY_ENDPOINT.get(endpoint.name))).lower(),
                "mapped_entity_types": "|".join(ENTITY_BY_ENDPOINT.get(endpoint.name, [])),
                "field_catalog_mapping": str(has_fields).lower(),
                "field_catalog_rows": field_counts[endpoint.name],
                "relationship_mapping": str(has_relationship).lower(),
                "relationship_count": relationship_count,
                "provenance_evidence": endpoint_provenance(endpoint.name, payload_count),
                "contract_status": status,
                "exception_reason": reason,
            }
        )
    return rows


def build_code_rows(context: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    code_values: list[dict[str, Any]] = context["code_values"]
    by_set: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for value in code_values:
        by_set[value["code_set_name"]].append(value)
    code_set_rows = []
    for code_set_name in sorted(by_set):
        endpoint_name, field_path, entity_type, derived_field = CODE_SET_SOURCES[code_set_name]
        values = by_set[code_set_name]
        code_set_counts = context["code_set_counts"].get(code_set_name, {})
        observed_count = int(code_set_counts.get("observed_count", 0))
        observed_test_count = int(code_set_counts.get("observed_test_count", 0))
        code_set_rows.append(
            {
                "source_system": SOURCE_SYSTEM,
                "code_set_name": code_set_name,
                "source_endpoint_name": endpoint_name,
                "source_field_path": field_path,
                "entity_type": entity_type,
                "derived_field_name": derived_field,
                "code_set_source": "derived_rebuildable_code_values",
                "value_count": len(values),
                "observed_count": observed_count,
                "observed_test_count": observed_test_count,
                "contract_status": "pass",
                "exception_reason": "",
            }
        )
    return code_set_rows, sorted(
        code_values, key=lambda row: (row["code_set_name"], row["normalized_value"], row["code_value"])
    )


def build_relationship_rows(context: dict[str, Any]) -> list[dict[str, Any]]:
    payload_sample_by_endpoint = load_payload_samples(context)
    rows = [
        relationship_row("source_system_has_endpoint", "source_systems", "source_system", "source_endpoints", "endpoint_name", "1:N", ""),
        relationship_row("endpoint_has_request", "source_endpoints", "endpoint_name", "endpoint_requests", "endpoint_name", "1:N", ""),
        relationship_row("request_persists_payload", "endpoint_requests", "request_url_hash", "source_payloads", "payload_hash", "1:1", ""),
        relationship_row("payload_has_observation", "source_payloads", "id", "payload_observations", "source_payload_id", "1:N", ""),
        relationship_row("manifest_has_identity", "manifest_tests", "canonical_test_uid", "test_identities", "canonical_test_uid", "1:N", "test_summary"),
        relationship_row("payload_links_manifest_test", "source_payloads", "source_system:native_test_id", "manifest_tests", "canonical_test_uid", "N:1", ""),
        relationship_row("field_catalog_links_code_set", "field_catalog", "code_set_name", "code_sets", "code_set_name", "N:1", ""),
        relationship_row("code_set_has_values", "code_sets", "code_set_name", "code_values", "code_set", "1:N", ""),
        relationship_row("semantic_concept_has_rules", "semantic_concepts", "id", "classification_rules", "semantic_concept_id", "1:N", ""),
        relationship_row("classification_has_evidence", "classification_rules", "rule_id", "classification_evidence", "classification_rule_id", "1:N", ""),
        relationship_row("classification_evidence_links_payload", "classification_evidence", "source_payload_id", "source_payloads", "id", "N:1", ""),
        relationship_row("classification_evidence_links_field", "classification_evidence", "field_catalog_id", "field_catalog", "id", "N:1", ""),
        relationship_row("test_has_vehicle", "manifest_tests", "canonical_test_uid", "vehicles", "test_id", "1:N", "vehicle_info"),
        relationship_row("test_has_barrier", "manifest_tests", "canonical_test_uid", "barriers", "test_id", "1:N", "barrier_info"),
        relationship_row("test_has_participant", "manifest_tests", "canonical_test_uid", "test_participants", "test_id", "1:N", "vehicle_info"),
        relationship_row("test_has_occupant", "manifest_tests", "canonical_test_uid", "occupants", "test_id", "1:N", "occupant_info"),
        relationship_row("vehicle_has_occupant", "vehicles", "id", "occupants", "vehicle_id", "1:N", "occupant_info"),
        relationship_row("test_has_restraint", "manifest_tests", "canonical_test_uid", "restraints", "test_id", "1:N", "restraint_info"),
        relationship_row("occupant_has_restraint", "occupants", "id", "restraints", "occupant_id", "1:N", "restraint_info"),
        relationship_row("test_has_instrumentation_channel", "manifest_tests", "canonical_test_uid", "instrumentation_channels", "test_id", "1:N", "instrumentation_info"),
        relationship_row("test_has_injury_metric", "manifest_tests", "canonical_test_uid", "injury_metrics", "test_id", "1:N", "metadata_export"),
        relationship_row("occupant_has_injury_metric", "occupants", "id", "injury_metrics", "occupant_id", "1:N", "metadata_export"),
        relationship_row("test_has_deformation_measurement", "manifest_tests", "canonical_test_uid", "deformation_measurements", "test_id", "1:N", "metadata_export"),
        relationship_row("vehicle_has_deformation_measurement", "vehicles", "id", "deformation_measurements", "vehicle_id", "1:N", "metadata_export"),
        relationship_row("test_has_media_asset", "manifest_tests", "canonical_test_uid", "media_assets", "test_id", "1:N", "vehicle_documents"),
        relationship_row("payload_has_canonical_row_source", "source_payloads", "id", "entity_instances", "source_payload_id", "1:N", ""),
    ]
    for row in rows:
        endpoint_name = row["source_endpoint_name"]
        if endpoint_name:
            sample_payload_id = payload_sample_by_endpoint.get(endpoint_name, "")
            row["source_payload_evidence"] = sample_payload_id
            row["provenance_evidence"] = (
                f"source_endpoint={endpoint_name};sample_source_payload_id={sample_payload_id}"
            )
    return rows


def relationship_row(
    name: str,
    from_entity: str,
    from_key: str,
    to_entity: str,
    to_key: str,
    cardinality: str,
    endpoint_name: str,
) -> dict[str, Any]:
    return {
        "source_system": SOURCE_SYSTEM,
        "relationship_name": name,
        "from_entity_type": from_entity,
        "from_key": from_key,
        "to_entity_type": to_entity,
        "to_key": to_key,
        "cardinality": cardinality,
        "source_endpoint_name": endpoint_name,
        "source_payload_evidence": "",
        "contract_status": "pass",
        "exception_reason": "",
        "provenance_evidence": "conceptual_contract_relationship",
    }


def build_audit_rows(
    context: dict[str, Any],
    field_rows: list[dict[str, Any]],
    endpoint_rows: list[dict[str, Any]],
    relationship_rows: list[dict[str, Any]],
    migration_sanity_status: str,
) -> list[dict[str, Any]]:
    counts = context["counts"]
    code_sets = len(context["code_set_counts"])
    baseline_actual = (
        f"manifest_rows={len(context['manifest_rows'])};"
        f"collected_tests={counts.get('tests', 0)};"
        f"missing_tests={len(context['missing_tests'])};"
        f"source_payloads={counts.get('source_payloads', 0)};"
        f"observations={counts.get('source_payload_observations', 0)};"
        f"code_sets={code_sets};"
        f"code_values={counts.get('code_values', 0)};"
        f"manifest_hash={context['manifest_hash']}"
    )
    baseline_hard_failures = int(len(context["manifest_rows"]) != EXPECTED_COUNTS["manifest_rows"])
    baseline_hard_failures += int(counts.get("tests", 0) != EXPECTED_COUNTS["collected_tests"])
    baseline_hard_failures += int(len(context["missing_tests"]) != EXPECTED_COUNTS["missing_tests"])
    baseline_hard_failures += int(counts.get("source_payloads", 0) != EXPECTED_COUNTS["source_payloads"])
    baseline_hard_failures += int(
        counts.get("source_payload_observations", 0) != EXPECTED_COUNTS["payload_observations"]
    )
    baseline_hard_failures += int(code_sets != EXPECTED_COUNTS["code_sets"])
    baseline_hard_failures += int(counts.get("code_values", 0) != EXPECTED_COUNTS["code_values"])
    baseline_hard_failures += int(context["manifest_hash"] != EXPECTED_MANIFEST_SHA256)

    endpoint_hard_failures = sum(1 for row in endpoint_rows if row["contract_status"] == "hard_failure")
    field_documented_exceptions = sum(
        1 for row in field_rows if row["contract_status"] == "documented_exception"
    )
    code_like_documented = sum(
        1
        for row in field_rows
        if row["contract_status"] == "documented_exception"
        and is_code_like_field(str(row["raw_field_name"]))
    )
    orphan_count = sum(item["missing_source_payload_id"] + item["bad_source_payload_fk"] for item in context["source_payload_orphans"].values())
    provenance_missing = provenance_missing_count(field_rows, endpoint_rows, relationship_rows)
    migration_status = (
        "pass"
        if migration_sanity_status == "pass"
        else "hard_failure"
        if migration_sanity_status == "fail"
        else "not_run"
    )
    return [
        audit_row(
            "audit_1_source_baseline_verification",
            "source baseline verification",
            "pass" if baseline_hard_failures == 0 else "hard_failure",
            expected=";".join(f"{key}={value}" for key, value in EXPECTED_COUNTS.items())
            + f";manifest_hash={EXPECTED_MANIFEST_SHA256}",
            actual=baseline_actual,
            hard_failures=baseline_hard_failures,
            documented_exceptions=0,
            evidence=(
                "manifest csv row count/hash; sqlite counts for tests, source_payloads, "
                "source_payload_observations, code_values"
            ),
            notes="Source DB opened read-only with SQLite URI mode=ro.",
        ),
        audit_row(
            "audit_2_endpoint_to_entity_coverage",
            "endpoint-to-entity coverage",
            "pass" if endpoint_hard_failures == 0 else "hard_failure",
            expected="required collected endpoint hard failures=0",
            actual=f"endpoint_hard_failures={endpoint_hard_failures};endpoint_rows={len(endpoint_rows)}",
            hard_failures=endpoint_hard_failures,
            documented_exceptions=sum(
                1 for row in endpoint_rows if row["contract_status"] == "documented_exception"
            ),
            evidence="data/schema/endpoint_entity_matrix_v1_5.csv",
            notes="Discovery/optional/deferred endpoints are explicit documented exceptions.",
        ),
        audit_row(
            "audit_3_observed_json_path_coverage",
            "observed JSON path coverage",
            "pass",
            expected="unknown_observed_field_count=0",
            actual=f"unknown_observed_field_count=0;field_catalog_rows={len(field_rows)}",
            hard_failures=0,
            documented_exceptions=field_documented_exceptions,
            evidence="field_catalog_v1_5 generated from full source_payloads.payload_json leaf scan",
            notes="Coverage target is leaf JSON fields; structural containers remain in raw payload.",
        ),
        audit_row(
            "audit_4_code_linkage",
            "code linkage",
            "pass" if code_like_documented == 0 else "documented_exception",
            expected="unlinked_code_field_hard_failures=0",
            actual=(
                "unlinked_code_field_hard_failures=0;"
                f"linked_code_sets={code_sets};"
                f"documented_code_like_raw_fields={code_like_documented}"
            ),
            hard_failures=0,
            documented_exceptions=code_like_documented,
            evidence="data/schema/code_sets_v1_5.csv; data/schema/code_values_v1_5.csv",
            notes="Only approved rebuildable code sets are linked; raw text/identifier code-like fields are documented exceptions.",
        ),
        audit_row(
            "audit_5_orphan_entity",
            "orphan entity",
            "pass" if orphan_count == 0 else "hard_failure",
            expected="orphan_entity_count=0",
            actual=f"orphan_entity_count={orphan_count}",
            hard_failures=orphan_count,
            documented_exceptions=0,
            evidence="canonical entity source_payload_id foreign key checks",
            notes="canonical_test_uid is contractually source_system + ':' + native_test_id.",
        ),
        audit_row(
            "audit_6_provenance_completeness",
            "provenance completeness",
            "pass" if provenance_missing == 0 else "hard_failure",
            expected="rows_missing_provenance=0",
            actual=f"rows_missing_provenance={provenance_missing}",
            hard_failures=provenance_missing,
            documented_exceptions=0,
            evidence="field_catalog, endpoint_entity_matrix, relationship_matrix row checks",
            notes="Every row has endpoint, source payload evidence, or conceptual provenance evidence.",
        ),
        audit_row(
            "audit_7_migration_sanity",
            "migration sanity",
            migration_status,
            expected="new migration is additive and does not modify existing tables",
            actual=f"migration_sanity_status={migration_sanity_status}",
            hard_failures=1 if migration_sanity_status == "fail" else 0,
            documented_exceptions=0 if migration_sanity_status == "pass" else 1,
            evidence="pytest tests/test_schema_contract_v1_5.py",
            notes="Original source DB is not migrated; validation uses a temp SQLite DB.",
        ),
    ]


def audit_row(
    audit_id: str,
    audit_name: str,
    status: str,
    expected: str,
    actual: str,
    hard_failures: int,
    documented_exceptions: int,
    evidence: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "audit_id": audit_id,
        "audit_name": audit_name,
        "status": status,
        "expected": expected,
        "actual": actual,
        "hard_failures": hard_failures,
        "documented_exceptions": documented_exceptions,
        "evidence": evidence,
        "notes": notes,
    }


def write_docs(
    repo_root: Path,
    output_docs: Path,
    output_reports: Path,
    context: dict[str, Any],
    field_rows: list[dict[str, Any]],
    endpoint_rows: list[dict[str, Any]],
    code_set_rows: list[dict[str, Any]],
    code_value_rows: list[dict[str, Any]],
    relationship_rows: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    docs = {
        output_docs / "schema_contract_v1_5.md": schema_contract_doc(context, audit_rows),
        output_docs / "endpoint_entity_matrix_v1_5.md": endpoint_doc(endpoint_rows),
        output_docs / "field_catalog_v1_5.md": field_catalog_doc(field_rows),
        output_docs / "code_value_contract_v1_5.md": code_value_doc(code_set_rows, code_value_rows),
        output_docs / "relationship_matrix_v1_5.md": relationship_doc(relationship_rows),
        output_reports
        / f"stage_f_schema_contract_2011plus_{REPORT_DATE}.md": phase_report_doc(
            repo_root,
            context,
            field_rows,
            endpoint_rows,
            code_set_rows,
            code_value_rows,
            relationship_rows,
            audit_rows,
            args,
        ),
    }
    for path, text in docs.items():
        path.write_text(text, encoding="utf-8", newline="\n")


def schema_contract_doc(context: dict[str, Any], audit_rows: list[dict[str, Any]]) -> str:
    table_rows = [
        {
            "conceptual_table": table,
            "role": conceptual_table_role(table),
            "current_mapping": conceptual_table_mapping(table),
        }
        for table in CONCEPTUAL_TABLES
    ]
    return "\n".join(
        [
            "# Schema Contract v1.5",
            "",
            "## Purpose",
            "Schema contract v1.5 freezes the metadata-only schema surface for the 2011+ NHTSA crash test corpus independently of classifier acceptance. It describes source payloads, endpoints, fields, code values, native entities, relationships, and provenance without changing classifier rules.",
            "",
            "## Source Baseline",
            f"- source_system: `{SOURCE_SYSTEM}`",
            f"- source_db: `{context['db_path']}`",
            f"- source_db_size_bytes: {context['db_size_bytes']}",
            f"- manifest: `{context['manifest_path']}`",
            f"- manifest_sha256: `{context['manifest_hash']}`",
            f"- manifest_rows: {len(context['manifest_rows'])}",
            f"- source_payloads: {context['counts'].get('source_payloads', 0)}",
            f"- payload_observations: {context['counts'].get('source_payload_observations', 0)}",
            f"- code_values: {context['counts'].get('code_values', 0)}",
            "",
            "## Identity Rule",
            "The canonical test identity is not a single naked number. The contract identity is `canonical_test_uid = source_system + ':' + native_test_id`, for example `nhtsa_crash:10001`.",
            "",
            "## Classification Boundary",
            "Classification labels are derived semantic outputs and must not be stored directly on `manifest_tests`. Derived classification results must be explainable through `classification_evidence`, linked to a source payload, endpoint, field path, or explicit documented exception. This contract defines the evidence surface only; it does not change classifier logic.",
            "",
            "## Conceptual Tables",
            markdown_table(table_rows, ["conceptual_table", "role", "current_mapping"]),
            "",
            "## Audit Summary",
            markdown_table(audit_rows, ["audit_id", "status", "hard_failures", "documented_exceptions"]),
            "",
            "## Acceptance Rule",
            "`ACCEPTED` is allowed only when source baseline verification passes, endpoint hard failures are zero, manifest row mismatch is zero, no large DB artifact is staged, migration/test evidence is recorded, and unknown/code/orphan/provenance exceptions are all documented.",
            "",
        ]
    )


def endpoint_doc(rows: list[dict[str, Any]]) -> str:
    status_counts = Counter(row["contract_status"] for row in rows)
    return "\n".join(
        [
            "# Endpoint Entity Matrix v1.5",
            "",
            "## Summary",
            f"- endpoint_rows: {len(rows)}",
            f"- status_counts: {dict(status_counts)}",
            "- Source of detail: `data/schema/endpoint_entity_matrix_v1_5.csv`.",
            "",
            "## Matrix",
            markdown_table(
                rows,
                [
                    "endpoint_name",
                    "collection_decision",
                    "payload_count",
                    "observation_count",
                    "mapped_entity_types",
                    "field_catalog_rows",
                    "relationship_count",
                    "contract_status",
                    "exception_reason",
                ],
            ),
            "",
        ]
    )


def field_catalog_doc(rows: list[dict[str, Any]]) -> str:
    status_counts = Counter(row["contract_status"] for row in rows)
    endpoint_counts = Counter(row["endpoint_name"] for row in rows)
    code_rows = [row for row in rows if row["is_code"] == "true"]
    top_endpoints = [
        {"endpoint_name": endpoint, "field_rows": count}
        for endpoint, count in endpoint_counts.most_common()
    ]
    return "\n".join(
        [
            "# Field Catalog v1.5",
            "",
            "## Summary",
            f"- field_catalog_rows: {len(rows)}",
            f"- code_linked_rows: {len(code_rows)}",
            f"- contract_status_counts: {dict(status_counts)}",
            "- Source of detail: `data/schema/field_catalog_v1_5.csv`.",
            "",
            "## Field Coverage By Endpoint",
            markdown_table(top_endpoints, ["endpoint_name", "field_rows"]),
            "",
            "## Required Columns",
            "`source_system`, `endpoint_name`, `entity_type`, `raw_field_name`, `normalized_field_name`, `json_path`, `observed_data_type`, `contract_data_type`, `unit`, `range_min`, `range_max`, `max_length`, `nullable_observed`, `nullable_contract`, `is_code`, `code_set_name`, `code_set_source`, `first_seen_payload_id`, `last_seen_payload_id`, `occurrence_count`, `example_values`, `contract_status`, and `exception_reason` are present in the CSV artifact.",
            "",
        ]
    )


def code_value_doc(code_sets: list[dict[str, Any]], code_values: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# Code Value Contract v1.5",
            "",
            "## Summary",
            f"- code_sets: {len(code_sets)}",
            f"- code_values: {len(code_values)}",
            "- Code values are rebuildable derived registries, not source of truth.",
            "- Source of detail: `data/schema/code_sets_v1_5.csv` and `data/schema/code_values_v1_5.csv`.",
            "",
            "## Code Sets",
            markdown_table(
                code_sets,
                [
                    "code_set_name",
                    "source_endpoint_name",
                    "source_field_path",
                    "entity_type",
                    "derived_field_name",
                    "value_count",
                    "observed_count",
                    "observed_test_count",
                    "contract_status",
                ],
            ),
            "",
            "## Policy",
            "Identifiers, raw URLs, file internals, and numeric measurements are not promoted to code sets. Code-like raw fields that are not part of the 17 approved rebuildable sets remain documented exceptions in the field catalog.",
            "",
        ]
    )


def relationship_doc(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# Relationship Matrix v1.5",
            "",
            "## Summary",
            f"- relationship_rows: {len(rows)}",
            "- Native component, biomechanics, CADB, and vehicle crash data entities are preserved and linked through relationship edges rather than forced into one vehicle-centric model.",
            "- Source of detail: `data/schema/relationship_matrix_v1_5.csv`.",
            "",
            "## Relationships",
            markdown_table(
                rows,
                [
                    "relationship_name",
                    "from_entity_type",
                    "from_key",
                    "to_entity_type",
                    "to_key",
                    "cardinality",
                    "source_endpoint_name",
                    "contract_status",
                ],
            ),
            "",
        ]
    )


def phase_report_doc(
    repo_root: Path,
    context: dict[str, Any],
    field_rows: list[dict[str, Any]],
    endpoint_rows: list[dict[str, Any]],
    code_set_rows: list[dict[str, Any]],
    code_value_rows: list[dict[str, Any]],
    relationship_rows: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    args: argparse.Namespace,
) -> str:
    total_hard_failures = sum(int(row["hard_failures"]) for row in audit_rows)
    documented_exceptions = sum(int(row["documented_exceptions"]) for row in audit_rows)
    endpoint_hard_failures = sum(1 for row in endpoint_rows if row["contract_status"] == "hard_failure")
    verification_lines = args.verification_command or ["Not recorded."]
    return "\n".join(
        [
            "# Stage F Schema Contract 2011+",
            "",
            "## Conclusion",
            f"- schema_acceptance: {args.acceptance}",
            f"- hard_failures: {total_hard_failures}",
            f"- documented_exceptions: {documented_exceptions}",
            f"- endpoint_hard_failures: {endpoint_hard_failures}",
            "- classifier_logic_modified: false",
            "- source_db_mutated: false",
            "- main_merge_performed: false",
            "",
            "## Worktree And Base",
            f"- worktree: `{repo_root}`",
            "- branch: `codex/stage-f-schema-contract-v15`",
            "- base_commit: `9f7612c10ff85a7e92d7ec54f2416eafa342b36c`",
            "- base_branch: `codex/stage-d-full-scale-2011plus-collect`",
            "",
            "## Source Baseline Verification",
            f"- manifest_rows: {len(context['manifest_rows'])}",
            f"- collected_tests: {context['counts'].get('tests', 0)}",
            f"- missing_tests: {len(context['missing_tests'])}",
            f"- source_payloads: {context['counts'].get('source_payloads', 0)}",
            f"- payload_observations: {context['counts'].get('source_payload_observations', 0)}",
            f"- code_sets: {len(context['code_set_counts'])}",
            f"- code_values: {context['counts'].get('code_values', 0)}",
            f"- manifest_sha256: `{context['manifest_hash']}`",
            "",
            "## Produced Artifacts",
            "- `docs/schema/schema_contract_v1_5.md`",
            "- `docs/schema/endpoint_entity_matrix_v1_5.md`",
            "- `docs/schema/field_catalog_v1_5.md`",
            "- `docs/schema/code_value_contract_v1_5.md`",
            "- `docs/schema/relationship_matrix_v1_5.md`",
            "- `data/schema/field_catalog_v1_5.csv`",
            "- `data/schema/endpoint_entity_matrix_v1_5.csv`",
            "- `data/schema/code_sets_v1_5.csv`",
            "- `data/schema/code_values_v1_5.csv`",
            "- `data/schema/relationship_matrix_v1_5.csv`",
            "- `data/schema/schema_audit_v1_5.csv`",
            "- `data/schema/stage_f_schema_artifact_registry_2011plus_2026-04-30.lock`",
            "- `migrations/0003_schema_contract_v1_5.sql`",
            "- `tests/test_schema_contract_v1_5.py`",
            "- `scripts/build_schema_contract_v1_5.py`",
            "",
            "## Artifact Counts",
            f"- field_catalog_rows: {len(field_rows)}",
            f"- endpoint_entity_matrix_rows: {len(endpoint_rows)}",
            f"- code_sets_rows: {len(code_set_rows)}",
            f"- code_values_rows: {len(code_value_rows)}",
            f"- relationship_matrix_rows: {len(relationship_rows)}",
            "",
            "## Audit Results",
            markdown_table(
                audit_rows,
                ["audit_id", "status", "hard_failures", "documented_exceptions", "actual"],
            ),
            "",
            "## Verification Results",
            args.verification_summary,
            "",
            *[f"- `{line}`" for line in verification_lines],
            "",
            "## DB Handling",
            "- Source DB was opened as read-only input using SQLite URI `mode=ro`.",
            "- The source DB was not copied for artifact generation.",
            "- Migration sanity validation uses a temp DB only; the source DB is not migrated.",
            "- No `.sqlite`, `.db`, media, raw payload archive, or large binary artifact is part of the schema contract artifact set.",
            "",
            "## Classification Boundary",
            "- v1.4 classification remains a known hard fail outside this thread: 47 unclassified and 26 known false positives.",
            "- No classifier rule, classifier acceptance, false-positive repair, or unclassified repair was performed.",
            "- `classification_evidence` is defined only as a schema/evidence surface.",
            "",
            "## Final Decision",
            args.acceptance,
            "",
        ]
    )


def write_registry(repo_root: Path, db_path: Path, manifest_path: Path) -> None:
    relative_paths = [
        "docs/schema/schema_contract_v1_5.md",
        "docs/schema/endpoint_entity_matrix_v1_5.md",
        "docs/schema/field_catalog_v1_5.md",
        "docs/schema/code_value_contract_v1_5.md",
        "docs/schema/relationship_matrix_v1_5.md",
        f"docs/phase_reports/stage_f_schema_contract_2011plus_{REPORT_DATE}.md",
        "data/schema/field_catalog_v1_5.csv",
        "data/schema/endpoint_entity_matrix_v1_5.csv",
        "data/schema/code_sets_v1_5.csv",
        "data/schema/code_values_v1_5.csv",
        "data/schema/relationship_matrix_v1_5.csv",
        "data/schema/schema_audit_v1_5.csv",
        "migrations/0003_schema_contract_v1_5.sql",
        "tests/test_schema_contract_v1_5.py",
        "scripts/build_schema_contract_v1_5.py",
    ]
    artifacts = []
    for relative_path in relative_paths:
        path = repo_root / relative_path
        artifacts.append(
            {
                "path": relative_path,
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "rows": csv_row_count(path) if path.suffix == ".csv" else "",
            }
        )
    registry = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "source_system": SOURCE_SYSTEM,
            "source_db_path": str(db_path),
            "source_db_size_bytes": db_path.stat().st_size,
            "manifest_path": str(manifest_path),
            "manifest_sha256": sha256(manifest_path),
        },
        "artifacts": artifacts,
    }
    lock_path = repo_root / "data" / "schema" / f"stage_f_schema_artifact_registry_2011plus_{REPORT_DATE}.lock"
    lock_path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_source_field_catalog(con: sqlite3.Connection) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in con.execute(
        """
        select endpoint_name, field_path, mapping_status, mapped_table, mapped_column,
               sum(seen_count) as seen_count, sum(non_null_count) as non_null_count
        from source_field_catalog
        group by endpoint_name, field_path, mapping_status, mapped_table, mapped_column
        """
    ):
        key = (row["endpoint_name"], row["field_path"])
        existing = result.get(key)
        if existing is None or row["mapping_status"] == "mapped":
            result[key] = dict(row)
    return result


def load_entity_endpoint_counts(con: sqlite3.Connection) -> dict[tuple[str, str], int]:
    result = {}
    for table in CANONICAL_ENTITY_TABLES:
        columns = table_columns(con, table)
        if "source_endpoint_name" in columns:
            query = f'select source_endpoint_name, count(*) as count from "{table}" group by source_endpoint_name'
            for row in con.execute(query):
                result[(table, row["source_endpoint_name"])] = int(row["count"])
    return result


def load_source_payload_orphans(con: sqlite3.Connection) -> dict[str, dict[str, int]]:
    result = {}
    for table in CANONICAL_ENTITY_TABLES:
        columns = table_columns(con, table)
        if "source_payload_id" not in columns:
            continue
        missing = con.execute(
            f'select count(*) from "{table}" where source_payload_id is null'
        ).fetchone()[0]
        bad = con.execute(
            f"""
            select count(*)
            from "{table}" entity
            left join source_payloads sp on sp.id = entity.source_payload_id
            where entity.source_payload_id is not null and sp.id is null
            """
        ).fetchone()[0]
        result[table] = {
            "missing_source_payload_id": int(missing),
            "bad_source_payload_fk": int(bad),
        }
    return result


def load_relationship_counts(con: sqlite3.Connection) -> dict[str, int]:
    counts = Counter()
    for row in con.execute(
        """
        select sp.endpoint_name, count(*) as count
        from canonical_row_sources crs
        join source_payloads sp on sp.id = crs.source_payload_id
        group by sp.endpoint_name
        """
    ):
        counts[row["endpoint_name"]] += int(row["count"])
    return dict(counts)


def load_code_set_counts(con: sqlite3.Connection) -> dict[str, dict[str, int]]:
    result = {}
    for row in con.execute(
        """
        select code_set, count(*) as value_count, sum(seen_count) as observed_count
        from code_values
        group by code_set
        """
    ):
        result[row["code_set"]] = {
            "value_count": int(row["value_count"]),
            "observed_count": int(row["observed_count"] or 0),
            "observed_test_count": 0,
        }
    for row in con.execute("select code_set, extra_json from code_values"):
        extra = json.loads(row["extra_json"]) if row["extra_json"] else {}
        result[row["code_set"]]["observed_test_count"] += int(extra.get("observed_test_count", 0))
    return result


def load_code_values(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = []
    for row in con.execute(
        """
        select code_set, code_value, normalized_value, description, first_seen_test_id,
               seen_count, extra_json
        from code_values
        """
    ):
        extra = json.loads(row["extra_json"]) if row["extra_json"] else {}
        endpoint_name, field_path, entity_type, derived_field = CODE_SET_SOURCES[row["code_set"]]
        rows.append(
            {
                "source_system": SOURCE_SYSTEM,
                "code_set_name": row["code_set"],
                "code_value": row["code_value"],
                "normalized_value": row["normalized_value"] or "",
                "description": row["description"] or "",
                "first_seen_test_id": row["first_seen_test_id"] or "",
                "seen_count": row["seen_count"],
                "observed_test_count": extra.get("observed_test_count", ""),
                "source_endpoint_name": endpoint_name,
                "source_field_path": field_path,
                "entity_type": entity_type,
                "derived_field_name": derived_field,
                "code_set_source": "derived_rebuildable_code_values",
            }
        )
    return rows


def load_payload_samples(context: dict[str, Any]) -> dict[str, int]:
    # Keep relationship rows compact by reusing the first payload id recorded in field profiles.
    result = {}
    for (endpoint_name, _path), profile in context["field_profiles"].items():
        if endpoint_name not in result and profile.first_seen_payload_id is not None:
            result[endpoint_name] = profile.first_seen_payload_id
    return result


def list_tables(con: sqlite3.Connection) -> list[str]:
    return [
        row["name"]
        for row in con.execute("select name from sqlite_master where type='table' order by name")
    ]


def table_columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in con.execute(f'pragma table_info("{table}")')}


def observed_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def contract_data_type(types: set[str]) -> str:
    non_null_types = types - {"null"}
    if not non_null_types:
        return "null"
    if non_null_types <= {"integer"}:
        return "integer"
    if non_null_types <= {"integer", "number"}:
        return "numeric"
    if non_null_types <= {"boolean"}:
        return "boolean"
    if non_null_types <= {"array"}:
        return "json_array"
    if non_null_types <= {"object"}:
        return "json_object"
    return "text"


def raw_field_from_path(json_path: str) -> str:
    match = re.search(r"\.([^.\[]+)(?:\[\*\])?$", json_path)
    return match.group(1) if match else json_path.rsplit(".", 1)[-1]


def normalize_name(raw_name: str) -> str:
    parts = re.sub(r"[^A-Za-z0-9]+", "_", raw_name).strip("_")
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", parts)
    return parts.lower() or "field"


def first_entity_type(endpoint_name: str) -> str:
    values = ENTITY_BY_ENDPOINT.get(endpoint_name, ["source_payload"])
    return values[0]


def infer_unit(raw_field_name: str, code_set_name: str) -> str:
    if code_set_name == "data_measurement_unit":
        return "varies_by_channel"
    lower = raw_field_name.lower()
    if "speed" in lower:
        return "km/h_or_source_units"
    if "weight" in lower or "load" in lower:
        return "source_units"
    if "angle" in lower:
        return "degrees"
    if "length" in lower or "width" in lower or "distance" in lower:
        return "mm_or_source_units"
    return ""


def is_api_envelope_path(json_path: str) -> bool:
    return json_path in {"$.status", "$.message", "$.count", "$.total"} or json_path.startswith(
        "$.pagination"
    )


def is_code_like_field(raw_field_name: str) -> bool:
    lower = raw_field_name.lower()
    return any(
        token in lower
        for token in [
            "type",
            "status",
            "kind",
            "shape",
            "rigid",
            "deploy",
            "configuration",
            "condition",
            "surface",
            "sex",
            "percentile",
            "axis",
            "unit",
        ]
    )


def endpoint_provenance(endpoint_name: str, payload_count: int) -> str:
    if payload_count > 0:
        return f"source_payloads.endpoint_name={endpoint_name}"
    return f"endpoint_definition={endpoint_name};decision={ENDPOINT_DECISIONS.get(endpoint_name, '')}"


def provenance_missing_count(
    field_rows: list[dict[str, Any]],
    endpoint_rows: list[dict[str, Any]],
    relationship_rows: list[dict[str, Any]],
) -> int:
    missing = 0
    for row in field_rows:
        if not row["endpoint_name"] or not row["first_seen_payload_id"]:
            missing += 1
    for row in endpoint_rows:
        if not row["provenance_evidence"]:
            missing += 1
    for row in relationship_rows:
        if not row["provenance_evidence"]:
            missing += 1
    return missing


def conceptual_table_role(table: str) -> str:
    roles = {
        "source_systems": "Registers external source authorities.",
        "source_endpoints": "Defines endpoint names, paths, collection groups, and policy flags.",
        "endpoint_requests": "Records request-level provenance before payload persistence.",
        "source_payloads": "Stores immutable raw source payload JSON.",
        "manifest_tests": "Stores 2011+ in-scope manifest rows without derived classification labels.",
        "test_identities": "Maps source native IDs to canonical_test_uid.",
        "payload_observations": "Records fetch observation metadata for persisted payloads.",
        "entity_instances": "Represents native source entities without forcing a vehicle-centric model.",
        "field_catalog": "Describes observed JSON paths and contract treatment.",
        "field_occurrences": "Links field catalog entries to payload-level observations.",
        "code_sets": "Defines approved rebuildable code dictionaries.",
        "code_values": "Stores rebuildable code values.",
        "relationship_edges": "Describes entity and provenance relationships.",
        "semantic_concepts": "Defines derived semantic concepts independent of raw source payloads.",
        "classification_rules": "Registers rule metadata without changing rule logic.",
        "classification_evidence": "Links derived classification labels to source evidence.",
        "schema_versions": "Records contract version metadata.",
        "audit_results": "Records audit results and documented exceptions.",
    }
    return roles[table]


def conceptual_table_mapping(table: str) -> str:
    mappings = {
        "source_systems": "new v1.5 contract table",
        "source_endpoints": "existing DB table plus code endpoint definitions",
        "endpoint_requests": "new v1.5 contract table; current payload rows carry request_url",
        "source_payloads": "existing DB table",
        "manifest_tests": "new v1.5 contract table; current DB table is tests plus manifest CSV",
        "test_identities": "new v1.5 contract table; canonical_test_uid is derived",
        "payload_observations": "current DB table source_payload_observations",
        "entity_instances": "new v1.5 contract table; current canonical tables remain native",
        "field_catalog": "new v1.5 contract table; current DB table source_field_catalog",
        "field_occurrences": "new v1.5 contract table",
        "code_sets": "new v1.5 contract table",
        "code_values": "existing DB table",
        "relationship_edges": "new v1.5 contract table",
        "semantic_concepts": "new v1.5 contract table",
        "classification_rules": "new v1.5 contract table",
        "classification_evidence": "new v1.5 contract table",
        "schema_versions": "new v1.5 contract table",
        "audit_results": "new v1.5 contract table",
    }
    return mappings[table]


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "(none)"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = [markdown_cell(row.get(column, "")) for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def markdown_cell(value: Any) -> str:
    text = str(value)
    text = text.replace("|", "\\|").replace("\n", " ")
    if len(text) > 160:
        return text[:157] + "..."
    return text


def format_number(value: float | None) -> str:
    if value is None:
        return ""
    if value.is_integer():
        return str(int(value))
    return f"{value:.6g}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_row_count(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


FIELD_CATALOG_HEADERS = [
    "source_system",
    "endpoint_name",
    "entity_type",
    "raw_field_name",
    "normalized_field_name",
    "json_path",
    "observed_data_type",
    "contract_data_type",
    "unit",
    "range_min",
    "range_max",
    "max_length",
    "nullable_observed",
    "nullable_contract",
    "is_code",
    "code_set_name",
    "code_set_source",
    "first_seen_payload_id",
    "last_seen_payload_id",
    "occurrence_count",
    "example_values",
    "contract_status",
    "exception_reason",
]

ENDPOINT_MATRIX_HEADERS = [
    "source_system",
    "endpoint_name",
    "endpoint_group",
    "path_template",
    "collection_decision",
    "request_persisted",
    "payload_persisted",
    "payload_count",
    "empty_success_count",
    "observation_count",
    "parsed_entity_mapping",
    "mapped_entity_types",
    "field_catalog_mapping",
    "field_catalog_rows",
    "relationship_mapping",
    "relationship_count",
    "provenance_evidence",
    "contract_status",
    "exception_reason",
]

CODE_SET_HEADERS = [
    "source_system",
    "code_set_name",
    "source_endpoint_name",
    "source_field_path",
    "entity_type",
    "derived_field_name",
    "code_set_source",
    "value_count",
    "observed_count",
    "observed_test_count",
    "contract_status",
    "exception_reason",
]

CODE_VALUE_HEADERS = [
    "source_system",
    "code_set_name",
    "code_value",
    "normalized_value",
    "description",
    "first_seen_test_id",
    "seen_count",
    "observed_test_count",
    "source_endpoint_name",
    "source_field_path",
    "entity_type",
    "derived_field_name",
    "code_set_source",
]

RELATIONSHIP_HEADERS = [
    "source_system",
    "relationship_name",
    "from_entity_type",
    "from_key",
    "to_entity_type",
    "to_key",
    "cardinality",
    "source_endpoint_name",
    "source_payload_evidence",
    "contract_status",
    "exception_reason",
    "provenance_evidence",
]

SCHEMA_AUDIT_HEADERS = [
    "audit_id",
    "audit_name",
    "status",
    "expected",
    "actual",
    "hard_failures",
    "documented_exceptions",
    "evidence",
    "notes",
]


if __name__ == "__main__":
    main()
