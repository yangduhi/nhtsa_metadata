from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from nhtsa_metadata.db.models import (
    BarrierLoadCellChannelMap,
    CrashTest,
)
from nhtsa_metadata.db.session import ensure_schema
from nhtsa_metadata.services.filter_db_reports import build_filter_db_read_model_report
from nhtsa_metadata.services.read_model_builder import ReadModelBuilder
from nhtsa_metadata.services.vehicle_filter_fields import promote_vehicle_filter_fields


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
            "read_model_report": build_filter_db_read_model_report(
                session,
                channel_map_rows_before_discard=channel_map_rows_before_discard,
                discard_load_cell_channel_map=discard_load_cell_channel_map,
            ),
        }
        session.commit()
    engine.dispose()
    payload["output_size_bytes"] = output_path.stat().st_size
    return payload


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"
