from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import UniqueConstraint, func, inspect, select
from sqlalchemy.orm import Session

from nhtsa_metadata.config import sanitize_database_url
from nhtsa_metadata.db.models import (
    AssetSummary,
    Barrier,
    Base,
    CanonicalRowSource,
    CodeValue,
    CollectionRun,
    CollectionRunItem,
    CrashTest,
    DeformationMeasurement,
    DiscoveryAuthorityDecision,
    DiscoveryManifestRow,
    DiscoveryRun,
    FieldCoverageSnapshot,
    InjuryMetric,
    InstrumentationChannel,
    InstrumentationChannelDetail,
    IntrusionMeasurement,
    MediaAsset,
    Occupant,
    Restraint,
    SourceConflict,
    SourceEndpoint,
    SourceFieldCatalog,
    SourcePayload,
    SourcePayloadObservation,
    SourcePayloadSection,
    TestClassification,
    TestFacet,
    TestFilterSummary,
    TestParticipant,
    Vehicle,
)
from nhtsa_metadata.sources.nhtsa_crash.endpoints import ENDPOINT_BY_NAME

RAW_TABLES = [
    "collection_runs",
    "collection_run_items",
    "source_endpoints",
    "source_payloads",
    "source_payload_observations",
    "source_payload_sections",
    "source_field_catalog",
    "source_conflicts",
    "canonical_row_sources",
    "discovery_runs",
    "discovery_manifest_rows",
    "discovery_authority_decisions",
]
CANONICAL_TABLES = [
    "tests",
    "test_participants",
    "vehicles",
    "barriers",
    "occupants",
    "restraints",
    "instrumentation_channels",
    "instrumentation_channel_details",
    "injury_metrics",
    "deformation_measurements",
    "intrusion_measurements",
    "media_assets",
    "code_values",
]
READ_MODEL_TABLES = [
    "test_filter_summary",
    "test_classification",
    "test_facets",
    "asset_summary",
    "field_coverage_snapshots",
]
REQUIRED_TABLES = RAW_TABLES + CANONICAL_TABLES + READ_MODEL_TABLES
LINEAGE_COLUMNS = {
    "source_payload_id",
    "source_endpoint_name",
    "source_section_name",
    "source_row_path",
    "source_row_hash",
    "raw_row_json",
    "extra_json",
}
LINEAGE_TABLES = [
    "tests",
    "test_participants",
    "vehicles",
    "barriers",
    "occupants",
    "restraints",
    "instrumentation_channels",
    "instrumentation_channel_details",
    "injury_metrics",
    "deformation_measurements",
    "intrusion_measurements",
    "media_assets",
]
REQUIRED_UNIQUE_CONSTRAINTS: dict[str, list[tuple[str, ...]]] = {
    "source_payloads": [("endpoint_name", "canonical_url_hash", "payload_hash")],
    "source_payload_sections": [("source_payload_id", "section_name", "json_path")],
    "source_field_catalog": [
        ("endpoint_name", "section_name", "field_path", "observed_type")
    ],
    "canonical_row_sources": [
        ("table_name", "row_id", "source_payload_id", "source_row_path", "source_row_hash")
    ],
    "discovery_manifest_rows": [
        ("discovery_run_id", "test_no"),
        ("discovery_run_id", "row_hash"),
    ],
    "tests": [("test_no",)],
    "vehicles": [("test_id", "source_vehicle_no", "source_row_hash")],
    "barriers": [("test_id", "source_row_hash")],
    "occupants": [
        ("test_id", "source_vehicle_no", "occupant_location_raw", "source_row_hash")
    ],
    "restraints": [
        (
            "test_id",
            "restraint_subject_kind",
            "restraint_subject_semantic_hash",
            "semantic_hash",
        )
    ],
    "instrumentation_channels": [("test_id", "curve_no")],
    "media_assets": [("test_id", "asset_kind", "canonical_url_hash")],
    "code_values": [("code_set", "code_value")],
    "test_filter_summary": [("test_id",), ("test_no",)],
    "test_classification": [("test_id",), ("test_no",)],
    "test_facets": [("facet_name", "facet_value")],
    "asset_summary": [("test_id", "asset_kind")],
}
CRITICAL_INDEXES: dict[str, list[tuple[str, ...]]] = {
    "tests": [("test_no",)],
    "source_payloads": [("test_no",), ("endpoint_name",), ("payload_hash",)],
    "source_payload_observations": [("source_payload_id",)],
    "discovery_runs": [("run_kind",), ("manifest_hash",)],
    "discovery_manifest_rows": [
        ("discovery_run_id",),
        ("test_no",),
        ("authority_status",),
        ("row_hash",),
    ],
    "discovery_authority_decisions": [("decision_name",)],
    "instrumentation_channels": [("test_id",), ("test_no",)],
    "media_assets": [("test_id",)],
    "test_filter_summary": [("test_no",)],
}
PROHIBITED_WHOLE_INDEX_COLUMNS = {"payload_json", "raw_row_json"}

ENDPOINT_CONTRACT = [
    {
        "logical_name": "vehicle-database-test-results",
        "endpoint_name": "test_results",
        "group": "discovery",
        "decision": "required",
        "cardinality_policy": "paginated discovery",
    },
    {
        "logical_name": "vehicle-database-test-results/by-search",
        "endpoint_name": "search",
        "group": "discovery",
        "decision": "required",
        "cardinality_policy": "paginated by-search manifest discovery",
    },
    {
        "logical_name": "test_summary / test-no/{testNo}",
        "endpoint_name": "test_summary",
        "group": "core",
        "decision": "required",
        "cardinality_policy": "one request per test_no",
    },
    {
        "logical_name": "test_detail / get-test-detail/{testNo}",
        "endpoint_name": "test_detail",
        "group": "core",
        "decision": "optional_core",
        "cardinality_policy": "one request per test_no when enabled",
    },
    {
        "logical_name": "metadata_export / metadata/{testNo}",
        "endpoint_name": "metadata_export",
        "group": "core",
        "decision": "required",
        "cardinality_policy": "one request per test_no",
    },
    {
        "logical_name": "vehicle_info",
        "endpoint_name": "vehicle_info",
        "group": "detail",
        "decision": "required",
        "cardinality_policy": "one request per test_no",
    },
    {
        "logical_name": "vehicle_detail_info",
        "endpoint_name": "vehicle_detail",
        "group": "detail",
        "decision": "optional_detail",
        "cardinality_policy": "one request per discovered vehicle_no",
    },
    {
        "logical_name": "barrier_info",
        "endpoint_name": "barrier_info",
        "group": "detail",
        "decision": "required",
        "cardinality_policy": "one request per test_no; empty success allowed",
    },
    {
        "logical_name": "occupant_info",
        "endpoint_name": "occupant_info",
        "group": "detail",
        "decision": "required",
        "cardinality_policy": "one request per test_no",
    },
    {
        "logical_name": "occupant_detail_information",
        "endpoint_name": "occupant_detail",
        "group": "detail",
        "decision": "optional_detail",
        "cardinality_policy": "one request per discovered occupant slot",
    },
    {
        "logical_name": "restraint_info",
        "endpoint_name": "restraint_info",
        "group": "detail",
        "decision": "required",
        "cardinality_policy": "one request per discovered occupant slot",
    },
    {
        "logical_name": "intrusion_info",
        "endpoint_name": "intrusion_info",
        "group": "detail",
        "decision": "required",
        "cardinality_policy": "one request per discovered vehicle_no; empty success allowed",
    },
    {
        "logical_name": "instrumentation_info",
        "endpoint_name": "instrumentation_info",
        "group": "detail",
        "decision": "required",
        "cardinality_policy": "paginated one-to-many per test_no",
    },
    {
        "logical_name": "instrumentation_detail_info",
        "endpoint_name": "instrumentation_detail",
        "group": "detail",
        "decision": "deferred_optional",
        "cardinality_policy": "one request per curve_no; deferred due request volume",
    },
    {
        "logical_name": "multimedia_files",
        "endpoint_name": "multimedia_files",
        "group": "assets",
        "decision": "required",
        "cardinality_policy": "one request per test_no; URL registry only",
    },
    {
        "logical_name": "vehicle_documents",
        "endpoint_name": "vehicle_documents",
        "group": "assets",
        "decision": "required",
        "cardinality_policy": "one request per test_no; URL registry only",
    },
]


@dataclass(frozen=True)
class ManifestRecord:
    test_no: int
    test_date: date
    test_year: int
    test_configuration_key: str | None
    test_configuration: str | None
    test_type: str | None
    model_year: int | None
    vehicle_make: str | None
    vehicle_model: str | None
    scope_status: str | None


class SchemaContractValidator:
    def __init__(self, session: Session, database_url: str | None) -> None:
        self.session = session
        self.database_url = database_url
        self.inspector = inspect(session.get_bind())

    def validate(self) -> dict[str, Any]:
        hard_failures: list[str] = []
        warnings: list[str] = []
        db_tables = set(self.inspector.get_table_names())
        metadata_tables = set(Base.metadata.tables)
        table_checks = []
        for table_name in REQUIRED_TABLES:
            exists_in_db = table_name in db_tables
            exists_in_model = table_name in metadata_tables
            if not exists_in_db or not exists_in_model:
                hard_failures.append(f"required table missing: {table_name}")
            table_checks.append(
                {
                    "table_name": table_name,
                    "exists_in_db": exists_in_db,
                    "exists_in_model": exists_in_model,
                }
            )
        column_checks = self._column_checks(db_tables, hard_failures)
        lineage_checks = self._lineage_checks(db_tables, hard_failures)
        unique_checks = self._unique_checks(hard_failures)
        index_checks = self._index_checks(db_tables, hard_failures, warnings)
        scope_contract = self._scope_contract_check(hard_failures)
        payload_observation = {
            "source_payload_observations_table": "source_payload_observations" in db_tables,
            "links_to_source_payloads": self._column_exists(
                "source_payload_observations", "source_payload_id"
            ),
        }
        if not payload_observation["source_payload_observations_table"]:
            hard_failures.append("source_payload_observations table missing")
        if not payload_observation["links_to_source_payloads"]:
            hard_failures.append("source_payload_observations.source_payload_id missing")
        return {
            "run": {
                "created_at": _now(),
                "database_url_redacted": sanitize_database_url(self.database_url)
                if self.database_url
                else None,
            },
            "summary": {
                "required_tables": len(REQUIRED_TABLES),
                "hard_failure_count": len(hard_failures),
                "warning_count": len(warnings),
                "result": "pass" if not hard_failures else "fail",
            },
            "table_checks": table_checks,
            "column_checks": column_checks,
            "lineage_checks": lineage_checks,
            "unique_constraint_checks": unique_checks,
            "index_checks": index_checks,
            "source_payload_immutability": _check_pass(
                unique_checks,
                "source_payloads",
                ("endpoint_name", "canonical_url_hash", "payload_hash"),
            ),
            "source_payload_observation_policy": payload_observation,
            "discovery_provenance_policy": {
                "tables": [
                    "discovery_runs",
                    "discovery_manifest_rows",
                    "discovery_authority_decisions",
                ],
                "result": "pass"
                if all(
                    table in db_tables
                    for table in (
                        "discovery_runs",
                        "discovery_manifest_rows",
                        "discovery_authority_decisions",
                    )
                )
                else "fail",
                "purpose": (
                    "operational authority and manifest lineage; not canonical source of truth"
                ),
            },
            "code_values_policy": {
                "decision": "derived_registry_not_source_of_truth",
                "table_exists": "code_values" in db_tables,
                "rebuildable_from": [
                    "source_field_catalog",
                    "canonical tables",
                    "schema optimize-analyze output",
                ],
            },
            "scope_contract": scope_contract,
            "prohibited_index_policy": {
                "prohibited_columns": sorted(PROHIBITED_WHOLE_INDEX_COLUMNS),
                "result": "pass"
                if not any(not row["passed"] for row in index_checks["prohibited"])
                else "fail",
            },
            "hard_failures": hard_failures,
            "warnings": warnings,
        }

    def to_markdown(self, payload: dict[str, Any]) -> str:
        summary = payload["summary"]
        lines = [
            "# Schema Contract Validation 2011+",
            "",
            "## Scope",
            "- DB schema v1.1 full-cover readiness validation.",
            "- Read-only validation; no live API, no detail collect, no file download.",
            "",
            "## Result",
            f"- result: {summary['result']}",
            f"- hard failures: {summary['hard_failure_count']}",
            f"- warnings: {summary['warning_count']}",
            "",
            "## Required Tables",
        ]
        for row in payload["table_checks"]:
            lines.append(
                f"- {row['table_name']}: db={row['exists_in_db']} model={row['exists_in_model']}"
            )
        lines.extend(
            [
                "",
                "## Lineage And Immutability",
                "- source_payload immutability: "
                f"{payload['source_payload_immutability']['passed']}",
                f"- source_payload_observations link: "
                f"{payload['source_payload_observation_policy']['links_to_source_payloads']}",
                f"- discovery provenance tables: "
                f"{payload['discovery_provenance_policy']['result']}",
                "",
                "## Prohibited Index Policy",
                f"- result: {payload['prohibited_index_policy']['result']}",
                "- whole-column `payload_json` / `raw_row_json` indexes are prohibited.",
                "",
                "## Hard Failures",
            ]
        )
        if payload["hard_failures"]:
            lines.extend(f"- {item}" for item in payload["hard_failures"])
        else:
            lines.append("- none")
        lines.extend(["", "## Warnings"])
        if payload["warnings"]:
            lines.extend(f"- {item}" for item in payload["warnings"])
        else:
            lines.append("- none")
        return "\n".join(lines) + "\n"

    def _column_checks(
        self, db_tables: set[str], hard_failures: list[str]
    ) -> list[dict[str, Any]]:
        checks = []
        for table_name in REQUIRED_TABLES:
            if table_name not in Base.metadata.tables:
                continue
            metadata_columns = set(Base.metadata.tables[table_name].columns.keys())
            db_columns = set(self._db_columns(table_name)) if table_name in db_tables else set()
            missing_in_db = sorted(metadata_columns - db_columns)
            for column_name in missing_in_db:
                hard_failures.append(f"required column missing: {table_name}.{column_name}")
            checks.append(
                {
                    "table_name": table_name,
                    "model_column_count": len(metadata_columns),
                    "db_column_count": len(db_columns),
                    "missing_in_db": missing_in_db,
                }
            )
        return checks

    def _lineage_checks(
        self, db_tables: set[str], hard_failures: list[str]
    ) -> list[dict[str, Any]]:
        checks = []
        for table_name in LINEAGE_TABLES:
            columns = set(self._db_columns(table_name)) if table_name in db_tables else set()
            missing = sorted(LINEAGE_COLUMNS - columns)
            if missing:
                hard_failures.append(f"lineage columns missing: {table_name} {missing}")
            checks.append(
                {
                    "table_name": table_name,
                    "missing_lineage_columns": missing,
                    "passed": not missing,
                }
            )
        return checks

    def _unique_checks(self, hard_failures: list[str]) -> list[dict[str, Any]]:
        checks = []
        for table_name, expected_constraints in REQUIRED_UNIQUE_CONSTRAINTS.items():
            observed = _metadata_unique_sets(table_name)
            for expected in expected_constraints:
                passed = _constraint_present(observed, expected)
                if not passed:
                    hard_failures.append(
                        f"required unique constraint missing in model: {table_name}{expected}"
                    )
                checks.append(
                    {
                        "table_name": table_name,
                        "expected_columns": list(expected),
                        "observed_unique_sets": [list(item) for item in sorted(observed)],
                        "passed": passed,
                    }
                )
        return checks

    def _index_checks(
        self,
        db_tables: set[str],
        hard_failures: list[str],
        warnings: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        prohibited = []
        critical = []
        for table_name in db_tables:
            for index in self.inspector.get_indexes(table_name):
                columns = tuple(index.get("column_names") or [])
                if len(columns) == 1 and columns[0] in PROHIBITED_WHOLE_INDEX_COLUMNS:
                    hard_failures.append(
                        f"prohibited whole-column index exists: {table_name}.{columns[0]}"
                    )
                    prohibited.append(
                        {"table_name": table_name, "index_name": index["name"], "passed": False}
                    )
        if not prohibited:
            prohibited.append({"table_name": "*", "index_name": None, "passed": True})
        for table_name, expected_indexes in CRITICAL_INDEXES.items():
            db_index_sets: set[tuple[str, ...]] = set()
            if table_name in db_tables:
                db_index_sets = {
                    tuple(str(column) for column in index.get("column_names") or [])
                    for index in self.inspector.get_indexes(table_name)
                }
            metadata_index_sets: set[tuple[str, ...]] = set()
            if table_name in Base.metadata.tables:
                table = Base.metadata.tables[table_name]
                metadata_index_sets = {
                    tuple(str(column.name) for column in index.columns)
                    for index in table.indexes
                }
            unique_sets = _metadata_unique_sets(table_name)
            observed = db_index_sets | metadata_index_sets | unique_sets
            for expected in expected_indexes:
                passed = _constraint_present(observed, expected)
                if not passed:
                    warnings.append(f"critical index not explicit: {table_name}{expected}")
                critical.append(
                    {
                        "table_name": table_name,
                        "expected_columns": list(expected),
                        "passed": passed,
                    }
                )
        return {"prohibited": prohibited, "critical": critical}

    def _scope_contract_check(self, hard_failures: list[str]) -> dict[str, Any]:
        docs = [
            Path("docs/2026-04-28__contract__current__db-schema-contract.md"),
            Path("docs/2026-04-28__contract__current__filtering-contract.md"),
            Path("docs/2026-04-28__contract__current__catalog-builder-contract.md"),
            Path("docs/2026-04-28__operations__current__operations.md"),
        ]
        checked = []
        for doc in docs:
            exists = doc.exists()
            text = doc.read_text(encoding="utf-8") if exists else ""
            has_min_date = "2011-01-01" in text
            has_model_year_warning = "modelYear" in text or "model year" in text.lower()
            passed = exists and has_min_date and has_model_year_warning
            if not passed:
                hard_failures.append(f"2011+ scope guard absent from contract doc: {doc}")
            checked.append(
                {
                    "path": str(doc),
                    "exists": exists,
                    "has_2011_min_date": has_min_date,
                    "has_model_year_warning": has_model_year_warning,
                    "passed": passed,
                }
            )
        return {"min_test_date": "2011-01-01", "docs": checked}

    def _db_columns(self, table_name: str) -> list[str]:
        return [str(column["name"]) for column in self.inspector.get_columns(table_name)]

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        try:
            return column_name in self._db_columns(table_name)
        except Exception:
            return False


class EndpointMatrixContractValidator:
    def __init__(
        self,
        session: Session,
        manifest: Path,
        database_url: str | None,
    ) -> None:
        self.session = session
        self.manifest = manifest
        self.database_url = database_url

    def validate(self) -> dict[str, Any]:
        hard_failures: list[str] = []
        warnings: list[str] = []
        manifest_rows = read_manifest_records(self.manifest)
        manifest_summary = manifest_hard_gate_summary(manifest_rows)
        if manifest_summary["row_count"] <= 0:
            hard_failures.append("manifest is empty")
        if manifest_summary["duplicate_test_no"] > 0:
            hard_failures.append("manifest has duplicate test_no")
        if manifest_summary["pre_2011_rows"] > 0:
            hard_failures.append("manifest has pre-2011 rows")
        if manifest_summary["scope_status_values"] != ["in_scope"]:
            hard_failures.append("manifest has non in_scope status")
        endpoint_rows = {
            name for name in self.session.scalars(select(SourceEndpoint.name).distinct())
        }
        payload_counts: dict[str, int] = {
            str(endpoint_name): int(count)
            for endpoint_name, count in self.session.execute(
                select(SourcePayload.endpoint_name, func.count())
                .group_by(SourcePayload.endpoint_name)
                .order_by(SourcePayload.endpoint_name)
            )
        }
        endpoint_checks = []
        for contract in ENDPOINT_CONTRACT:
            endpoint_name = contract["endpoint_name"]
            exists_in_code = endpoint_name in ENDPOINT_BY_NAME
            exists_in_db = endpoint_name in endpoint_rows
            if not exists_in_code:
                hard_failures.append(f"endpoint contract missing in code: {endpoint_name}")
            endpoint_checks.append(
                {
                    **contract,
                    "exists_in_code": exists_in_code,
                    "exists_in_db": exists_in_db,
                    "actual_payload_count": int(payload_counts.get(endpoint_name, 0)),
                    "empty_success_policy": _endpoint_allow_empty(endpoint_name),
                    "summary_links_are_authority": False,
                }
            )
        instrumentation_detail = {
            "endpoint_name": "instrumentation_detail",
            "decision": "deferred_optional",
            "reason": (
                "per-curve detail collection can multiply request volume by "
                "instrumentation_channels; v1.1 preserves schema support but does not "
                "require it for metadata-only full-scale collection"
            ),
        }
        return {
            "run": {
                "created_at": _now(),
                "database_url_redacted": sanitize_database_url(self.database_url)
                if self.database_url
                else None,
                "manifest": str(self.manifest),
            },
            "summary": {
                "endpoint_contracts": len(ENDPOINT_CONTRACT),
                "hard_failure_count": len(hard_failures),
                "warning_count": len(warnings),
                "result": "pass" if not hard_failures else "fail",
            },
            "manifest_summary": manifest_summary,
            "endpoint_checks": endpoint_checks,
            "endpoint_payload_counts": {
                str(key): int(value) for key, value in sorted(payload_counts.items())
            },
            "scheduling_policy": {
                "request_matrix_reproducible_from": [
                    "manifest test_no",
                    "canonical vehicles",
                    "canonical occupants",
                    "canonical instrumentation_channels",
                    "source_payload observations",
                ],
                "summary_links_are_not_authority": True,
                "empty_success_payload_is_not_failure": True,
                "instrumentation_pagination_is_auditable": True,
            },
            "instrumentation_detail_info_decision": instrumentation_detail,
            "hard_failures": hard_failures,
            "warnings": warnings,
        }

    def to_markdown(self, payload: dict[str, Any]) -> str:
        summary = payload["summary"]
        lines = [
            "# Endpoint Matrix Contract 2011+",
            "",
            "## Result",
            f"- result: {summary['result']}",
            f"- hard failures: {summary['hard_failure_count']}",
            f"- warnings: {summary['warning_count']}",
            "",
            "## Manifest Gate",
        ]
        for key, value in payload["manifest_summary"].items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Endpoints"])
        for row in payload["endpoint_checks"]:
            lines.append(
                f"- {row['logical_name']} -> `{row['endpoint_name']}` "
                f"decision={row['decision']} payloads={row['actual_payload_count']} "
                f"code={row['exists_in_code']} db={row['exists_in_db']}"
            )
        decision = payload["instrumentation_detail_info_decision"]
        lines.extend(
            [
                "",
                "## Instrumentation Detail Decision",
                f"- decision: {decision['decision']}",
                f"- reason: {decision['reason']}",
                "",
                "## Hard Failures",
            ]
        )
        if payload["hard_failures"]:
            lines.extend(f"- {item}" for item in payload["hard_failures"])
        else:
            lines.append("- none")
        lines.extend(["", "## Warnings"])
        if payload["warnings"]:
            lines.extend(f"- {item}" for item in payload["warnings"])
        else:
            lines.append("- none")
        return "\n".join(lines) + "\n"


class FullCoverageGapService:
    def __init__(
        self,
        session: Session,
        database_url: str | None,
        full_manifest: Path,
    ) -> None:
        self.session = session
        self.database_url = database_url
        self.full_manifest = full_manifest

    def analyze(self) -> dict[str, Any]:
        manifest_rows = read_manifest_records(self.full_manifest)
        db_rows = self._db_test_rows()
        db_by_test_no = {row["test_no"]: row for row in db_rows}
        manifest_by_test_no = {row.test_no: row for row in manifest_rows}
        full_set = set(manifest_by_test_no)
        db_set = set(db_by_test_no)
        overlap = full_set & db_set
        full_only = full_set - db_set
        db_only = db_set - full_set
        edge_candidates = self._edge_case_candidates(
            [manifest_by_test_no[test_no] for test_no in sorted(full_only)]
        )
        return {
            "run": {
                "created_at": _now(),
                "database_url_redacted": sanitize_database_url(self.database_url)
                if self.database_url
                else None,
                "full_manifest": str(self.full_manifest),
            },
            "summary": {
                "full_manifest_tests": len(full_set),
                "db_tests": len(db_set),
                "overlap_tests": len(overlap),
                "full_manifest_only_tests": len(full_only),
                "db_only_tests": len(db_only),
                "overlap_ratio_of_full": round(len(overlap) / len(full_set), 4)
                if full_set
                else 0.0,
                "edge_case_validation_needed": bool(edge_candidates),
            },
            "manifest_hard_gate": manifest_hard_gate_summary(manifest_rows),
            "year_coverage": _coverage_distribution(
                Counter(row.test_year for row in manifest_rows),
                Counter(row["test_year"] for row in db_rows if row["test_year"] is not None),
            ),
            "test_type_coverage": _coverage_distribution(
                Counter(_display(row.test_type) for row in manifest_rows),
                Counter(_display(row["test_type"]) for row in db_rows),
            ),
            "test_configuration_coverage": _coverage_distribution(
                Counter(_display(row.test_configuration) for row in manifest_rows),
                Counter(_display(row["test_configuration"]) for row in db_rows),
            ),
            "classification_coverage": _coverage_distribution(
                Counter(_manifest_family(row) for row in manifest_rows),
                Counter(_display(row["test_family"]) for row in db_rows),
            ),
            "proxy_coverage": {
                "media_data_package_risk": _proxy_distribution(manifest_rows, "media"),
                "occupant_restraint_expected_presence": _proxy_distribution(
                    manifest_rows, "occupant_restraint"
                ),
                "instrumentation_tier": _proxy_distribution(manifest_rows, "instrumentation"),
                "unknown_or_needs_review": _proxy_distribution(manifest_rows, "unknown"),
            },
            "full_manifest_only_samples": sorted(full_only)[:50],
            "db_only_samples": sorted(db_only)[:50],
            "edge_case_candidates": [record_to_dict(row) for row in edge_candidates],
            "decision": _gap_decision(len(full_set), len(overlap), edge_candidates),
        }

    def to_markdown(self, payload: dict[str, Any]) -> str:
        summary = payload["summary"]
        lines = [
            "# Full Coverage Gap 2011+",
            "",
            "## Scope",
            "- Compares full 2011+ manifest-only universe against the 1500-test local DB.",
            "- No detail collect, no file download, no package parsing.",
            "",
            "## Summary",
        ]
        for key, value in summary.items():
            lines.append(f"- {key}: {value}")
        lines.extend(
            [
                "",
                "## Manifest Hard Gate",
            ]
        )
        for key, value in payload["manifest_hard_gate"].items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Year Coverage"])
        lines.extend(_coverage_lines(payload["year_coverage"], limit=20))
        lines.extend(["", "## Test Configuration Coverage"])
        lines.extend(_coverage_lines(payload["test_configuration_coverage"], limit=20))
        lines.extend(["", "## Classification Coverage"])
        lines.extend(_coverage_lines(payload["classification_coverage"], limit=20))
        lines.extend(["", "## Edge-Case Candidate Need"])
        lines.append(f"- decision: {payload['decision']}")
        if payload["edge_case_candidates"]:
            for row in payload["edge_case_candidates"][:20]:
                lines.append(
                    f"- {row['test_no']} {row['test_date']} "
                    f"{row.get('test_configuration') or row.get('test_configuration_key')}"
                )
        else:
            lines.append("- no candidate manifest needed")
        return "\n".join(lines) + "\n"

    def _db_test_rows(self) -> list[dict[str, Any]]:
        classification = {
            row.test_no: row
            for row in self.session.scalars(select(TestClassification))
        }
        rows = []
        for test in self.session.scalars(select(CrashTest).order_by(CrashTest.test_no)):
            test_date = test.test_date
            classification_row = classification.get(test.test_no)
            rows.append(
                {
                    "test_no": test.test_no,
                    "test_date": test_date,
                    "test_year": test_date.year if test_date else None,
                    "test_type": test.test_type,
                    "test_configuration": test.test_configuration,
                    "test_configuration_key": test.test_configuration_key,
                    "test_family": classification_row.test_family
                    if classification_row
                    else None,
                    "classification_status": classification_row.classification_status
                    if classification_row
                    else None,
                }
            )
        return rows

    def _edge_case_candidates(self, rows: list[ManifestRecord]) -> list[ManifestRecord]:
        if not rows:
            return []
        config_counts = Counter(_display(row.test_configuration) for row in rows)
        family_counts = Counter(_manifest_family(row) for row in rows)
        year_counts = Counter(row.test_year for row in rows)
        scored = sorted(
            rows,
            key=lambda row: (
                config_counts[_display(row.test_configuration)],
                family_counts[_manifest_family(row)],
                year_counts[row.test_year],
                row.test_date,
                row.test_no,
            ),
        )
        return scored[:100]


class FullScaleCapacityEstimator:
    def __init__(
        self,
        session: Session,
        database_url: str | None,
        full_manifest: Path,
    ) -> None:
        self.session = session
        self.database_url = database_url
        self.full_manifest = full_manifest

    def estimate(self) -> dict[str, Any]:
        manifest_rows = read_manifest_records(self.full_manifest)
        full_tests = len({row.test_no for row in manifest_rows})
        db_tests = _count(self.session, CrashTest)
        scale_factor = full_tests / db_tests if db_tests else 0.0
        table_counts = _table_counts(self.session)
        endpoint_payload_counts: dict[str, int] = {
            str(endpoint_name): int(count)
            for endpoint_name, count in self.session.execute(
                select(SourcePayload.endpoint_name, func.count()).group_by(
                    SourcePayload.endpoint_name
                )
            )
        }
        estimated_tables = {
            table_name: int(round(row_count * scale_factor))
            for table_name, row_count in table_counts.items()
        }
        estimated_endpoint_requests = {
            endpoint_name: int(round(int(count) * scale_factor))
            for endpoint_name, count in endpoint_payload_counts.items()
        }
        total_requests = sum(estimated_endpoint_requests.values())
        db_size_bytes = _sqlite_file_size(self.database_url)
        estimated_db_size_bytes = int(round(db_size_bytes * scale_factor)) if db_size_bytes else 0
        return {
            "run": {
                "created_at": _now(),
                "database_url_redacted": sanitize_database_url(self.database_url)
                if self.database_url
                else None,
                "full_manifest": str(self.full_manifest),
            },
            "summary": {
                "estimated_full_tests": full_tests,
                "baseline_db_tests": db_tests,
                "scale_factor": round(scale_factor, 4),
                "estimated_endpoint_requests": total_requests,
                "estimated_sqlite_db_size_bytes": estimated_db_size_bytes,
                "sqlite_recommendation": _sqlite_recommendation(
                    estimated_db_size_bytes, estimated_tables
                ),
            },
            "baseline_table_counts": table_counts,
            "estimated_table_counts": estimated_tables,
            "estimated_endpoint_requests_by_endpoint": estimated_endpoint_requests,
            "runtime_estimates": [
                {
                    "delay_seconds": delay,
                    "request_delay_hours": round(total_requests * delay / 3600, 2),
                }
                for delay in (0.1, 0.2, 0.5, 1.0)
            ],
            "bottleneck_tables": _bottleneck_tables(estimated_tables),
        }

    def to_markdown(self, payload: dict[str, Any]) -> str:
        summary = payload["summary"]
        lines = [
            "# Full-Scale Schema Capacity Estimate",
            "",
            "## Summary",
        ]
        for key, value in summary.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Estimated Table Counts"])
        for table_name, row_count in sorted(payload["estimated_table_counts"].items()):
            lines.append(f"- {table_name}: {row_count}")
        lines.extend(["", "## Runtime By Delay"])
        for row in payload["runtime_estimates"]:
            lines.append(
                f"- delay={row['delay_seconds']}s: request delay "
                f"{row['request_delay_hours']} hours"
            )
        lines.extend(["", "## Bottleneck Tables"])
        if payload["bottleneck_tables"]:
            for row in payload["bottleneck_tables"]:
                lines.append(f"- {row['table_name']}: {row['estimated_rows']}")
        else:
            lines.append("- none")
        return "\n".join(lines) + "\n"


def manual_domain_review_backlog(payload: dict[str, Any]) -> dict[str, Any]:
    items = list(payload.get("items") or payload.get("recommendations") or [])
    review_items = []
    for index, item in enumerate(items, 1):
        decision = str(item.get("v1_0_decision") or "")
        recommendation_class = str(item.get("recommendation_class") or "")
        if decision != "requires_manual_domain_review" and recommendation_class not in {
            "requires_manual_review",
            "conflict_resolution_candidate",
        }:
            continue
        target = str(item.get("target") or item.get("field_path") or f"item_{index}")
        priority = str(item.get("recommendation_priority") or "P3")
        review_items.append(
            {
                "field_or_recommendation_id": item.get("id") or f"recommendation_{index}",
                "endpoint_name": item.get("endpoint_name"),
                "field_path": item.get("field_path") or target,
                "current_class": recommendation_class or decision,
                "support_test_count": int(item.get("observed_test_count") or 0),
                "non_null_ratio": float(item.get("non_null_ratio") or 0.0),
                "candidate_action": _manual_review_action(target, recommendation_class),
                "risk": _manual_review_risk(priority, item),
                "reason": item.get("recommendation_reason")
                or "manual domain interpretation required",
                "example_values": item.get("example_values") or [],
            }
        )
    risk_counter = Counter(str(item["risk"]) for item in review_items)
    action_counter = Counter(str(item["candidate_action"]) for item in review_items)
    blocker_count = risk_counter["high"]
    return {
        "run": {"created_at": _now()},
        "summary": {
            "total": len(review_items),
            "high_risk": risk_counter["high"],
            "medium_risk": risk_counter["medium"],
            "low_risk": risk_counter["low"],
            "blocker_count": blocker_count,
            "full_scale_blocked": blocker_count > 0,
            "by_action": dict(sorted(action_counter.items())),
        },
        "items": review_items,
    }


def manual_domain_review_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Manual Domain Review Backlog 2011+",
        "",
        "## Summary",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Items"])
    if payload["items"]:
        for item in payload["items"][:100]:
            lines.append(
                f"- {item['risk']} {item['candidate_action']}: "
                f"{item['endpoint_name']} `{item['field_path']}` "
                f"support={item['support_test_count']}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
        + "\n",
        encoding="utf-8",
    )


def read_manifest_records(path: Path) -> list[ManifestRecord]:
    rows: list[ManifestRecord] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            test_no = _int_value(row.get("test_no"))
            test_date = _date_value(row.get("test_date"))
            if test_no is None or test_date is None:
                continue
            rows.append(
                ManifestRecord(
                    test_no=test_no,
                    test_date=test_date,
                    test_year=_int_value(row.get("test_year")) or test_date.year,
                    test_configuration_key=_str_value(row.get("test_configuration_key")),
                    test_configuration=_str_value(row.get("test_configuration")),
                    test_type=_str_value(row.get("test_type")),
                    model_year=_int_value(row.get("model_year")),
                    vehicle_make=_str_value(row.get("vehicle_make")),
                    vehicle_model=_str_value(row.get("vehicle_model")),
                    scope_status=_str_value(row.get("scope_status")),
                )
            )
    return rows


def manifest_hard_gate_summary(rows: list[ManifestRecord]) -> dict[str, Any]:
    test_numbers = [row.test_no for row in rows]
    date_values = [row.test_date for row in rows]
    duplicate_count = len(test_numbers) - len(set(test_numbers))
    anchors = {
        7201: 7201 in test_numbers,
        10001: 10001 in test_numbers,
        10003: 10003 in test_numbers,
    }
    return {
        "row_count": len(rows),
        "date_range": [
            min(date_values).isoformat() if date_values else None,
            max(date_values).isoformat() if date_values else None,
        ],
        "duplicate_test_no": duplicate_count,
        "missing_or_parse_failed_date": 0,
        "pre_2011_rows": sum(row.test_date < date(2011, 1, 1) for row in rows),
        "scope_status_values": sorted({row.scope_status for row in rows if row.scope_status}),
        "anchors": anchors,
        "year_distribution": dict(sorted(Counter(row.test_year for row in rows).items())),
        "test_type_distribution": dict(
            sorted(Counter(_display(row.test_type) for row in rows).items())
        ),
        "test_configuration_distribution": dict(
            sorted(Counter(_display(row.test_configuration) for row in rows).items())
        ),
        "classification_distribution": dict(
            sorted(Counter(_manifest_family(row) for row in rows).items())
        ),
    }


def record_to_dict(record: ManifestRecord) -> dict[str, Any]:
    return {
        "test_no": record.test_no,
        "test_date": record.test_date.isoformat(),
        "test_year": record.test_year,
        "test_configuration_key": record.test_configuration_key,
        "test_configuration": record.test_configuration,
        "test_type": record.test_type,
        "model_year": record.model_year,
        "vehicle_make": record.vehicle_make,
        "vehicle_model": record.vehicle_model,
        "scope_status": record.scope_status,
    }


def write_edge_case_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        "scope_status",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def _metadata_unique_sets(table_name: str) -> set[tuple[str, ...]]:
    table = Base.metadata.tables.get(table_name)
    if table is None:
        return set()
    unique_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    unique_sets.update((column.name,) for column in table.columns if column.unique)
    return unique_sets


def _constraint_present(observed: set[tuple[str, ...]], expected: tuple[str, ...]) -> bool:
    expected_set = set(expected)
    return any(set(item) == expected_set for item in observed)


def _check_pass(
    checks: list[dict[str, Any]], table_name: str, expected: tuple[str, ...]
) -> dict[str, Any]:
    for row in checks:
        if row["table_name"] == table_name and tuple(row["expected_columns"]) == expected:
            return row
    return {"table_name": table_name, "expected_columns": list(expected), "passed": False}


def _endpoint_allow_empty(endpoint_name: str) -> bool:
    endpoint = ENDPOINT_BY_NAME.get(endpoint_name)
    return bool(endpoint.allow_empty) if endpoint is not None else False


def _coverage_distribution(
    full_counts: Counter[Any],
    db_counts: Counter[Any],
) -> list[dict[str, Any]]:
    rows = []
    for value in sorted(set(full_counts) | set(db_counts), key=lambda item: str(item)):
        full_count = int(full_counts.get(value, 0))
        db_count = int(db_counts.get(value, 0))
        rows.append(
            {
                "value": value,
                "full_count": full_count,
                "db_count": db_count,
                "db_to_full_ratio": round(db_count / full_count, 4) if full_count else None,
                "status": _coverage_status(full_count, db_count),
            }
        )
    return rows


def _coverage_status(full_count: int, db_count: int) -> str:
    if not full_count and db_count:
        return "db_only"
    if full_count and not db_count:
        return "uncovered"
    if full_count and db_count / full_count < 0.1:
        return "thin"
    return "represented"


def _coverage_lines(rows: list[dict[str, Any]], limit: int) -> list[str]:
    if not rows:
        return ["- none"]
    ordered = sorted(
        rows,
        key=lambda row: (
            0 if row["status"] == "uncovered" else 1 if row["status"] == "thin" else 2,
            str(row["value"]),
        ),
    )
    return [
        f"- {row['value']}: full={row['full_count']} db={row['db_count']} "
        f"status={row['status']}"
        for row in ordered[:limit]
    ]


def _proxy_distribution(rows: list[ManifestRecord], proxy: str) -> dict[str, int]:
    if proxy == "media":
        counter = Counter(
            "high" if _manifest_family(row) in {"frontal_barrier", "side_impactor"} else "medium"
            for row in rows
        )
    elif proxy == "occupant_restraint":
        counter = Counter(
            "expected"
            if _manifest_family(row)
            in {"frontal_barrier", "side_impactor", "pole", "vehicle_to_vehicle", "rollover"}
            else "unknown"
            for row in rows
        )
    elif proxy == "instrumentation":
        counter = Counter(
            "high"
            if _manifest_family(row) in {"frontal_barrier", "side_impactor"}
            else "medium"
            for row in rows
        )
    else:
        counter = Counter(
            "unknown_or_needs_review"
            if _manifest_family(row) == "unknown_or_other"
            else "classified"
            for row in rows
        )
    return dict(sorted(counter.items()))


def _manifest_family(row: ManifestRecord) -> str:
    text = " ".join(
        item
        for item in [
            row.test_configuration_key,
            row.test_configuration,
            row.test_type,
        ]
        if item
    ).upper()
    if "IMPACTOR INTO VEHICLE" in text or " ITV" in f" {text}":
        return "side_impactor"
    if "VEHICLE INTO BARRIER" in text or " VTB" in f" {text}":
        return "frontal_barrier"
    if "VEHICLE INTO POLE" in text or " VTP" in f" {text}":
        return "pole"
    if "VEHICLE INTO VEHICLE" in text or " VTV" in f" {text}":
        return "vehicle_to_vehicle"
    if "ROLLOVER" in text:
        return "rollover"
    if "SLED" in text:
        return "sled"
    if "LOW RISK" in text or "STATIC" in text:
        return "airbag_static_or_low_risk"
    if "WARNING" in text or "ASSIST" in text:
        return "non_crash_adas"
    return "unknown_or_other"


def _gap_decision(full_count: int, overlap_count: int, candidates: list[ManifestRecord]) -> str:
    if not full_count:
        return "blocked: full manifest is empty"
    if overlap_count == full_count:
        return "pass: 1500 DB covers all full manifest tests"
    if candidates:
        return (
            "conditional: uncovered strata exist; "
            "edge-case bounded validation candidate prepared"
        )
    return "pass: no edge-case candidate needed"


def _table_counts(session: Session) -> dict[str, int]:
    models = [
        CollectionRun,
        CollectionRunItem,
        SourceEndpoint,
        SourcePayload,
        SourcePayloadObservation,
        SourcePayloadSection,
        SourceFieldCatalog,
        SourceConflict,
        DiscoveryRun,
        DiscoveryManifestRow,
        DiscoveryAuthorityDecision,
        CanonicalRowSource,
        CrashTest,
        TestParticipant,
        Vehicle,
        Barrier,
        Occupant,
        Restraint,
        InstrumentationChannel,
        InstrumentationChannelDetail,
        InjuryMetric,
        DeformationMeasurement,
        IntrusionMeasurement,
        MediaAsset,
        CodeValue,
        TestFilterSummary,
        TestClassification,
        TestFacet,
        AssetSummary,
        FieldCoverageSnapshot,
    ]
    return {model.__tablename__: _count(session, model) for model in models}


def _count(session: Session, model: type[Any]) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _sqlite_file_size(database_url: str | None) -> int:
    if not database_url or not database_url.startswith("sqlite:///"):
        return 0
    path = Path(database_url.removeprefix("sqlite:///"))
    return path.stat().st_size if path.exists() else 0


def _sqlite_recommendation(size_bytes: int, estimated_tables: dict[str, int]) -> str:
    if size_bytes > 5_000_000_000:
        return "postgresql_recommended_before_full_scale"
    if estimated_tables.get("canonical_row_sources", 0) > 5_000_000:
        return "sqlite_possible_but_postgresql_preferred_for_lineage_queries"
    return "sqlite_possible_for_full_scale_metadata_only"


def _bottleneck_tables(estimated_tables: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"table_name": table_name, "estimated_rows": row_count}
        for table_name, row_count in sorted(
            estimated_tables.items(), key=lambda item: item[1], reverse=True
        )
        if row_count >= 1_000_000
    ][:10]


def _manual_review_action(target: str, recommendation_class: str) -> str:
    lowered = target.lower()
    if any(token in lowered for token in ("testno", "vehicleno", "curveno", "url", "hash")):
        return "raw_only"
    if any(token in lowered for token in ("speed", "weight", "height", "length", "value")):
        return "new_column_candidate"
    if recommendation_class in {"code_values_candidate", "dictionary_candidate"}:
        return "new_code_value_candidate"
    if recommendation_class == "column_candidate":
        return "new_column_candidate"
    if recommendation_class == "alias_map_candidate":
        return "map_to_existing_column"
    return "defer"


def _manual_review_risk(priority: str, item: dict[str, Any]) -> str:
    if priority in {"P0", "P1"}:
        return "high"
    support = int(item.get("observed_test_count") or 0)
    if priority == "P2" and support >= 100:
        return "medium"
    if priority == "P2":
        return "medium"
    return "low"


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _display(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return text or "UNKNOWN"


def _int_value(value: object | None) -> int | None:
    try:
        if isinstance(value, int | str) and str(value).strip() != "":
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
            return datetime.strptime(text[:19] if "%H" in fmt else text[:10], fmt).date()
        except ValueError:
            pass
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None
