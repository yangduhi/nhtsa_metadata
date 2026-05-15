"""download jobs for GUI-controlled asset downloads

Revision ID: 0007_download_jobs
Revises: 0006_barrier_load_cell_classification
Create Date: 2026-05-14
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, inspect

revision = "0007_download_jobs"
down_revision = "0006_barrier_load_cell_classification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "download_jobs" not in tables:
        op.create_table(
            "download_jobs",
            Column("id", Integer, primary_key=True),
            Column("media_asset_id", Integer, ForeignKey("media_assets.id"), nullable=False),
            Column("test_no", Integer, nullable=True),
            Column("status", String(32), nullable=False),
            Column("source_url", Text, nullable=False),
            Column("destination_path", Text, nullable=False),
            Column("filename", Text, nullable=False),
            Column("content_type", Text, nullable=True),
            Column("size_bytes", Integer, nullable=True),
            Column("started_at", DateTime, nullable=True),
            Column("finished_at", DateTime, nullable=True),
            Column("error_json", JSON, nullable=True),
            Column("created_at", DateTime, nullable=True),
            Column("updated_at", DateTime, nullable=True),
        )
        op.create_index("ix_download_jobs_media_asset_id", "download_jobs", ["media_asset_id"])
        op.create_index("ix_download_jobs_test_no", "download_jobs", ["test_no"])


def downgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "download_jobs" in tables:
        op.drop_index("ix_download_jobs_test_no", table_name="download_jobs")
        op.drop_index("ix_download_jobs_media_asset_id", table_name="download_jobs")
        op.drop_table("download_jobs")
