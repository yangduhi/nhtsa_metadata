from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nhtsa_metadata.sources.nhtsa_crash.contracts import FieldObservation, SectionObservation


@dataclass(frozen=True)
class SourceRow:
    endpoint_name: str
    section_name: str | None
    json_path: str
    row_hash: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ParsedSourcePayload:
    endpoint_name: str
    test_no: int | None
    source_rows: list[SourceRow]
    sections: list[SectionObservation] = field(default_factory=list)
    field_observations: list[FieldObservation] = field(default_factory=list)
