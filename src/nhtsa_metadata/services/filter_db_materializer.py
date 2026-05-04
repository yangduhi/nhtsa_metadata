from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from nhtsa_metadata.db.models import (
    BarrierLoadCellChannelMap,
    BarrierLoadCellClassification,
    CrashTest,
    TestFilterSummary,
    Vehicle,
)
from nhtsa_metadata.db.session import ensure_schema
from nhtsa_metadata.services.read_model_builder import ReadModelBuilder
from nhtsa_metadata.sources.nhtsa_crash.normalization import parse_number

VEHICLE_FIELD_SPECS: tuple[tuple[str, str, tuple[str, ...], bool], ...] = (
    ("body_type", "body_type", ("bodyType", "BODYD"), False),
    ("curb_weight", "curb_weight_raw", ("curbWeight", "CURBWT"), True),
    ("vehicle_length", "vehicle_length_raw", ("vehicleLength", "VEHLEN"), True),
    ("vehicle_width", "vehicle_width_raw", ("vehicleWidth", "VEHWID"), True),
    ("wheelbase", "wheelbase_raw", ("wheelbase", "WHLBAS"), True),
    ("vax_crush_distance", "vax_crush_distance_raw", ("vaxCrushDistance", "CRHDST"), True),
)


def materialize_filter_database(
    *,
    source_db: Path,
    output_db: Path,
    overwrite: bool = False,
    discard_load_cell_channel_map: bool = True,
) -> dict[str, Any]:
    source_path = source_db.resolve()
    output_path = output_db.resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"source DB not found: {source_path}")
    if source_path == output_path:
        raise ValueError("source DB and output DB must be different paths")
    if output_path.exists():
        if not overwrite:
            raise FileExistsError(f"output DB already exists: {output_path}")
        output_path.unlink()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, output_path)

    engine = create_engine(_sqlite_url(output_path), future=True)
    ensure_schema(engine)
    session_factory: sessionmaker[Session] = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        vehicle_report = promote_vehicle_filter_fields(session)
        test_numbers = list(
            session.scalars(select(CrashTest.test_no).order_by(CrashTest.test_no))
        )
        builder = ReadModelBuilder(session)
        for test_no in test_numbers:
            builder.rebuild_for_test(test_no, rebuild_facets=False)
        builder.rebuild_facets()
        channel_map_rows_before_discard = int(
            session.scalar(select(func.count(BarrierLoadCellChannelMap.id))) or 0
        )
        if discard_load_cell_channel_map:
            session.execute(delete(BarrierLoadCellChannelMap))
        payload = {
            "source_db": str(source_path),
            "output_db": str(output_path),
            "source_size_bytes": source_path.stat().st_size,
            "output_size_bytes": output_path.stat().st_size,
            "schema_materialized": True,
            "vehicle_report": vehicle_report,
            "read_model_report": _read_model_report(
                session,
                channel_map_rows_before_discard=channel_map_rows_before_discard,
                discard_load_cell_channel_map=discard_load_cell_channel_map,
            ),
        }
        session.commit()
    engine.dispose()
    payload["output_size_bytes"] = output_path.stat().st_size
    return payload


def promote_vehicle_filter_fields(session: Session) -> dict[str, Any]:
    changed_rows = 0
    field_non_null_counts: dict[str, int] = {
        field_name: 0 for field_name, *_ in VEHICLE_FIELD_SPECS
    }
    for vehicle in session.scalars(select(Vehicle).order_by(Vehicle.id)):
        raw_row = _raw_dict(vehicle.raw_row_json)
        row_changed = False
        for field_name, raw_field_name, source_keys, is_numeric in VEHICLE_FIELD_SPECS:
            raw_value = _first(raw_row, source_keys)
            if raw_value is None:
                if getattr(vehicle, field_name) is not None:
                    field_non_null_counts[field_name] += 1
                continue
            if is_numeric:
                parsed = parse_number(raw_value)
                numeric_value = parsed.numeric_value
                raw_text = None if parsed.raw_value is None else str(parsed.raw_value)
                if getattr(vehicle, raw_field_name) != raw_text:
                    setattr(vehicle, raw_field_name, raw_text)
                    row_changed = True
                if getattr(vehicle, field_name) != numeric_value:
                    setattr(vehicle, field_name, numeric_value)
                    row_changed = True
            else:
                text_value = str(raw_value)
                if getattr(vehicle, field_name) != text_value:
                    setattr(vehicle, field_name, text_value)
                    row_changed = True
            if getattr(vehicle, field_name) is not None:
                field_non_null_counts[field_name] += 1
        if row_changed:
            changed_rows += 1
    session.flush()
    return {
        "vehicle_rows": int(session.scalar(select(func.count(Vehicle.id))) or 0),
        "changed_rows": changed_rows,
        "field_non_null_counts": field_non_null_counts,
    }


def _read_model_report(
    session: Session,
    *,
    channel_map_rows_before_discard: int,
    discard_load_cell_channel_map: bool,
) -> dict[str, Any]:
    classification_counts = {
        classification_id: int(count)
        for classification_id, count in session.execute(
            select(
                BarrierLoadCellClassification.classification_id,
                func.count(BarrierLoadCellClassification.id),
            )
            .group_by(BarrierLoadCellClassification.classification_id)
            .order_by(BarrierLoadCellClassification.classification_id)
        )
    }
    family_counts = {
        family: int(count)
        for family, count in session.execute(
            select(
                BarrierLoadCellClassification.family,
                func.count(BarrierLoadCellClassification.id),
            )
            .group_by(BarrierLoadCellClassification.family)
            .order_by(BarrierLoadCellClassification.family)
        )
    }
    return {
        "test_rows": int(session.scalar(select(func.count(CrashTest.id))) or 0),
        "test_filter_summary_rows": int(
            session.scalar(select(func.count(TestFilterSummary.id))) or 0
        ),
        "has_load_cell_barrier_count": int(
            session.scalar(
                select(func.count(TestFilterSummary.id)).where(
                    TestFilterSummary.has_load_cell_barrier.is_(True)
                )
            )
            or 0
        ),
        "load_cell_classified_test_count": int(
            session.scalar(
                select(func.count(func.distinct(BarrierLoadCellClassification.test_no)))
            )
            or 0
        ),
        "load_cell_classification_counts": classification_counts,
        "load_cell_family_counts": family_counts,
        "channel_map_rows_before_discard": channel_map_rows_before_discard,
        "channel_map_rows_materialized": (
            0 if discard_load_cell_channel_map else channel_map_rows_before_discard
        ),
        "channel_map_discarded_for_filter_db": discard_load_cell_channel_map,
    }


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def _raw_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _first(raw: dict[str, Any], keys: tuple[str, ...]) -> object | None:
    for key in keys:
        if key in raw:
            return cast(object, raw[key])
    return None
