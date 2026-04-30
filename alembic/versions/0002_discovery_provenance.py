"""discovery provenance

Revision ID: 0002_discovery_provenance
Revises: 0001_initial_schema
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    inspect,
)

revision = "0002_discovery_provenance"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    if "discovery_runs" not in existing:
        op.create_table(
            "discovery_runs",
            Column("id", Integer, primary_key=True),
            Column("run_kind", String(64), nullable=False),
            Column("source_authority", String(64), nullable=False),
            Column("min_test_date", Date, nullable=True),
            Column("year_from", Integer, nullable=True),
            Column("year_to", Integer, nullable=True),
            Column("reference_database_path_hash", String(64), nullable=True),
            Column("command_json", JSON, nullable=True),
            Column("manifest_path", Text, nullable=True),
            Column("manifest_hash", String(64), nullable=True),
            Column("started_at", DateTime, nullable=True),
            Column("ended_at", DateTime, nullable=True),
            Column("status", String(32), nullable=False),
            Column("total_rows", Integer, nullable=False),
            Column("in_scope_count", Integer, nullable=False),
            Column("out_of_scope_count", Integer, nullable=False),
            Column("duplicate_test_no_count", Integer, nullable=False),
            Column("missing_date_count", Integer, nullable=False),
            Column("parse_failed_date_count", Integer, nullable=False),
            Column("date_range_start", Date, nullable=True),
            Column("date_range_end", Date, nullable=True),
            Column("git_commit", String(64), nullable=True),
            Column("software_version", String(64), nullable=True),
            Column("extra_json", JSON, nullable=True),
            Column("created_at", DateTime, nullable=False),
            Column("updated_at", DateTime, nullable=True),
        )
        op.create_index("ix_discovery_runs_run_kind", "discovery_runs", ["run_kind"])
        op.create_index("ix_discovery_runs_manifest_hash", "discovery_runs", ["manifest_hash"])
    if "discovery_manifest_rows" not in existing:
        op.create_table(
            "discovery_manifest_rows",
            Column("id", Integer, primary_key=True),
            Column(
                "discovery_run_id",
                Integer,
                ForeignKey("discovery_runs.id"),
                nullable=False,
            ),
            Column("test_no", Integer, nullable=False),
            Column("test_date_raw", String(120), nullable=True),
            Column("test_date", Date, nullable=True),
            Column("test_date_parse_status", String(32), nullable=False),
            Column("scope_status", String(32), nullable=False),
            Column("test_configuration", Text, nullable=True),
            Column("test_configuration_key", String(64), nullable=True),
            Column("test_type", Text, nullable=True),
            Column("model_year", Integer, nullable=True),
            Column("vehicle_make", Text, nullable=True),
            Column("vehicle_model", Text, nullable=True),
            Column("seed_source", String(64), nullable=False),
            Column("live_by_search_present", Boolean, nullable=False),
            Column("reference_present", Boolean, nullable=False),
            Column("live_validation_present", Boolean, nullable=False),
            Column("validation_status", String(64), nullable=True),
            Column("validation_endpoint", String(120), nullable=True),
            Column("authority_status", String(64), nullable=False),
            Column("selection_status", String(64), nullable=False),
            Column("rejection_reason", Text, nullable=True),
            Column("row_hash", String(64), nullable=False),
            Column("extra_json", JSON, nullable=True),
            Column("created_at", DateTime, nullable=False),
            Column("updated_at", DateTime, nullable=True),
            UniqueConstraint("discovery_run_id", "test_no"),
            UniqueConstraint("discovery_run_id", "row_hash"),
        )
        op.create_index(
            "ix_discovery_manifest_rows_discovery_run_id",
            "discovery_manifest_rows",
            ["discovery_run_id"],
        )
        op.create_index(
            "ix_discovery_manifest_rows_test_no",
            "discovery_manifest_rows",
            ["test_no"],
        )
        op.create_index(
            "ix_discovery_manifest_rows_authority_status",
            "discovery_manifest_rows",
            ["authority_status"],
        )
        op.create_index(
            "ix_discovery_manifest_rows_row_hash",
            "discovery_manifest_rows",
            ["row_hash"],
        )
    if "discovery_authority_decisions" not in existing:
        op.create_table(
            "discovery_authority_decisions",
            Column("id", Integer, primary_key=True),
            Column("decision_name", String(120), nullable=False),
            Column("decision_status", String(32), nullable=False),
            Column("selected_authority", String(64), nullable=False),
            Column("live_manifest_count", Integer, nullable=False),
            Column("reference_seed_count", Integer, nullable=False),
            Column("reference_only_count", Integer, nullable=False),
            Column("validated_supplement_count", Integer, nullable=False),
            Column("excluded_supplement_count", Integer, nullable=False),
            Column("final_manifest_count", Integer, nullable=False),
            Column("decision_reason", Text, nullable=False),
            Column("decided_at", DateTime, nullable=False),
            Column("git_commit", String(64), nullable=True),
            Column("extra_json", JSON, nullable=True),
            Column("created_at", DateTime, nullable=False),
            Column("updated_at", DateTime, nullable=True),
        )
        op.create_index(
            "ix_discovery_authority_decisions_decision_name",
            "discovery_authority_decisions",
            ["decision_name"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    if "discovery_authority_decisions" in existing:
        op.drop_index(
            "ix_discovery_authority_decisions_decision_name",
            table_name="discovery_authority_decisions",
        )
        op.drop_table("discovery_authority_decisions")
    if "discovery_manifest_rows" in existing:
        op.drop_index("ix_discovery_manifest_rows_row_hash", table_name="discovery_manifest_rows")
        op.drop_index(
            "ix_discovery_manifest_rows_authority_status",
            table_name="discovery_manifest_rows",
        )
        op.drop_index("ix_discovery_manifest_rows_test_no", table_name="discovery_manifest_rows")
        op.drop_index(
            "ix_discovery_manifest_rows_discovery_run_id",
            table_name="discovery_manifest_rows",
        )
        op.drop_table("discovery_manifest_rows")
    if "discovery_runs" in existing:
        op.drop_index("ix_discovery_runs_manifest_hash", table_name="discovery_runs")
        op.drop_index("ix_discovery_runs_run_kind", table_name="discovery_runs")
        op.drop_table("discovery_runs")
