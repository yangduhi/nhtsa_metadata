"""vehicle filter field promotion

Revision ID: 0005_vehicle_filter_fields
Revises: 0004_schema_v1_6_lineage
Create Date: 2026-05-03
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from alembic import op
from sqlalchemy import Boolean, Column, Numeric, String, Text, inspect

revision = "0005_vehicle_filter_fields"
down_revision = "0004_schema_v1_6_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "vehicles" in tables:
        _add_columns_if_missing(
            "vehicles",
            inspector,
            (
                Column("body_type", Text),
                Column("curb_weight_raw", String(120)),
                Column("curb_weight", Numeric),
                Column("vehicle_length_raw", String(120)),
                Column("vehicle_length", Numeric),
                Column("vehicle_width_raw", String(120)),
                Column("vehicle_width", Numeric),
                Column("wheelbase_raw", String(120)),
                Column("wheelbase", Numeric),
                Column("vax_crush_distance_raw", String(120)),
                Column("vax_crush_distance", Numeric),
            ),
        )
    if "test_filter_summary" in tables:
        _add_columns_if_missing(
            "test_filter_summary",
            inspector,
            (
                Column("vehicle_test_weight_min", Numeric),
                Column("vehicle_test_weight_max", Numeric),
                Column("curb_weight_min", Numeric),
                Column("curb_weight_max", Numeric),
                Column("vehicle_length_min", Numeric),
                Column("vehicle_length_max", Numeric),
                Column("vehicle_width_min", Numeric),
                Column("vehicle_width_max", Numeric),
                Column("wheelbase_min", Numeric),
                Column("wheelbase_max", Numeric),
                Column("vax_crush_distance_min", Numeric),
                Column("vax_crush_distance_max", Numeric),
                Column(
                    "has_load_cell_barrier",
                    Boolean,
                    nullable=False,
                    server_default="0",
                ),
            ),
        )


def downgrade() -> None:
    # Additive migration: older downgrade steps remove the parent tables.
    pass


def _add_columns_if_missing(
    table_name: str,
    inspector: Any,
    columns: Sequence[Column[object]],
) -> None:
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column)
