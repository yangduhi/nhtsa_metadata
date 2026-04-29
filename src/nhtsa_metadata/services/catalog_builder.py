from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from nhtsa_metadata.config import Settings, get_settings, sanitize_database_url
from nhtsa_metadata.db.models import CollectionRun, CollectionRunItem
from nhtsa_metadata.services.ingestion_service import IngestionService
from nhtsa_metadata.services.scope import evaluate_scope_from_fetch_results
from nhtsa_metadata.sources.nhtsa_crash.client import LiveAccessNotAllowedError
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient
from nhtsa_metadata.sources.nhtsa_crash.live_client import LiveNhtsaClient


@dataclass(frozen=True)
class CollectResult:
    run_id: int
    test_numbers: list[int]
    payload_count: int
    canonical_rows: int


class CatalogBuilder:
    def __init__(
        self,
        session: Session,
        source: str = "fixture",
        allow_live: bool = False,
        settings: Settings | None = None,
    ) -> None:
        if source == "live" and not allow_live:
            raise LiveAccessNotAllowedError("--source live requires --allow-live")
        self.session = session
        self.mode = source
        self.allow_live = allow_live
        self.settings = settings or get_settings()
        self.client = (
            LiveNhtsaClient(self.settings, allow_live=allow_live)
            if source == "live"
            else FixtureNhtsaClient()
        )
        self.ingestion = IngestionService(session, min_test_date=self.settings.min_test_date)

    def discover(self, max_pages: int = 1) -> dict[str, object]:
        return {"source": "fixture", "max_pages": max_pages, "test_numbers": [10001, 10003]}

    def collect_manifest(self, manifest: Path) -> CollectResult:
        test_numbers: list[int] = []
        with manifest.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                test_numbers.append(int(row["test_no"]))
        return self.collect_tests(test_numbers)

    def collect_tests(self, test_numbers: list[int]) -> CollectResult:
        run = CollectionRun(
            run_uuid=str(uuid4()),
            source="nhtsa_crash",
            mode=self.mode,
            allow_live=self.allow_live,
            database_url_sanitized=sanitize_database_url(self.settings.database_url),
            options_json={"test_numbers": test_numbers},
        )
        self.session.add(run)
        self.session.flush()
        payload_count = 0
        canonical_rows = 0
        for test_no in test_numbers:
            run_item = CollectionRunItem(
                run_id=run.id,
                test_no=test_no,
                status="started",
                endpoint_statuses_json={
                    "min_test_date": self.settings.min_test_date.isoformat()
                },
            )
            self.session.add(run_item)
            self.session.flush()
            scope_probe = self._fetch_scope_probe(test_no)
            scope_decision = evaluate_scope_from_fetch_results(
                scope_probe, self.settings.min_test_date
            )
            run_item.endpoint_statuses_json = {"scope": scope_decision.to_json()}
            if not scope_decision.in_scope:
                self.ingestion.canonical_service.delete_test_canonical_rows(test_no)
                self.ingestion.read_model_builder.rebuild_facets()
                run_item.status = "skipped_out_of_scope"
                run_item.finished_at = datetime.utcnow()
                continue
            fetch_results = self._fetch_fixture_matrix(test_no, preloaded_results=scope_probe)
            payload_count += len(
                self.ingestion.ingest_fetch_results(
                    fetch_results, run_id=run.id, run_item_id=run_item.id
                )
            )
            canonical_rows += self.ingestion.rebuild_test(test_no)
            run_item.status = "succeeded"
            run_item.finished_at = datetime.utcnow()
        run.status = "succeeded"
        run.finished_at = datetime.utcnow()
        self.session.commit()
        return CollectResult(run.id, test_numbers, payload_count, canonical_rows)

    def _fetch_scope_probe(self, test_no: int) -> list[SourceFetchResult]:
        return [self.client.fetch("test_summary", test_no=test_no)]

    def _fetch_fixture_matrix(
        self,
        test_no: int,
        preloaded_results: list[SourceFetchResult] | None = None,
    ) -> list[SourceFetchResult]:
        results: list[SourceFetchResult] = []
        preloaded_by_endpoint = {
            result.request.endpoint_name: result for result in preloaded_results or []
        }
        occupant_result: SourceFetchResult | None = None
        for endpoint_name in (
            "test_summary",
            "metadata_export",
            "test_detail",
            "vehicle_info",
            "barrier_info",
            "occupant_info",
            "multimedia_files",
            "vehicle_documents",
        ):
            result = preloaded_by_endpoint.get(endpoint_name)
            if result is None:
                result = self.client.fetch(endpoint_name, test_no=test_no)
            results.append(result)
            if endpoint_name == "occupant_info":
                occupant_result = result
        for vehicle_no, occupant_location in _restraint_requests_from_occupants(occupant_result):
            results.append(
                self.client.fetch(
                    "restraint_info",
                    test_no=test_no,
                    vehicle_no=vehicle_no,
                    occupant_location=occupant_location,
                )
            )
        if test_no == 10001:
            results.append(self.client.fetch("intrusion_info", test_no=10001, vehicle_no=1))
        if test_no == 10003:
            results.append(self.client.fetch("intrusion_info", test_no=10003, vehicle_no=2))
        results.extend(self.client.fetch_all_pages("instrumentation_info", test_no=test_no))
        return results


def _restraint_requests_from_occupants(
    occupant_result: SourceFetchResult | None,
) -> list[tuple[int, str]]:
    if occupant_result is None:
        return []
    results = occupant_result.payload.get("results", [])
    rows = results if isinstance(results, list) else []
    requests: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        vehicle_no = _to_int(_first(row, "vehicleNo", "VEHNO"))
        occupant_location = _first(row, "occupantLocation", "OCCLOC")
        if vehicle_no is None or occupant_location in (None, ""):
            continue
        key = (vehicle_no, str(occupant_location))
        if key in seen:
            continue
        seen.add(key)
        requests.append(key)
    return requests


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
