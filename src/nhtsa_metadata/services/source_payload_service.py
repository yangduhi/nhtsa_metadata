from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    SourcePayload,
    SourcePayloadObservation,
    SourcePayloadSection,
)
from nhtsa_metadata.sources.nhtsa_crash.contracts import SectionObservation, SourceFetchResult


class SourcePayloadService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_payload(
        self,
        fetch_result: SourceFetchResult,
        run_id: int | None = None,
        run_item_id: int | None = None,
    ) -> SourcePayload:
        payload_hash = _hash_json(fetch_result.payload)
        canonical_url_hash = _hash_text(fetch_result.request.url)
        meta = fetch_result.meta
        pagination = meta.pagination
        existing = self.session.scalar(
            select(SourcePayload).where(
                SourcePayload.endpoint_name == fetch_result.request.endpoint_name,
                SourcePayload.canonical_url_hash == canonical_url_hash,
                SourcePayload.payload_hash == payload_hash,
            )
        )
        if existing is None:
            existing = SourcePayload(
                endpoint_name=fetch_result.request.endpoint_name,
                source="nhtsa_crash",
                test_no=_to_int(fetch_result.request.path_values.get("test_no")),
                vehicle_no=_to_int(fetch_result.request.path_values.get("vehicle_no")),
                occupant_location_raw=_to_str(
                    fetch_result.request.path_values.get("occupant_location")
                ),
                curve_no=_to_int(fetch_result.request.path_values.get("curve_no")),
                page_number=pagination.page_number if pagination else None,
                request_url=fetch_result.request.url,
                canonical_url_hash=canonical_url_hash,
                http_status=fetch_result.http_status,
                api_status=meta.status,
                api_message=meta.message,
                api_error=meta.error,
                pagination_json=pagination.__dict__ if pagination else None,
                count_returned=pagination.count
                if pagination
                else _result_count(fetch_result.payload),
                total_available=pagination.total if pagination else None,
                payload_hash=payload_hash,
                payload_json=fetch_result.payload,
                fetched_at=datetime.utcnow(),
            )
            self.session.add(existing)
            self.session.flush()
        self.session.add(
            SourcePayloadObservation(
                source_payload_id=existing.id,
                run_id=run_id,
                run_item_id=run_item_id,
                observed_at=datetime.utcnow(),
                http_status=fetch_result.http_status,
                elapsed_ms=fetch_result.elapsed_ms,
                response_size_bytes=len(json.dumps(fetch_result.payload)),
                response_headers_json=fetch_result.response_headers,
            )
        )
        self.session.flush()
        return existing

    def save_sections(self, source_payload_id: int, sections: list[SectionObservation]) -> None:
        for section in sections:
            existing = self.session.scalar(
                select(SourcePayloadSection).where(
                    SourcePayloadSection.source_payload_id == source_payload_id,
                    SourcePayloadSection.section_name == section.section_name,
                    SourcePayloadSection.json_path == section.json_path,
                )
            )
            if existing is None:
                self.session.add(
                    SourcePayloadSection(
                        source_payload_id=source_payload_id,
                        section_name=section.section_name,
                        json_path=section.json_path,
                        row_count=section.row_count,
                        section_hash=_hash_json(section.sample_json),
                        sample_json=section.sample_json,
                    )
                )
            else:
                existing.row_count = section.row_count
                existing.sample_json = section.sample_json
        self.session.flush()

    def get_latest_payloads_for_test(
        self, test_no: int, endpoint_names: list[str] | None = None
    ) -> list[SourcePayload]:
        statement = select(SourcePayload).where(SourcePayload.test_no == test_no)
        if endpoint_names:
            statement = statement.where(SourcePayload.endpoint_name.in_(endpoint_names))
        statement = statement.order_by(SourcePayload.fetched_at, SourcePayload.id)
        return list(self.session.scalars(statement))


def _hash_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _result_count(payload: dict[str, object]) -> int:
    results = payload.get("results")
    return len(results) if isinstance(results, list) else 0


def _to_int(value: object) -> int | None:
    try:
        return int(value) if isinstance(value, int | str) else None
    except (TypeError, ValueError):
        return None


def _to_str(value: object) -> str | None:
    return None if value is None else str(value)
