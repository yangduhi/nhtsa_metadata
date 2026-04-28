from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ApiPagination:
    page_number: int | None = None
    count: int | None = None
    total: int | None = None
    current_url: str | None = None
    next_url: str | None = None
    previous_url: str | None = None


@dataclass(frozen=True)
class ApiMeta:
    pagination: ApiPagination | None = None
    status: int | None = None
    message: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class SourceRequest:
    endpoint_name: str
    url: str
    path_values: dict[str, Any] = field(default_factory=dict)
    query_values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceFetchResult:
    request: SourceRequest
    payload: dict[str, Any]
    http_status: int | None = None
    elapsed_ms: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)

    @property
    def meta(self) -> ApiMeta:
        raw_meta = self.payload.get("meta")
        if not isinstance(raw_meta, dict):
            return ApiMeta()
        raw_pagination = raw_meta.get("pagination")
        pagination = None
        if isinstance(raw_pagination, dict):
            pagination = ApiPagination(
                page_number=raw_pagination.get("pageNumber"),
                count=raw_pagination.get("count"),
                total=raw_pagination.get("total"),
                current_url=raw_pagination.get("currentUrl"),
                next_url=raw_pagination.get("nextUrl"),
                previous_url=raw_pagination.get("previousUrl"),
            )
        return ApiMeta(
            pagination=pagination,
            status=raw_meta.get("status"),
            message=raw_meta.get("message"),
            error=raw_meta.get("error"),
        )


@dataclass(frozen=True)
class SectionObservation:
    section_name: str
    json_path: str
    row_count: int
    sample_json: Any | None = None


@dataclass(frozen=True)
class FieldObservation:
    endpoint_name: str
    section_name: str | None
    field_path: str
    observed_type: str
    is_non_null: bool
    example_value: Any | None = None
    mapping_status: str = "unmapped"
    mapped_table: str | None = None
    mapped_column: str | None = None
