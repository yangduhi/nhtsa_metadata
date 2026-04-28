from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import SourceFieldCatalog


@dataclass(frozen=True)
class CoverageRow:
    endpoint_name: str
    section_name: str | None
    field_path: str
    observed_type: str
    seen_count: int
    non_null_count: int
    mapping_status: str
    mapped_table: str | None
    mapped_column: str | None
    example_values: list[Any] | None


class CoverageService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def report_rows(self) -> list[CoverageRow]:
        rows = self.session.scalars(
            select(SourceFieldCatalog).order_by(
                SourceFieldCatalog.endpoint_name, SourceFieldCatalog.field_path
            )
        )
        return [
            CoverageRow(
                endpoint_name=row.endpoint_name,
                section_name=row.section_name,
                field_path=row.field_path,
                observed_type=row.observed_type,
                seen_count=row.seen_count,
                non_null_count=row.non_null_count,
                mapping_status=row.mapping_status,
                mapped_table=row.mapped_table,
                mapped_column=row.mapped_column,
                example_values=row.example_values_json,
            )
            for row in rows
        ]
