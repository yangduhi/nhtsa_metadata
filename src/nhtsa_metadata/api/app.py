from fastapi import FastAPI
from sqlalchemy import select

from nhtsa_metadata import __version__
from nhtsa_metadata.config import Settings, get_settings
from nhtsa_metadata.db.models import (
    CollectionRun,
    CrashTest,
    MediaAsset,
    TestFacet,
    TestFilterSummary,
    TestParticipant,
    Vehicle,
)
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.coverage_service import CoverageService


def create_app(settings: Settings | None = None) -> FastAPI:
    effective_settings = settings or get_settings()
    engine = create_engine_for_settings(effective_settings)
    ensure_schema(engine)
    session_factory = create_session_factory(effective_settings)
    app = FastAPI(title=effective_settings.app_name, version=__version__)
    app.state.settings = effective_settings

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "app": effective_settings.app_name,
            "environment": effective_settings.environment,
            "database_url_configured": bool(effective_settings.database_url),
        }

    @app.get("/api/tests")
    def list_tests(
        test_type: str | None = None,
        vehicle_make: str | None = None,
        asset_kind: str | None = None,
    ) -> dict[str, object]:
        with session_factory() as session:
            summaries = list(
                session.scalars(select(TestFilterSummary).order_by(TestFilterSummary.test_no))
            )
        items = [_summary_out(summary) for summary in summaries]
        if test_type:
            items = [item for item in items if item.get("test_type") == test_type]
        if vehicle_make:
            items = [item for item in items if _contains(item, "vehicle_makes", vehicle_make)]
        if asset_kind:
            items = [item for item in items if _contains(item, "asset_kinds", asset_kind)]
        return {"items": items, "count": len(items)}

    @app.get("/api/tests/{test_no}")
    def get_test_detail(test_no: int, include_raw: bool = False) -> dict[str, object]:
        with session_factory() as session:
            test = session.scalar(select(CrashTest).where(CrashTest.test_no == test_no))
            if test is None:
                return {"test_no": test_no, "found": False}
            vehicles = list(session.scalars(select(Vehicle).where(Vehicle.test_id == test.id)))
            participants = list(
                session.scalars(select(TestParticipant).where(TestParticipant.test_id == test.id))
            )
            assets = list(session.scalars(select(MediaAsset).where(MediaAsset.test_id == test.id)))
            payload: dict[str, object] = {
                "found": True,
                "test": {
                    "test_no": test.test_no,
                    "test_type": test.test_type,
                    "test_date": str(test.test_date) if test.test_date else None,
                    "test_configuration": test.test_configuration,
                    "closing_speed": float(test.closing_speed) if test.closing_speed else None,
                },
                "vehicles": [
                    {
                        "source_vehicle_no": vehicle.source_vehicle_no,
                        "make": vehicle.make,
                        "model": vehicle.model,
                        "model_year": vehicle.model_year,
                    }
                    for vehicle in vehicles
                ],
                "test_participants": [
                    {
                        "participant_kind": participant.participant_kind,
                        "source_vehicle_no": participant.source_vehicle_no,
                        "display_name": participant.display_name,
                    }
                    for participant in participants
                ],
                "media_assets": [
                    {
                        "asset_kind": asset.asset_kind,
                        "source_url": asset.source_url,
                        "suggested_filename": asset.suggested_filename,
                    }
                    for asset in assets
                ],
            }
            if include_raw:
                payload["raw_payload_note"] = "Raw payload endpoint is intentionally separated."
            return payload

    @app.get("/api/filter-options")
    def filter_options() -> dict[str, list[dict[str, object]]]:
        with session_factory() as session:
            facets = list(session.scalars(select(TestFacet).order_by(TestFacet.facet_name)))
        options: dict[str, list[dict[str, object]]] = {}
        for facet in facets:
            options.setdefault(facet.facet_name, []).append(
                {"value": facet.facet_value, "test_count": facet.test_count}
            )
        return options

    @app.get("/api/coverage/fields")
    def coverage_fields() -> dict[str, object]:
        with session_factory() as session:
            rows = CoverageService(session).report_rows()
        return {"items": [row.__dict__ for row in rows], "count": len(rows)}

    @app.get("/api/collection-runs")
    def collection_runs() -> dict[str, object]:
        with session_factory() as session:
            rows = list(session.scalars(select(CollectionRun).order_by(CollectionRun.id)))
        return {
            "items": [
                {
                    "id": row.id,
                    "run_uuid": row.run_uuid,
                    "source": row.source,
                    "mode": row.mode,
                    "status": row.status,
                }
                for row in rows
            ],
            "count": len(rows),
        }

    return app


def _summary_out(summary: TestFilterSummary) -> dict[str, object]:
    return {
        "test_no": summary.test_no,
        "test_type": summary.test_type,
        "test_configuration": summary.test_configuration,
        "test_date": str(summary.test_date) if summary.test_date else None,
        "vehicle_makes": summary.vehicle_makes_json or [],
        "vehicle_models": summary.vehicle_models_json or [],
        "participant_kinds": summary.participant_kinds_json or [],
        "asset_kinds": summary.asset_kinds_json or [],
        "has_uds_or_tdms_package": summary.has_uds_or_tdms_package,
    }


def _contains(item: dict[str, object], key: str, value: str) -> bool:
    candidate = item.get(key)
    return isinstance(candidate, list) and value in candidate
