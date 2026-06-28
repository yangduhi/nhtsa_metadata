from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine, RowMapping

from nhtsa_metadata import __version__
from nhtsa_metadata.config import Settings, get_settings
from nhtsa_metadata.db.models import (
    CollectionRun,
    CrashTest,
    MediaAsset,
    TestClassification,
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
from nhtsa_metadata.services.scope import is_in_scope_test_record

FINAL_SUMMARY_TABLE = "metadata_refresh_test_filter_summary_v10"
FINAL_FACET_TABLE = "metadata_refresh_facets_v10"
FINAL_TEST_VIEW = "vw_tests_metadata_refresh_v10_final"
FINAL_CLASSIFICATION_TABLE = "metadata_refresh_test_classification_v10"
FINAL_METRICS_TABLE = "metadata_refresh_v10_final_summary"
FINAL_OPEN5_TABLE = "metadata_refresh_open5_final_recommendation_v10"
FINAL_SCENARIO_TABLE = "metadata_refresh_scenario_trajectory_v10"


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
            "min_test_date": effective_settings.min_test_date.isoformat(),
        }

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return _metadata_refresh_html()

    @app.get("/metadata-refresh", response_class=HTMLResponse)
    def metadata_refresh_page() -> str:
        return _metadata_refresh_html()

    @app.get("/api/tests")
    def list_tests(
        test_type: str | None = None,
        vehicle_make: str | None = None,
        asset_kind: str | None = None,
        test_family: str | None = None,
        test_configuration_key: str | None = None,
        metadata_flag: str | None = None,
        limit: int = 5000,
        offset: int = 0,
    ) -> dict[str, object]:
        if _metadata_refresh_v10_available(engine):
            items = _final_test_summaries(
                engine,
                min_test_date=effective_settings.min_test_date,
                test_type=test_type,
                vehicle_make=vehicle_make,
                asset_kind=asset_kind,
                test_family=test_family,
                test_configuration_key=test_configuration_key,
                metadata_flag=metadata_flag,
            )
            total = len(items)
            return {
                "items": items[offset : offset + limit],
                "count": total,
                "limit": limit,
                "offset": offset,
                "source": "metadata_refresh_v10_final",
            }

        with session_factory() as session:
            summaries = list(
                session.scalars(
                    select(TestFilterSummary)
                    .where(TestFilterSummary.test_date >= effective_settings.min_test_date)
                    .order_by(TestFilterSummary.test_no)
                )
            )
        items = [_summary_out(summary) for summary in summaries]
        if test_type:
            items = [item for item in items if item.get("test_type") == test_type]
        if vehicle_make:
            items = [item for item in items if _contains(item, "vehicle_makes", vehicle_make)]
        if asset_kind:
            items = [item for item in items if _contains(item, "asset_kinds", asset_kind)]
        total = len(items)
        return {
            "items": items[offset : offset + limit],
            "count": total,
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/tests/{test_no}")
    def get_test_detail(test_no: int, include_raw: bool = False) -> dict[str, object]:
        with session_factory() as session:
            test = session.scalar(select(CrashTest).where(CrashTest.test_no == test_no))
            if test is None:
                return {"test_no": test_no, "found": False}
            if not is_in_scope_test_record(
                test.test_date,
                test.test_date_parse_status,
                effective_settings.min_test_date,
            ):
                return {
                    "test_no": test_no,
                    "found": False,
                    "reason": "out_of_scope",
                    "min_test_date": effective_settings.min_test_date.isoformat(),
                }
            vehicles = list(session.scalars(select(Vehicle).where(Vehicle.test_id == test.id)))
            participants = list(
                session.scalars(select(TestParticipant).where(TestParticipant.test_id == test.id))
            )
            assets = list(session.scalars(select(MediaAsset).where(MediaAsset.test_id == test.id)))
            legacy_classification = session.scalar(
                select(TestClassification).where(TestClassification.test_id == test.id)
            )

        if _metadata_refresh_v10_available(engine):
            final_payload = _final_test_detail(engine, test_no)
            if final_payload is not None:
                final_test = final_payload["test"]
                payload: dict[str, object] = {
                    "found": True,
                    "source": "metadata_refresh_v10_final",
                    "test": final_test,
                    "metadata_refresh": final_payload["metadata_refresh"],
                    "test_classification": final_payload["test_classification"],
                    "legacy_test_classification": _classification_out(legacy_classification),
                    "test_participants": [
                        _participant_out(participant) for participant in participants
                    ],
                    "vehicles": [_vehicle_out(vehicle) for vehicle in vehicles],
                    "media_assets": [_asset_out(asset) for asset in assets],
                    "scenario_trajectory": final_payload["scenario_trajectory"],
                    "open5_recommendations": final_payload["open5_recommendations"],
                }
                if include_raw:
                    payload["raw_payload_note"] = "Raw payload endpoint is intentionally separated."
                return payload

        payload = {
            "found": True,
            "test": {
                "test_no": test.test_no,
                "test_type": test.test_type,
                "test_date": str(test.test_date) if test.test_date else None,
                "test_configuration": test.test_configuration,
                "closing_speed": _float_or_none(test.closing_speed),
            },
            "vehicles": [_vehicle_out(vehicle) for vehicle in vehicles],
            "test_classification": _classification_out(legacy_classification),
            "test_participants": [_participant_out(participant) for participant in participants],
            "media_assets": [_asset_out(asset) for asset in assets],
        }
        if include_raw:
            payload["raw_payload_note"] = "Raw payload endpoint is intentionally separated."
        return payload

    @app.get("/api/filter-options")
    def filter_options() -> dict[str, list[dict[str, object]]]:
        if _metadata_refresh_v10_available(engine):
            with engine.connect() as connection:
                rows = connection.execute(
                    text(
                        f"select facet_name, facet_value, test_count "
                        f"from {FINAL_FACET_TABLE} "
                        "order by facet_name, test_count desc, facet_value"
                    )
                ).mappings()
                options: dict[str, list[dict[str, object]]] = {}
                for row in rows:
                    options.setdefault(str(row["facet_name"]), []).append(
                        {"value": row["facet_value"], "test_count": row["test_count"]}
                    )
                return options

        with session_factory() as session:
            facets = list(session.scalars(select(TestFacet).order_by(TestFacet.facet_name)))
        options = {}
        for facet in facets:
            options.setdefault(facet.facet_name, []).append(
                {"value": facet.facet_value, "test_count": facet.test_count}
            )
        return options

    @app.get("/api/metadata-refresh/v10/summary")
    def metadata_refresh_summary() -> dict[str, object]:
        if not _metadata_refresh_v10_available(engine):
            return {"available": False, "reason": "metadata_refresh_v10_final_not_installed"}
        with engine.connect() as connection:
            metrics = {
                str(row["metric"]): _parse_metric_value(row["value"])
                for row in connection.execute(
                    text(f"select metric, value from {FINAL_METRICS_TABLE} order by metric")
                ).mappings()
            }
            recommendations = list(
                connection.execute(
                    text(
                        f"select test_no, issue, family, final_status, confidence "
                        f"from {FINAL_OPEN5_TABLE} order by test_no, issue"
                    )
                ).mappings()
            )
        return {
            "available": True,
            "source": "metadata_refresh_v10_final",
            "metrics": metrics,
            "open5_recommendation_count": len(recommendations),
            "open5_recommendations": [dict(row) for row in recommendations],
        }

    @app.get("/api/metadata-refresh/v10/recommendations")
    def metadata_refresh_recommendations() -> dict[str, object]:
        if not _metadata_refresh_v10_available(engine):
            return {"available": False, "items": [], "count": 0}
        with engine.connect() as connection:
            rows = list(
                connection.execute(
                    text(f"select * from {FINAL_OPEN5_TABLE} order by test_no, issue")
                )
                .mappings()
                .all()
            )
        return {
            "available": True,
            "items": [_jsonable_mapping(row) for row in rows],
            "count": len(rows),
        }

    @app.get("/api/metadata-refresh/v10/tests/{test_no}")
    def metadata_refresh_test(test_no: int) -> dict[str, object]:
        if not _metadata_refresh_v10_available(engine):
            return {"available": False, "test_no": test_no, "found": False}
        detail = _final_test_detail(engine, test_no)
        if detail is None:
            return {"available": True, "test_no": test_no, "found": False}
        return {"available": True, "found": True, **detail}

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


def _metadata_refresh_v10_available(engine: Engine) -> bool:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    view_names = set(inspector.get_view_names())
    return (
        FINAL_SUMMARY_TABLE in table_names
        and FINAL_FACET_TABLE in table_names
        and FINAL_CLASSIFICATION_TABLE in table_names
        and FINAL_METRICS_TABLE in table_names
        and FINAL_TEST_VIEW in view_names
    )


def _final_test_summaries(
    engine: Engine,
    *,
    min_test_date: date,
    test_type: str | None,
    vehicle_make: str | None,
    asset_kind: str | None,
    test_family: str | None,
    test_configuration_key: str | None,
    metadata_flag: str | None,
) -> list[dict[str, object]]:
    with engine.connect() as connection:
        rows = list(
            connection.execute(
                text(
                    f"select * from {FINAL_SUMMARY_TABLE} "
                    "where test_date >= :min_test_date order by test_no"
                ),
                {"min_test_date": min_test_date.isoformat()},
            )
            .mappings()
            .all()
        )
    items = [_final_summary_out(row) for row in rows]
    if test_type:
        items = [item for item in items if item.get("test_type") == test_type]
    if vehicle_make:
        items = [item for item in items if _contains(item, "vehicle_makes", vehicle_make)]
    if asset_kind:
        items = [item for item in items if _contains(item, "asset_kinds", asset_kind)]
    if test_family:
        items = [item for item in items if item.get("test_family") == test_family]
    if test_configuration_key:
        items = [
            item
            for item in items
            if item.get("test_configuration_key") == test_configuration_key
        ]
    if metadata_flag:
        items = [
            item
            for item in items
            if isinstance(item.get("metadata_flags"), list)
            and metadata_flag in item["metadata_flags"]
        ]
    return items


def _final_test_detail(engine: Engine, test_no: int) -> dict[str, object] | None:
    with engine.connect() as connection:
        final_row = connection.execute(
            text(f"select * from {FINAL_TEST_VIEW} where test_no=:test_no"),
            {"test_no": test_no},
        ).mappings().first()
        if final_row is None:
            return None
        classification = connection.execute(
            text(f"select * from {FINAL_CLASSIFICATION_TABLE} where test_no=:test_no"),
            {"test_no": test_no},
        ).mappings().first()
        scenarios = list(
            connection.execute(
                text(f"select * from {FINAL_SCENARIO_TABLE} where test_no=:test_no order by id"),
                {"test_no": test_no},
            )
            .mappings()
            .all()
        )
        recommendations = list(
            connection.execute(
                text(f"select * from {FINAL_OPEN5_TABLE} where test_no=:test_no order by issue"),
                {"test_no": test_no},
            )
            .mappings()
            .all()
        )
    return {
        "test": _final_test_out(final_row),
        "metadata_refresh": _metadata_refresh_out(final_row),
        "test_classification": _final_classification_out(classification),
        "scenario_trajectory": [_jsonable_mapping(row) for row in scenarios],
        "open5_recommendations": [_jsonable_mapping(row) for row in recommendations],
    }


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


def _final_summary_out(row: Mapping[str, Any]) -> dict[str, object]:
    flags = _metadata_flags(row)
    return {
        "test_no": row["test_no"],
        "test_type": row["test_type"],
        "test_configuration": row["test_configuration"],
        "test_configuration_key": row["test_configuration_key"],
        "test_date": _date_string(row["test_date"]),
        "vehicle_makes": _json_list(row["vehicle_makes_json"]),
        "vehicle_models": _json_list(row["vehicle_models_json"]),
        "participant_kinds": _json_list(row["participant_kinds_json"]),
        "asset_kinds": _json_list(row["asset_kinds_json"]),
        "has_uds_or_tdms_package": bool(row["has_uds_or_tdms_package"]),
        "closing_speed": _float_or_none(row["closing_speed"]),
        "impact_angle": _float_or_none(row["impact_angle"]),
        "offset_distance": _float_or_none(row["offset_distance"]),
        "model_year_min": row["model_year_min"],
        "model_year_max": row["model_year_max"],
        "test_family": row["official_family"],
        "official_category": row["official_category"],
        "official_mode": row["official_mode"],
        "official_evidence_confidence": row["official_evidence_confidence"],
        "metadata_refresh_status": row["metadata_refresh_status"],
        "metadata_flags": flags,
    }


def _final_test_out(row: Mapping[str, Any]) -> dict[str, object]:
    return {
        "test_no": row["test_no"],
        "test_reference_no": row["test_reference_no"],
        "test_type": row["test_type"],
        "test_date": _date_string(row["test_date"]),
        "test_performer": row["test_performer"],
        "contractor_study_title": row["contractor_study_title"],
        "test_configuration": row["test_configuration"],
        "test_configuration_key": row["test_configuration_key"],
        "closing_speed": _float_or_none(row["closing_speed"]),
        "impact_angle": _float_or_none(row["impact_angle"]),
        "offset_distance": _float_or_none(row["offset_distance"]),
        "model_year": row["model_year"],
        "original_values": {
            "test_configuration": row["original_test_configuration"],
            "test_configuration_key": row["original_test_configuration_key"],
            "closing_speed": _float_or_none(row["original_closing_speed"]),
            "impact_angle": _float_or_none(row["original_impact_angle"]),
            "offset_distance": _float_or_none(row["original_offset_distance"]),
            "model_year": row["original_model_year"],
        },
    }


def _metadata_refresh_out(row: Mapping[str, Any]) -> dict[str, object]:
    return {
        "status": row["metadata_refresh_status"],
        "finalized_at": row["metadata_refresh_finalized_at"],
        "auto_overlay_count": row["metadata_refresh_auto_overlay_count_v10"],
        "keep_null_count": row["metadata_refresh_keep_null_count_v10"],
        "resolved_by_ev_package_count": row["metadata_refresh_resolved_by_ev_count_v10"],
        "open5_recommendation_count": row["open5_recommendation_count_v10"],
        "live_summary_missing": bool(row["live_summary_missing_v10"]),
        "source_semantics_conflict": bool(row["source_semantics_conflict_v10"]),
        "open5_final_status": row["open5_final_status_v10"],
        "open5_value_decision": row["open5_value_decision_v10"],
        "ev_test_impang_raw": row["ev_test_impang_raw_v10"],
        "live_metadata_impang_raw": row["live_metadata_impang_raw_v10"],
        "flags": _metadata_flags(row),
    }


def _final_classification_out(classification: RowMapping | None) -> dict[str, object] | None:
    if classification is None:
        return None
    return {
        "source_test_configuration_key": classification["source_test_configuration_key"],
        "source_test_configuration": classification["source_test_configuration"],
        "impact_angle": _float_or_none(classification["impact_angle"]),
        "impact_direction": classification["impact_direction"],
        "counterparty_kind": classification["counterparty_kind"],
        "test_family": classification["test_family"],
        "official_category": classification["official_category"],
        "official_mode": classification["official_mode"],
        "official_evidence_confidence": classification["official_evidence_confidence"],
        "official_evidence_basis": classification["official_evidence_basis"],
        "official_anchor_ids": classification["official_anchor_ids"],
        "classification_version": classification["classification_version"],
        "classification_status": classification["classification_status"],
        "live_summary_missing": bool(classification["live_summary_missing_v10"]),
        "source_semantics_conflict": bool(classification["source_semantics_conflict_v10"]),
        "ev_test_impang_raw": classification["ev_test_impang_raw_v10"],
        "live_metadata_impang_raw": classification["live_metadata_impang_raw_v10"],
    }


def _classification_out(classification: TestClassification | None) -> dict[str, object] | None:
    if classification is None:
        return None
    return {
        "source_test_configuration_key": classification.source_test_configuration_key,
        "source_test_configuration": classification.source_test_configuration,
        "impact_angle": _float_or_none(classification.impact_angle),
        "impact_direction": classification.impact_direction,
        "counterparty_kind": classification.counterparty_kind,
        "test_family": classification.test_family,
        "classification_status": classification.classification_status,
    }


def _vehicle_out(vehicle: Vehicle) -> dict[str, object]:
    return {
        "source_vehicle_no": vehicle.source_vehicle_no,
        "make": vehicle.make,
        "model": vehicle.model,
        "model_year": vehicle.model_year,
        "vehicle_speed": _float_or_none(vehicle.vehicle_speed),
    }


def _participant_out(participant: TestParticipant) -> dict[str, object]:
    return {
        "participant_kind": participant.participant_kind,
        "source_vehicle_no": participant.source_vehicle_no,
        "display_name": participant.display_name,
    }


def _asset_out(asset: MediaAsset) -> dict[str, object]:
    return {
        "asset_kind": asset.asset_kind,
        "asset_subtype": asset.asset_subtype,
        "source_url": asset.source_url,
        "suggested_filename": asset.suggested_filename,
    }


def _contains(item: dict[str, object], key: str, value: str) -> bool:
    candidate = item.get(key)
    return isinstance(candidate, list) and value in candidate


def _json_list(value: Any) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _metadata_flags(row: Mapping[str, Any]) -> list[str]:
    flags: list[str] = []
    if row.get("live_summary_missing_v10"):
        flags.append("live_summary_missing_v10")
    if row.get("source_semantics_conflict_v10"):
        flags.append("source_semantics_conflict_v10")
    if row.get("metadata_refresh_auto_overlay_count_v10"):
        flags.append("has_auto_overlay_v10")
    if row.get("metadata_refresh_keep_null_count_v10"):
        flags.append("has_keep_null_policy_v10")
    if row.get("metadata_refresh_resolved_by_ev_count_v10"):
        flags.append("resolved_by_ev_package_v10")
    return flags


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_metric_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _jsonable_mapping(row: Mapping[str, Any]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in row.items():
        if hasattr(value, "isoformat"):
            result[str(key)] = value.isoformat()
        else:
            result[str(key)] = value
    return result


def _metadata_refresh_html() -> str:
    return """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NHTSA Metadata Refresh v10</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link
    rel="stylesheet"
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap"
  >
  <style>
    :root {
      --bg: #08090a;
      --panel: rgba(255,255,255,.035);
      --panel-strong: rgba(255,255,255,.06);
      --border: rgba(255,255,255,.085);
      --text: #f7f8f8;
      --muted: #8a8f98;
      --soft: #d0d6e0;
      --accent: #7170ff;
      --green: #10b981;
      --amber: #f59e0b;
      --red: #ef4444;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 15% 0%, rgba(113,112,255,.2), transparent 32rem),
        radial-gradient(circle at 80% 15%, rgba(16,185,129,.12), transparent 28rem),
        var(--bg);
      color: var(--text);
      font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
      font-feature-settings: 'cv01', 'ss03';
    }
    a { color: var(--soft); text-decoration: none; }
    a:hover { color: var(--text); }
    .shell { width: min(1180px, calc(100vw - 32px)); margin: 0 auto; padding: 36px 0; }
    .nav, .card, .metric, .table-wrap {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 24px 80px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.04);
    }
    .nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 16px;
      position: sticky;
      top: 12px;
      backdrop-filter: blur(18px);
      z-index: 2;
    }
    .brand { display: flex; align-items: center; gap: 10px; font-weight: 600; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--green); }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border: 1px solid var(--border);
      border-radius: 999px;
      color: var(--soft);
      font-size: 12px;
      background: rgba(255,255,255,.03);
    }
    .hero { padding: 58px 0 28px; }
    .eyebrow { color: var(--accent); font-size: 13px; font-weight: 600; }
    h1 {
      max-width: 840px;
      margin: 14px 0;
      font-size: clamp(38px, 6vw, 72px);
      line-height: .98;
      letter-spacing: -1.4px;
      font-weight: 600;
    }
    .lead { max-width: 760px; color: var(--muted); font-size: 18px; line-height: 1.65; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 22px; }
    .button {
      padding: 10px 14px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,.04);
      color: var(--text);
      font-weight: 500;
    }
    .button.primary { background: #5e6ad2; border-color: rgba(255,255,255,.16); }
    .grid { display: grid; gap: 14px; }
    .metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .metric { padding: 18px; min-height: 118px; }
    .metric .label { color: var(--muted); font-size: 12px; }
    .metric .value { margin-top: 14px; font: 600 30px/1 'JetBrains Mono', monospace; }
    .metric .note { margin-top: 10px; color: var(--soft); font-size: 12px; }
    .section { margin-top: 20px; }
    .section-head { display: flex; align-items: end; justify-content: space-between; gap: 16px; }
    h2 { margin: 0 0 10px; font-size: 22px; letter-spacing: -.25px; }
    .muted { color: var(--muted); }
    .cards { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .card { padding: 18px; }
    .card strong { display: block; margin-bottom: 8px; }
    .flag-live { color: var(--amber); }
    .flag-conflict { color: #fb7185; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 12px 14px; border-bottom: 1px solid rgba(255,255,255,.07); }
    th { color: var(--muted); text-align: left; font-weight: 500; }
    td { color: var(--soft); vertical-align: top; }
    .table-wrap { overflow: auto; }
    code, .mono { font-family: 'JetBrains Mono', ui-monospace, monospace; }
    .status { color: var(--green); }
    .error { color: var(--red); }
    .footer { color: var(--muted); padding: 28px 0; font-size: 12px; }
    @media (max-width: 900px) {
      .metrics, .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 620px) {
      .metrics, .cards { grid-template-columns: 1fr; }
      .nav { align-items: flex-start; flex-direction: column; gap: 10px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <nav class="nav">
      <div class="brand"><span class="dot"></span>NHTSA Metadata DB</div>
      <div class="pill"><span class="status">●</span><span id="runtime">loading</span></div>
    </nav>

    <section class="hero">
      <div class="eyebrow">metadata_refresh_v10_final · approved overlay</div>
      <h1>최종 메타데이터 overlay가 실제 API/GUI 경로에 연결되었습니다.</h1>
      <p class="lead">
        원본 canonical row는 보존하고, 승인된 v10 값·flags·evidence를 final read model로
        노출합니다. 아래 카드는 현재 연결된 DB에서 직접 읽은 값입니다.
      </p>
      <div class="actions">
        <a class="button primary" href="/api/metadata-refresh/v10/summary">Summary JSON</a>
        <a class="button" href="/api/filter-options">Facet options</a>
        <a class="button" href="/docs">Swagger docs</a>
      </div>
    </section>

    <section class="grid metrics" id="metrics"></section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Final flags</h2>
          <div class="muted">live 누락과 source semantics conflict를 필터링합니다.</div>
        </div>
      </div>
      <div class="grid cards" id="flagCards"></div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Open-5 evidence treatment</h2>
          <div class="muted">이 항목들은 blocker가 아니라 final evidence/flag로 관리됩니다.</div>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>test_no</th>
              <th>issue</th>
              <th>family</th>
              <th>final_status</th>
              <th>confidence</th>
            </tr>
          </thead>
          <tbody id="recommendations"></tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Quick detail checks</h2>
          <div class="muted">대표 항목의 final overlay/detail API로 바로 이동합니다.</div>
        </div>
      </div>
      <div class="grid cards">
        <a class="card" href="/api/tests/14432">
          <strong>14432 · live summary missing</strong>
          <span class="muted">static package/report resolved, SIDE_POLE</span>
        </a>
        <a class="card" href="/api/tests/11602">
          <strong>11602 · source semantics conflict</strong>
          <span class="muted">physical side-pole retained, angle null</span>
        </a>
        <a class="card" href="/api/metadata-refresh/v10/tests/12871">
          <strong>12871 · ADAS/TJA trajectory</strong>
          <span class="muted">scenario speeds stored separately, closing_speed null</span>
        </a>
      </div>
    </section>

    <div class="footer">
      Local endpoint: <span class="mono">127.0.0.1:8000</span> ·
      restart server after DB/code changes.
    </div>
  </main>

  <script>
    const fmt = new Intl.NumberFormat('en-US');
    const metricSpec = [
      ['tests', 'tests', 'denominator'],
      ['final_view_rows', 'final view rows', 'overlay coverage'],
      ['auto_overlay_rows', 'auto overlays', 'safe evidence applied'],
      ['keep_null_policy_rows', 'keep-null rows', 'explicit null policy'],
      ['resolved_by_ev_package_rows', 'EV resolved', 'static package evidence'],
      ['open5_recommendation_rows', 'open-5', 'closed as evidence'],
      ['live_summary_missing_rows', 'live missing', 'flagged final rows'],
      ['source_semantics_conflict_rows', 'source conflicts', 'flagged final rows'],
    ];
    function metricCard(metrics, key, label, note) {
      const value = metrics[key] ?? '—';
      return `<article class="metric">
        <div class="label">${label}</div>
        <div class="value">${typeof value === 'number' ? fmt.format(value) : value}</div>
        <div class="note">${note}</div>
      </article>`;
    }
    function flagCard(title, count, klass, href, rows) {
      const tests = rows.map((item) => item.test_no).join(', ');
      return `<a class="card" href="${href}">
        <strong class="${klass}">${title}</strong>
        <div class="mono">count=${count}</div>
        <div class="muted">tests: ${tests || 'none'}</div>
      </a>`;
    }
    async function loadDashboard() {
      const [summaryRes, liveRes, conflictRes] = await Promise.all([
        fetch('/api/metadata-refresh/v10/summary'),
        fetch('/api/tests?metadata_flag=live_summary_missing_v10'),
        fetch('/api/tests?metadata_flag=source_semantics_conflict_v10'),
      ]);
      const summary = await summaryRes.json();
      const live = await liveRes.json();
      const conflict = await conflictRes.json();
      if (!summary.available) {
        document.getElementById('runtime').textContent = 'v10 objects unavailable';
        document.getElementById('runtime').className = 'error';
        return;
      }
      document.getElementById('runtime').textContent = 'v10 final connected';
      document.getElementById('metrics').innerHTML = metricSpec
        .map(([key, label, note]) => metricCard(summary.metrics, key, label, note))
        .join('');
      document.getElementById('flagCards').innerHTML = [
        flagCard(
          'live_summary_missing_v10',
          live.count,
          'flag-live',
          '/api/tests?metadata_flag=live_summary_missing_v10',
          live.items || [],
        ),
        flagCard(
          'source_semantics_conflict_v10',
          conflict.count,
          'flag-conflict',
          '/api/tests?metadata_flag=source_semantics_conflict_v10',
          conflict.items || [],
        ),
        `<a class="card" href="/api/metadata-refresh/v10/recommendations">
          <strong>recommendation evidence</strong>
          <div class="mono">count=${summary.open5_recommendation_count}</div>
          <div class="muted">open-5 rows exposed by API and DB table</div>
        </a>`,
      ].join('');
      document.getElementById('recommendations').innerHTML =
        summary.open5_recommendations.map((row) => `<tr>
          <td><a href="/api/tests/${row.test_no}" class="mono">${row.test_no}</a></td>
          <td>${row.issue}</td>
          <td>${row.family}</td>
          <td><span class="mono">${row.final_status}</span></td>
          <td>${row.confidence}</td>
        </tr>`).join('');
    }
    loadDashboard().catch((error) => {
      document.getElementById('runtime').textContent = 'dashboard load failed';
      document.getElementById('runtime').className = 'error';
      console.error(error);
    });
  </script>
</body>
</html>
"""
