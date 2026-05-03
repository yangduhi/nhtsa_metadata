"""schema v1.6 evidence lineage

Revision ID: 0004_schema_v1_6_lineage
Revises: 0003_classification_disposition
Create Date: 2026-05-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import JSON, Column, ForeignKey, Integer, Numeric, String, Text, inspect

revision = "0004_schema_v1_6_lineage"
down_revision = "0003_classification_disposition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "classification_evidence" not in tables:
        op.create_table(
            "classification_evidence",
            Column("id", Integer, primary_key=True),
            Column("source_system", String(64), nullable=False),
            Column("canonical_test_uid", String(120), nullable=False),
            Column("test_no", Integer, nullable=False),
            Column("classifier_version", String(32), nullable=False),
            Column("evidence_stage", String(64), nullable=False),
            Column("source_payload_id", Integer, ForeignKey("source_payloads.id"), nullable=True),
            Column("source_endpoint_name", String(120), nullable=True),
            Column("source_field_path", Text, nullable=True),
            Column("normalized_feature_key", String(160), nullable=True),
            Column("candidate_rule_id", String(160), nullable=True),
            Column("final_status", String(64), nullable=False),
            Column("disposition_status", String(64), nullable=False),
            Column("evidence_json", JSON, nullable=True),
        )
        op.create_index(
            "ix_classification_evidence_canonical_test_uid",
            "classification_evidence",
            ["canonical_test_uid"],
        )
        op.create_index(
            "ix_classification_evidence_test_no", "classification_evidence", ["test_no"]
        )
    _create_table_if_missing(
        tables,
        "canonical_label_registry",
        [
            Column("id", Integer, primary_key=True),
            Column("canonical_label", String(160), nullable=False),
            Column("registry_version", String(32), nullable=False),
            Column("label_domain", String(120), nullable=False),
            Column("label_status", String(64), nullable=False),
            Column("definition", Text, nullable=False),
            Column("source_rule_id", String(160), nullable=True),
        ],
    )
    _create_table_if_missing(
        tables,
        "rule_registry",
        [
            Column("id", Integer, primary_key=True),
            Column("rule_id", String(160), nullable=False),
            Column("rule_version", String(32), nullable=False),
            Column("canonical_label", String(160), nullable=False),
            Column("rule_family_id", String(160), nullable=True),
            Column("rule_status", String(64), nullable=False),
            Column("evidence_gates_json", JSON, nullable=True),
        ],
    )
    _create_table_if_missing(
        tables,
        "program_standard_evidence",
        [
            Column("id", Integer, primary_key=True),
            Column("test_no", Integer, nullable=False),
            Column("program_domain", String(120), nullable=False),
            Column("standard_name", String(120), nullable=True),
            Column("evidence_json", JSON, nullable=True),
        ],
        index_columns=("test_no",),
    )
    _create_table_if_missing(
        tables,
        "test_event_domain",
        [
            Column("id", Integer, primary_key=True),
            Column("test_no", Integer, nullable=False),
            Column("domain_name", String(120), nullable=False),
            Column("domain_confidence", Numeric, nullable=True),
            Column("evidence_json", JSON, nullable=True),
        ],
        index_columns=("test_no",),
    )
    _create_table_if_missing(
        tables,
        "impact_device_evidence",
        [
            Column("id", Integer, primary_key=True),
            Column("test_no", Integer, nullable=False),
            Column("device_type", String(120), nullable=False),
            Column("evidence_json", JSON, nullable=True),
        ],
        index_columns=("test_no",),
    )
    _create_table_if_missing(
        tables,
        "restraint_equipment_evidence",
        [
            Column("id", Integer, primary_key=True),
            Column("test_no", Integer, nullable=False),
            Column("equipment_type", String(120), nullable=False),
            Column("evidence_json", JSON, nullable=True),
        ],
        index_columns=("test_no",),
    )
    _create_table_if_missing(
        tables,
        "classification_feature_evidence",
        [
            Column("id", Integer, primary_key=True),
            Column("canonical_test_uid", String(120), nullable=False),
            Column("test_no", Integer, nullable=False),
            Column("classifier_version", String(32), nullable=False),
            Column("normalized_text", Text, nullable=True),
            Column("normalized_features_json", JSON, nullable=True),
            Column("source_payload_ids_json", JSON, nullable=True),
            Column("source_field_paths_json", JSON, nullable=True),
            Column("extraction_warnings_json", JSON, nullable=True),
        ],
        index_columns=("canonical_test_uid", "test_no"),
    )


def downgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    for table_name in (
        "classification_feature_evidence",
        "restraint_equipment_evidence",
        "impact_device_evidence",
        "test_event_domain",
        "program_standard_evidence",
        "rule_registry",
        "canonical_label_registry",
        "classification_evidence",
    ):
        if table_name in tables:
            op.drop_table(table_name)


def _create_table_if_missing(
    tables: set[str],
    table_name: str,
    columns: Sequence[Column[object]],
    *,
    index_columns: Sequence[str] = (),
) -> None:
    if table_name in tables:
        return
    op.create_table(table_name, *columns)
    for column in index_columns:
        op.create_index(f"ix_{table_name}_{column}", table_name, [column])
