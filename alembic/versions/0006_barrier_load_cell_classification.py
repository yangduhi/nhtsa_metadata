"""barrier load cell classification read model

Revision ID: 0006_barrier_load_cell_classification
Revises: 0005_vehicle_filter_fields
Create Date: 2026-05-03
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from alembic import op
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    inspect,
)
from sqlalchemy.schema import UniqueConstraint

revision = "0006_barrier_load_cell_classification"
down_revision = "0005_vehicle_filter_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "barrier_load_cell_classification" not in tables:
        op.create_table(
            "barrier_load_cell_classification",
            Column("id", Integer, primary_key=True),
            Column("test_id", Integer, ForeignKey("tests.id"), nullable=False),
            Column("test_no", Integer, nullable=False),
            Column("barrier_id", Integer, ForeignKey("barriers.id"), nullable=True),
            Column("config_version", String(120), nullable=False),
            Column("classification_id", String(160), nullable=False),
            Column("family", String(120), nullable=False),
            Column("classification_status", String(64), nullable=False),
            Column("raw_barrier_shape", Text, nullable=True),
            Column("normalized_barrier_shape_key", String(160), nullable=False),
            Column("shape_alias_rule_id", String(160), nullable=True),
            Column("shape_alias_confidence", Numeric, nullable=True),
            Column("shape_alias_is_conditional", Boolean, nullable=False, server_default="0"),
            Column("row_count", Integer, nullable=True),
            Column("col_count", Integer, nullable=True),
            Column("row_range_json", JSON, nullable=True),
            Column("col_range_json", JSON, nullable=True),
            Column("pole_index_range_json", JSON, nullable=True),
            Column("channel_count", Integer, nullable=False, server_default="0"),
            Column("force_channel_count", Integer, nullable=False, server_default="0"),
            Column("moment_channel_count", Integer, nullable=False, server_default="0"),
            Column("missing_expected_channels_json", JSON, nullable=True),
            Column("duplicate_channels_json", JSON, nullable=True),
            Column("occupancy_map_json", JSON, nullable=True),
            Column("mask_summary_json", JSON, nullable=True),
            Column("evidence_json", JSON, nullable=True),
            Column("created_at", DateTime, nullable=True),
            Column("updated_at", DateTime, nullable=True),
            UniqueConstraint("test_no", "config_version", "classification_id"),
        )
        op.create_index(
            "ix_barrier_load_cell_classification_test_id",
            "barrier_load_cell_classification",
            ["test_id"],
        )
        op.create_index(
            "ix_barrier_load_cell_classification_test_no",
            "barrier_load_cell_classification",
            ["test_no"],
        )
    if "barrier_load_cell_channel_map" not in tables:
        op.create_table(
            "barrier_load_cell_channel_map",
            Column("id", Integer, primary_key=True),
            Column(
                "classification_id",
                Integer,
                ForeignKey("barrier_load_cell_classification.id"),
                nullable=False,
            ),
            Column("test_id", Integer, ForeignKey("tests.id"), nullable=False),
            Column("test_no", Integer, nullable=False),
            Column(
                "instrumentation_channel_id",
                Integer,
                ForeignKey("instrumentation_channels.id"),
                nullable=False,
            ),
            Column("curve_no", Integer, nullable=False),
            Column("sensor_attachment_raw", Text, nullable=True),
            Column("instrumentation_commentary", Text, nullable=True),
            Column("parsed_row", Integer, nullable=True),
            Column("parsed_col", Integer, nullable=True),
            Column("parsed_row_letter", String(8), nullable=True),
            Column("parsed_pole_index", Integer, nullable=True),
            Column("quantity_type", String(32), nullable=False),
            Column("raw_axis", String(64), nullable=True),
            Column("canonical_axis", String(64), nullable=True),
            Column("unit_raw", String(120), nullable=True),
            Column("generated_loma_name", String(120), nullable=True),
            Column("mask_flags_json", JSON, nullable=True),
            Column("evidence_json", JSON, nullable=True),
            Column("created_at", DateTime, nullable=True),
            Column("updated_at", DateTime, nullable=True),
            UniqueConstraint("classification_id", "instrumentation_channel_id"),
        )
        op.create_index(
            "ix_barrier_load_cell_channel_map_classification_id",
            "barrier_load_cell_channel_map",
            ["classification_id"],
        )
        op.create_index(
            "ix_barrier_load_cell_channel_map_test_id",
            "barrier_load_cell_channel_map",
            ["test_id"],
        )
        op.create_index(
            "ix_barrier_load_cell_channel_map_test_no",
            "barrier_load_cell_channel_map",
            ["test_no"],
        )
    if "test_filter_summary" in tables:
        _add_columns_if_missing(
            "test_filter_summary",
            inspector,
            (
                Column("load_cell_barrier_classification_ids_json", JSON),
                Column("load_cell_barrier_families_json", JSON),
                Column("load_cell_barrier_config_version", String(120)),
                Column("load_cell_barrier_channel_count", Integer),
                Column("load_cell_barrier_force_channel_count", Integer),
                Column("load_cell_barrier_moment_channel_count", Integer),
            ),
        )


def downgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "barrier_load_cell_channel_map" in tables:
        op.drop_table("barrier_load_cell_channel_map")
    if "barrier_load_cell_classification" in tables:
        op.drop_table("barrier_load_cell_classification")


def _add_columns_if_missing(
    table_name: str,
    inspector: Any,
    columns: Sequence[Column[object]],
) -> None:
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column)
