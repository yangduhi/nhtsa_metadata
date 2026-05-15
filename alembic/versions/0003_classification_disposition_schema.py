"""classification disposition schema baseline

Revision ID: 0003_classification_disposition
Revises: 0002_discovery_provenance
Create Date: 2026-05-03
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, Numeric, String, Text, inspect
from sqlalchemy.schema import UniqueConstraint

revision = "0003_classification_disposition"
down_revision = "0002_discovery_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "test_classification" in tables:
        columns = {item["name"] for item in inspector.get_columns("test_classification")}
        _add_column_if_missing(
            columns, "test_classification", Column("disposition_status", String(64))
        )
        _add_column_if_missing(
            columns, "test_classification", Column("canonical_label", String(160))
        )
        _add_column_if_missing(
            columns, "test_classification", Column("canonical_rule_id", String(160))
        )
        _add_column_if_missing(
            columns, "test_classification", Column("rule_family_id", String(160))
        )
        _add_column_if_missing(
            columns, "test_classification", Column("specificity_level", String(64))
        )
        _add_column_if_missing(columns, "test_classification", Column("confidence", Numeric))
        _add_column_if_missing(
            columns, "test_classification", Column("classification_run_id", String(120))
        )
        _add_column_if_missing(
            columns, "test_classification", Column("evidence_summary_json", JSON)
        )
    if "classification_adjudication" not in tables:
        op.create_table(
            "classification_adjudication",
            Column("id", Integer, primary_key=True),
            Column("test_id", Integer, ForeignKey("tests.id"), nullable=True),
            Column("test_no", Integer, nullable=False),
            Column("canonical_test_uid", String(120), nullable=False),
            Column("classifier_version", String(32), nullable=False),
            Column("classification_status", String(64), nullable=False),
            Column("disposition_status", String(64), nullable=False),
            Column("adjudication_status", String(64), nullable=False),
            Column("final_label", String(160), nullable=True),
            Column("recommended_rule_id", String(160), nullable=True),
            Column("adjudication_reason", Text, nullable=True),
            Column("recommended_action", Text, nullable=True),
            Column("source_endpoint_name", String(120), nullable=True),
            Column("evidence_json", JSON, nullable=True),
            Column("created_at", String, nullable=False),
            Column("updated_at", String, nullable=True),
            UniqueConstraint(
                "test_no",
                "classifier_version",
                name="uq_classification_adjudication_test_no_version",
            ),
        )
        op.create_index(
            "ix_classification_adjudication_test_no",
            "classification_adjudication",
            ["test_no"],
        )
    if "test_classification_candidates" not in tables:
        op.create_table(
            "test_classification_candidates",
            Column("id", Integer, primary_key=True),
            Column("test_id", Integer, ForeignKey("tests.id"), nullable=True),
            Column("test_no", Integer, nullable=False),
            Column("classifier_version", String(32), nullable=False),
            Column("rank", Integer, nullable=False),
            Column("rule_id", String(160), nullable=True),
            Column("canonical_rule_id", String(160), nullable=True),
            Column("rule_family_id", String(160), nullable=True),
            Column("program_domain", String(120), nullable=True),
            Column("specificity_level", String(64), nullable=True),
            Column("priority", Integer, nullable=True),
            Column("score", Numeric, nullable=True),
            Column("matched_evidence_json", JSON, nullable=True),
            Column("fallback_used", Boolean, nullable=False),
            Column("alias_used", Boolean, nullable=False),
            Column("created_at", String, nullable=False),
            Column("updated_at", String, nullable=True),
            UniqueConstraint(
                "test_no",
                "classifier_version",
                "rank",
                name="uq_test_classification_candidates_test_no_version_rank",
            ),
        )
        op.create_index(
            "ix_test_classification_candidates_test_no",
            "test_classification_candidates",
            ["test_no"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "test_classification_candidates" in tables:
        op.drop_table("test_classification_candidates")
    if "classification_adjudication" in tables:
        op.drop_table("classification_adjudication")


def _add_column_if_missing(
    existing_columns: set[str], table_name: str, column: Column[object]
) -> None:
    if column.name not in existing_columns:
        op.add_column(table_name, column)
