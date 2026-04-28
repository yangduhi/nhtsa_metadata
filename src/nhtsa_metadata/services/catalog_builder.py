from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import CollectionRun
from nhtsa_metadata.services.ingestion_service import IngestionService
from nhtsa_metadata.sources.nhtsa_crash.client import LiveAccessNotAllowedError
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient


@dataclass(frozen=True)
class CollectResult:
    run_id: int
    test_numbers: list[int]
    payload_count: int
    canonical_rows: int


class CatalogBuilder:
    def __init__(self, session: Session, source: str = "fixture", allow_live: bool = False) -> None:
        if source == "live" and not allow_live:
            raise LiveAccessNotAllowedError("--source live requires --allow-live")
        if source != "fixture":
            raise LiveAccessNotAllowedError("only fixture source is enabled before Phase 7")
        self.session = session
        self.client = FixtureNhtsaClient()
        self.ingestion = IngestionService(session)

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
        run = CollectionRun(run_uuid=str(uuid4()), source="nhtsa_crash", mode="fixture")
        self.session.add(run)
        self.session.flush()
        payload_count = 0
        canonical_rows = 0
        for test_no in test_numbers:
            fetch_results = self._fetch_fixture_matrix(test_no)
            payload_count += len(self.ingestion.ingest_fetch_results(fetch_results, run_id=run.id))
            canonical_rows += self.ingestion.rebuild_test(test_no)
        run.status = "succeeded"
        self.session.commit()
        return CollectResult(run.id, test_numbers, payload_count, canonical_rows)

    def _fetch_fixture_matrix(self, test_no: int) -> list[SourceFetchResult]:
        results: list[SourceFetchResult] = []
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
            results.append(self.client.fetch(endpoint_name, test_no=test_no))
        if test_no == 10001:
            results.append(
                self.client.fetch(
                    "restraint_info", test_no=10001, vehicle_no=1, occupant_location="DRIVER"
                )
            )
            results.append(self.client.fetch("intrusion_info", test_no=10001, vehicle_no=1))
        if test_no == 10003:
            results.append(
                self.client.fetch(
                    "restraint_info", test_no=10003, vehicle_no=2, occupant_location="DRIVER"
                )
            )
            results.append(self.client.fetch("intrusion_info", test_no=10003, vehicle_no=2))
        results.extend(self.client.fetch_all_pages("instrumentation_info", test_no=test_no))
        return results
