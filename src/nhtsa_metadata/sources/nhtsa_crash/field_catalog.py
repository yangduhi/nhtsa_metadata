from __future__ import annotations

from typing import Any

from nhtsa_metadata.sources.nhtsa_crash.contracts import FieldObservation
from nhtsa_metadata.sources.nhtsa_crash.field_aliases import FIELD_ALIASES


def observe_fields(
    endpoint_name: str,
    section_name: str | None,
    row: dict[str, Any],
    json_path: str,
) -> list[FieldObservation]:
    observations: list[FieldObservation] = []
    for key, value in row.items():
        source_key = f"{section_name}.{key}" if section_name else f"API.{key}"
        target = FIELD_ALIASES.get(source_key)
        observations.append(
            FieldObservation(
                endpoint_name=endpoint_name,
                section_name=section_name,
                field_path=f"{json_path}.{key}",
                observed_type=type(value).__name__,
                is_non_null=value is not None,
                example_value=value,
                mapping_status="mapped" if target else "unmapped",
                mapped_table=target[0] if target else None,
                mapped_column=target[1] if target else None,
            )
        )
    return observations
