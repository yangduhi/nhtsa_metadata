from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from nhtsa_metadata.config import get_settings
from nhtsa_metadata.db.models import SourcePayload
from nhtsa_metadata.services.canonical_mapper import map_to_canonical_specs
from nhtsa_metadata.services.canonical_upsert import CanonicalUpsertService
from nhtsa_metadata.services.field_catalog_service import FieldCatalogService
from nhtsa_metadata.services.read_model_builder import ReadModelBuilder
from nhtsa_metadata.services.scope import evaluate_scope_from_specs
from nhtsa_metadata.services.source_payload_service import SourcePayloadService
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult, SourceRequest
from nhtsa_metadata.sources.nhtsa_crash.parsers import parse_source_payload


class IngestionService:
    def __init__(self, session: Session, min_test_date: date | None = None) -> None:
        self.session = session
        self.min_test_date = min_test_date or get_settings().min_test_date
        self.payload_service = SourcePayloadService(session)
        self.field_catalog_service = FieldCatalogService(session)
        self.canonical_service = CanonicalUpsertService(session)
        self.read_model_builder = ReadModelBuilder(session, min_test_date=self.min_test_date)

    def ingest_fetch_results(
        self,
        fetch_results: list[SourceFetchResult],
        run_id: int | None = None,
        run_item_id: int | None = None,
    ) -> list[SourcePayload]:
        saved_payloads: list[SourcePayload] = []
        for fetch_result in fetch_results:
            payload = self.payload_service.save_payload(fetch_result, run_id, run_item_id)
            parsed = parse_source_payload(fetch_result)
            self.payload_service.save_sections(payload.id, parsed.sections)
            self.field_catalog_service.record_observations(parsed.field_observations)
            saved_payloads.append(payload)
        self.session.flush()
        return saved_payloads

    def rebuild_test(self, test_no: int) -> int:
        payloads = self.payload_service.get_latest_payloads_for_test(test_no)
        specs_by_payload = []
        all_specs = []
        for payload in payloads:
            fetch_result = SourceFetchResult(
                request=SourceRequest(
                    endpoint_name=payload.endpoint_name,
                    url=payload.request_url,
                    path_values={"test_no": test_no, "vehicle_no": payload.vehicle_no},
                ),
                payload=payload.payload_json,
                http_status=payload.http_status,
            )
            parsed = parse_source_payload(fetch_result)
            specs = map_to_canonical_specs(parsed)
            all_specs.extend(specs)
            specs_by_payload.append((payload.id, specs))
        decision = evaluate_scope_from_specs(all_specs, self.min_test_date)
        if not decision.in_scope:
            self.canonical_service.delete_test_canonical_rows(test_no)
            self.read_model_builder.rebuild_facets()
            self.session.flush()
            return 0
        inserted = self.canonical_service.replace_test_canonical_rows(test_no, specs_by_payload)
        self.read_model_builder.rebuild_for_test(test_no)
        self.session.flush()
        return inserted
