from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nhtsa_metadata.config import Settings, get_settings, sanitize_database_url
from nhtsa_metadata.db.models import (
    CollectionRun,
    CollectionRunItem,
    CrashTest,
    SourcePayload,
    TestParticipant,
    Vehicle,
)
from nhtsa_metadata.services.collection_runs import mark_stale_started_runs
from nhtsa_metadata.services.ingestion_service import IngestionService
from nhtsa_metadata.sources.nhtsa_crash.client import SourceClientProtocol
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient
from nhtsa_metadata.sources.nhtsa_crash.live_client import (
    LiveAccessNotAllowedError,
    LiveNhtsaClient,
)
from nhtsa_metadata.sources.nhtsa_crash.normalization import normalize_occupant_location

PER_TEST_ENDPOINTS = (
    "test_summary",
    "metadata_export",
    "test_detail",
    "vehicle_info",
    "barrier_info",
    "occupant_info",
    "multimedia_files",
    "vehicle_documents",
)


@dataclass(frozen=True)
class EndpointBackfillResult:
    run_id: int
    endpoint_names: list[str]
    fetched_count: int
    skipped_existing_count: int
    failed_count: int
    source_payload_count_before: int
    source_payload_count_after: int
    no_new_test_no_added: bool


class EndpointCompletenessService:
    def __init__(
        self,
        session: Session,
        manifest: Path,
        min_test_date: date | None = None,
    ) -> None:
        self.session = session
        self.manifest = manifest
        self.min_test_date = min_test_date or get_settings().min_test_date

    def report(self) -> dict[str, Any]:
        manifest_rows = _read_manifest(self.manifest)
        manifest_test_numbers = sorted({int(row["test_no"]) for row in manifest_rows})
        manifest_set = set(manifest_test_numbers)
        db_test_numbers = set(
            self.session.scalars(select(CrashTest.test_no).order_by(CrashTest.test_no))
        )
        endpoint_rows = [
            self._per_test_endpoint_row(endpoint, manifest_test_numbers)
            for endpoint in PER_TEST_ENDPOINTS
        ]
        intrusion = self._intrusion_report(manifest_set)
        restraint = self._restraint_report(manifest_set)
        instrumentation = self._instrumentation_report(manifest_set)
        endpoint_rows.extend(
            [
                intrusion["summary"],
                restraint["summary"],
                instrumentation["summary"],
            ]
        )
        missing_matrix = [
            row
            for endpoint in endpoint_rows
            for row in endpoint.get("missing_requests", [])
        ]
        return {
            "run": {
                "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "manifest": str(self.manifest),
                "min_test_date": self.min_test_date.isoformat(),
            },
            "manifest": {
                "test_count": len(manifest_test_numbers),
                "duplicate_test_no": len(manifest_rows) - len(manifest_set),
                "pre_2011_rows": sum(
                    1
                    for row in manifest_rows
                    if row.get("test_date") and row["test_date"] < self.min_test_date.isoformat()
                ),
                "missing_test_date_rows": sum(
                    1 for row in manifest_rows if not row.get("test_date")
                ),
            },
            "database": {
                "canonical_tests": len(db_test_numbers),
                "manifest_tests_missing_in_db": sorted(manifest_set - db_test_numbers),
                "db_tests_not_in_manifest": sorted(db_test_numbers - manifest_set),
            },
            "endpoint_coverage": endpoint_rows,
            "intrusion_info": intrusion,
            "restraint_info": restraint,
            "instrumentation_info": instrumentation,
            "missing_endpoint_matrix": missing_matrix[:1000],
            "missing_endpoint_matrix_count": len(missing_matrix),
        }

    def _per_test_endpoint_row(
        self, endpoint_name: str, manifest_test_numbers: list[int]
    ) -> dict[str, Any]:
        existing = set(
            self.session.scalars(
                select(SourcePayload.test_no)
                .where(SourcePayload.endpoint_name == endpoint_name)
                .where(SourcePayload.test_no.in_(manifest_test_numbers))
            )
        )
        payloads = list(
            self.session.scalars(
                select(SourcePayload)
                .where(SourcePayload.endpoint_name == endpoint_name)
                .where(SourcePayload.test_no.in_(manifest_test_numbers))
            )
        )
        missing = [
            {"test_no": test_no, "endpoint_name": endpoint_name}
            for test_no in manifest_test_numbers
            if test_no not in existing
        ]
        return {
            "endpoint_name": endpoint_name,
            "expected_request_count": len(manifest_test_numbers),
            "actual_payload_count": len(payloads),
            "missing_request_count": len(missing),
            "allowed_empty_count": sum(1 for payload in payloads if payload.count_returned == 0),
            "non_empty_count": sum(1 for payload in payloads if (payload.count_returned or 0) > 0),
            "missing_requests": missing[:100],
        }

    def _intrusion_report(self, manifest_set: set[int]) -> dict[str, Any]:
        targets = self.intrusion_targets(manifest_set)
        existing = _payload_target_set(self.session, "intrusion_info")
        missing = [
            {"test_no": test_no, "vehicle_no": vehicle_no, "endpoint_name": "intrusion_info"}
            for test_no, vehicle_no in targets
            if (test_no, vehicle_no) not in existing
        ]
        payloads = _payloads_for_endpoint(self.session, "intrusion_info", manifest_set)
        summary = _target_summary("intrusion_info", targets, payloads, missing)
        return {
            "policy": (
                "expected for all canonical vehicles in the manifest, except vehicles "
                "classified only as unambiguous impactor_vehicle"
            ),
            "summary": summary,
            "targets": [
                {"test_no": test_no, "vehicle_no": vehicle_no} for test_no, vehicle_no in targets
            ],
            "missing_requests": missing,
        }

    def intrusion_targets(self, manifest_set: set[int]) -> list[tuple[int, int]]:
        participant_lookup: dict[tuple[int, int], set[str]] = {}
        rows = self.session.execute(
            select(
                TestParticipant.test_id,
                TestParticipant.source_vehicle_no,
                TestParticipant.participant_kind,
            )
            .where(TestParticipant.source_vehicle_no.is_not(None))
        )
        for test_id, vehicle_no, participant_kind in rows:
            if vehicle_no is None:
                continue
            participant_lookup.setdefault((test_id, int(vehicle_no)), set()).add(participant_kind)
        targets: set[tuple[int, int]] = set()
        for vehicle in self.session.scalars(
            select(Vehicle).order_by(Vehicle.test_no, Vehicle.source_vehicle_no)
        ):
            if vehicle.test_no not in manifest_set or vehicle.source_vehicle_no is None:
                continue
            kinds = participant_lookup.get((vehicle.test_id, int(vehicle.source_vehicle_no)), set())
            if kinds == {"impactor_vehicle"}:
                continue
            targets.add((vehicle.test_no, int(vehicle.source_vehicle_no)))
        return sorted(targets)

    def _restraint_report(self, manifest_set: set[int]) -> dict[str, Any]:
        targets = sorted(
            _expected_restraint_requests(
                _payloads_for_endpoint(self.session, "occupant_info", manifest_set)
            )
        )
        existing = {
            (
                payload.test_no,
                payload.vehicle_no,
                _normalize_location(payload.occupant_location_raw),
            )
            for payload in _payloads_for_endpoint(self.session, "restraint_info", manifest_set)
        }
        missing = [
            {
                "test_no": test_no,
                "vehicle_no": vehicle_no,
                "occupant_location": occupant_location,
                "endpoint_name": "restraint_info",
            }
            for test_no, vehicle_no, occupant_location in targets
            if (test_no, vehicle_no, occupant_location) not in existing
        ]
        payloads = _payloads_for_endpoint(self.session, "restraint_info", manifest_set)
        summary = {
            "endpoint_name": "restraint_info",
            "expected_request_count": len(targets),
            "actual_payload_count": len(payloads),
            "missing_request_count": len(missing),
            "allowed_empty_count": sum(1 for payload in payloads if payload.count_returned == 0),
            "non_empty_count": sum(1 for payload in payloads if (payload.count_returned or 0) > 0),
            "missing_requests": missing[:100],
        }
        return {"summary": summary, "missing_requests": missing}

    def _instrumentation_report(self, manifest_set: set[int]) -> dict[str, Any]:
        payloads = _payloads_for_endpoint(self.session, "instrumentation_info", manifest_set)
        pages_by_test: dict[int, set[int]] = {}
        for payload in payloads:
            if payload.test_no is None:
                continue
            pages_by_test.setdefault(payload.test_no, set()).add(payload.page_number or 0)
        missing: list[dict[str, Any]] = []
        expected_by_test: dict[int, int] = {}
        for test_no in sorted(manifest_set):
            actual_pages = pages_by_test.get(test_no, set())
            if not actual_pages:
                expected_by_test[test_no] = 1
                missing.append(
                    {
                        "test_no": test_no,
                        "endpoint_name": "instrumentation_info",
                        "page_number": 0,
                    }
                )
                continue
            expected_pages = max(actual_pages) + 1
            expected_by_test[test_no] = expected_pages
            for page in range(max(actual_pages) + 1):
                if page not in actual_pages:
                    missing.append(
                        {
                            "test_no": test_no,
                            "endpoint_name": "instrumentation_info",
                            "page_number": page,
                        }
                    )
        summary = {
            "endpoint_name": "instrumentation_info",
            "expected_request_count": sum(
                expected_by_test.get(test_no, 1) for test_no in manifest_set
            ),
            "actual_payload_count": len(payloads),
            "missing_request_count": len(missing),
            "allowed_empty_count": sum(1 for payload in payloads if payload.count_returned == 0),
            "non_empty_count": sum(1 for payload in payloads if (payload.count_returned or 0) > 0),
            "missing_requests": missing[:100],
        }
        return {"summary": summary, "missing_requests": missing}


class EndpointBackfillService:
    def __init__(
        self,
        session: Session,
        *,
        manifest: Path,
        source: str,
        allow_live: bool,
        settings: Settings | None = None,
        min_test_date: date | None = None,
        client: SourceClientProtocol | None = None,
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
        rate_limit_delay_seconds: float | None = None,
    ) -> None:
        if source == "live" and not allow_live:
            raise LiveAccessNotAllowedError("--source live requires --allow-live")
        self.session = session
        self.manifest = manifest
        self.source = source
        self.allow_live = allow_live
        self.settings = settings or get_settings()
        self.min_test_date = min_test_date or self.settings.min_test_date
        if client is not None:
            self.client = client
        elif source == "live":
            self.client = LiveNhtsaClient(
                self.settings,
                allow_live=allow_live,
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
                rate_limit_delay_seconds=rate_limit_delay_seconds,
            )
        elif source == "fixture":
            self.client = FixtureNhtsaClient()
        else:
            raise ValueError(f"unsupported source: {source}")
        self.ingestion = IngestionService(session, min_test_date=self.min_test_date)

    def backfill(
        self,
        *,
        endpoints: list[str],
        scope: str,
        only_missing: bool,
    ) -> EndpointBackfillResult:
        if scope != "existing-manifest":
            raise ValueError("backfill scope must be existing-manifest")
        unsupported = sorted(set(endpoints) - {"intrusion_info"})
        if unsupported:
            raise ValueError(f"unsupported backfill endpoints: {unsupported}")
        manifest_rows = _read_manifest(self.manifest)
        self._validate_manifest_scope(manifest_rows)
        manifest_set = {int(row["test_no"]) for row in manifest_rows}
        before_tests = set(self.session.scalars(select(CrashTest.test_no)))
        stale_runs = mark_stale_started_runs(
            self.session, "closed before endpoint backfill resume"
        )
        run = CollectionRun(
            run_uuid=str(uuid4()),
            source="nhtsa_crash",
            mode=f"{self.source}_backfill",
            allow_live=self.allow_live,
            database_url_sanitized=sanitize_database_url(self.settings.database_url),
            options_json={
                "manifest": str(self.manifest),
                "endpoints": endpoints,
                "scope": scope,
                "only_missing": only_missing,
                "stale_runs_marked_interrupted": stale_runs,
            },
        )
        self.session.add(run)
        self.session.flush()
        source_payload_before = _count_source_payloads(self.session)
        fetched = 0
        skipped = 0
        failed = 0
        try:
            if "intrusion_info" in endpoints:
                completeness = EndpointCompletenessService(
                    self.session, self.manifest, self.min_test_date
                )
                targets = completeness.intrusion_targets(manifest_set)
                existing = _payload_target_set(self.session, "intrusion_info")
                for test_no, vehicle_no in targets:
                    if test_no not in manifest_set:
                        raise ValueError("backfill target escaped manifest scope")
                    if only_missing and (test_no, vehicle_no) in existing:
                        skipped += 1
                        continue
                    item = CollectionRunItem(
                        run_id=run.id,
                        test_no=test_no,
                        endpoint_name="intrusion_info",
                        status="started",
                        endpoint_statuses_json={"vehicle_no": vehicle_no},
                    )
                    self.session.add(item)
                    self.session.flush()
                    try:
                        result = self.client.fetch(
                            "intrusion_info", test_no=test_no, vehicle_no=vehicle_no
                        )
                        self.ingestion.ingest_fetch_results(
                            [result], run_id=run.id, run_item_id=item.id
                        )
                        item.status = "succeeded"
                        item.finished_at = datetime.utcnow()
                        fetched += 1
                        self.session.commit()
                    except Exception as exc:
                        failed += 1
                        item.status = "failed"
                        item.error_json = {
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        }
                        item.finished_at = datetime.utcnow()
                        self.session.commit()
            run.status = "succeeded" if failed == 0 else "failed"
            run.finished_at = datetime.utcnow()
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            persisted_run = self.session.get(CollectionRun, run.id)
            if persisted_run is not None:
                persisted_run.status = "failed"
                persisted_run.error_json = {
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
                persisted_run.finished_at = datetime.utcnow()
                self.session.commit()
            raise
        after_tests = set(self.session.scalars(select(CrashTest.test_no)))
        return EndpointBackfillResult(
            run_id=run.id,
            endpoint_names=endpoints,
            fetched_count=fetched,
            skipped_existing_count=skipped,
            failed_count=failed,
            source_payload_count_before=source_payload_before,
            source_payload_count_after=_count_source_payloads(self.session),
            no_new_test_no_added=after_tests == before_tests,
        )

    def _validate_manifest_scope(self, manifest_rows: list[dict[str, str]]) -> None:
        for row in manifest_rows:
            if not row.get("test_no"):
                raise ValueError("manifest row missing test_no")
            raw_date = row.get("test_date")
            if not raw_date:
                raise ValueError("manifest row missing test_date")
            test_date = date.fromisoformat(raw_date)
            if test_date < self.min_test_date:
                raise ValueError("manifest contains out-of-scope test_date")


def _read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _payloads_for_endpoint(
    session: Session, endpoint_name: str, manifest_set: set[int]
) -> list[SourcePayload]:
    return list(
        session.scalars(
            select(SourcePayload)
            .where(SourcePayload.endpoint_name == endpoint_name)
            .where(SourcePayload.test_no.in_(manifest_set))
        )
    )


def _payload_target_set(session: Session, endpoint_name: str) -> set[tuple[int, int]]:
    return {
        (int(payload.test_no), int(payload.vehicle_no))
        for payload in session.scalars(
            select(SourcePayload)
            .where(SourcePayload.endpoint_name == endpoint_name)
            .where(SourcePayload.test_no.is_not(None))
            .where(SourcePayload.vehicle_no.is_not(None))
        )
        if payload.test_no is not None and payload.vehicle_no is not None
    }


def _target_summary(
    endpoint_name: str,
    targets: list[tuple[int, int]],
    payloads: list[SourcePayload],
    missing: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "endpoint_name": endpoint_name,
        "expected_request_count": len(targets),
        "actual_payload_count": len(payloads),
        "missing_request_count": len(missing),
        "allowed_empty_count": sum(1 for payload in payloads if payload.count_returned == 0),
        "non_empty_count": sum(1 for payload in payloads if (payload.count_returned or 0) > 0),
        "missing_requests": missing[:100],
    }


def _count_source_payloads(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(SourcePayload)) or 0)


def _expected_restraint_requests(
    payloads: list[SourcePayload],
) -> set[tuple[int | None, int | None, str | None]]:
    expected: set[tuple[int | None, int | None, str | None]] = set()
    for payload in payloads:
        for row in _payload_rows(payload.payload_json):
            vehicle_no = _to_int(row.get("vehicleNo") or row.get("VEHNO"))
            occupant_location = row.get("occupantLocation") or row.get("OCCLOC")
            if vehicle_no is None or occupant_location in (None, ""):
                continue
            expected.add((payload.test_no, vehicle_no, _normalize_location(occupant_location)))
    return expected


def _payload_rows(payload_json: dict[str, Any]) -> list[dict[str, Any]]:
    raw_rows = payload_json.get("results")
    rows = raw_rows if isinstance(raw_rows, list) else []
    return [row for row in rows if isinstance(row, dict)]


def _normalize_location(value: object) -> str | None:
    return normalize_occupant_location(value)


def _to_int(value: object) -> int | None:
    if not isinstance(value, int | str):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2) + "\n",
        encoding="utf-8",
    )
