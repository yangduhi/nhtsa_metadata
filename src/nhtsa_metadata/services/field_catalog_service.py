from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import SourceFieldCatalog
from nhtsa_metadata.sources.nhtsa_crash.contracts import FieldObservation


class FieldCatalogService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record_observations(self, observations: Iterable[FieldObservation]) -> None:
        now = datetime.utcnow()
        for observation in observations:
            existing = self.session.scalar(
                select(SourceFieldCatalog).where(
                    SourceFieldCatalog.endpoint_name == observation.endpoint_name,
                    SourceFieldCatalog.section_name == observation.section_name,
                    SourceFieldCatalog.field_path == observation.field_path,
                    SourceFieldCatalog.observed_type == observation.observed_type,
                )
            )
            if existing is None:
                self.session.add(
                    SourceFieldCatalog(
                        endpoint_name=observation.endpoint_name,
                        section_name=observation.section_name,
                        field_path=observation.field_path,
                        observed_type=observation.observed_type,
                        first_seen_at=now,
                        last_seen_at=now,
                        seen_count=1,
                        non_null_count=1 if observation.is_non_null else 0,
                        mapping_status=observation.mapping_status,
                        mapped_table=observation.mapped_table,
                        mapped_column=observation.mapped_column,
                        example_values_json=[observation.example_value],
                    )
                )
            else:
                existing.last_seen_at = now
                existing.seen_count += 1
                if observation.is_non_null:
                    existing.non_null_count += 1
                examples = list(existing.example_values_json or [])
                if observation.example_value not in examples and len(examples) < 5:
                    examples.append(observation.example_value)
                existing.example_values_json = examples
        self.session.flush()
