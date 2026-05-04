from __future__ import annotations

import sqlite3
from datetime import date

from sqlalchemy import select

from nhtsa_metadata.config import Settings
from nhtsa_metadata.db.models import (
    Barrier,
    BarrierLoadCellChannelMap,
    BarrierLoadCellClassification,
    CrashTest,
    InstrumentationChannel,
    TestFilterSummary,
    Vehicle,
)
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.filter_db_materializer import materialize_filter_database


def test_materialize_filter_database_copies_and_populates_filter_read_model(
    tmp_settings: Settings,
    tmp_path,
) -> None:
    source_path = tmp_path / "source.sqlite"
    output_path = tmp_path / "filter_ready.sqlite"
    source_settings = tmp_settings.model_copy(
        update={"database_url": f"sqlite:///{source_path}"}
    )
    ensure_schema(create_engine_for_settings(source_settings))
    session_factory = create_session_factory(source_settings)
    with session_factory() as session:
        test = CrashTest(
            test_no=20001,
            test_date=date(2024, 1, 1),
            test_date_parse_status="parsed",
            test_type="NCAP",
            test_configuration="Flat barrier",
        )
        session.add(test)
        session.flush()
        session.add(
            Vehicle(
                test_id=test.id,
                test_no=test.test_no,
                source_vehicle_no=1,
                make="MAZDA",
                model="MAZDA3",
                model_year=2017,
                raw_row_json={
                    "BODYD": "FOUR DOOR SEDAN",
                    "CURBWT": "1324",
                    "VEHLEN": 4563,
                    "VEHWID": 1790,
                    "WHLBAS": 2700,
                    "CRHDST": 557,
                },
            )
        )
        session.add(
            Barrier(
                test_id=test.id,
                test_no=test.test_no,
                shape="FLAT BARRIER",
                raw_row_json={"barrierShape": "FLAT BARRIER"},
            )
        )
        curve_no = 1
        for row_letter in ("A", "B", "C", "D"):
            for col in range(1, 10):
                session.add(
                    InstrumentationChannel(
                        test_id=test.id,
                        test_no=test.test_no,
                        curve_no=curve_no,
                        sensor_type="LOAD CELL",
                        sensor_attachment=f"LOAD CELL {row_letter}{col}",
                        sensor_axis="1",
                        unit_raw="kN",
                        raw_row_json={
                            "SENTYPD": "LOAD CELL",
                            "SENATTD": f"LOAD CELL {row_letter}{col}",
                            "YTYPE": "FORCE",
                            "YUNITSD": "kN",
                        },
                    )
                )
                curve_no += 1
        session.commit()

    payload = materialize_filter_database(source_db=source_path, output_db=output_path)

    assert payload["vehicle_report"]["changed_rows"] == 1
    assert payload["read_model_report"]["load_cell_classification_counts"] == {
        "legacy_4x9_us_ncap": 1
    }
    assert payload["read_model_report"]["channel_map_discarded_for_filter_db"] is True

    output_settings = tmp_settings.model_copy(
        update={"database_url": f"sqlite:///{output_path}"}
    )
    output_session_factory = create_session_factory(output_settings)
    with output_session_factory() as session:
        vehicle = session.scalar(select(Vehicle).where(Vehicle.test_no == 20001))
        summary = session.scalar(
            select(TestFilterSummary).where(TestFilterSummary.test_no == 20001)
        )
        classification = session.scalar(
            select(BarrierLoadCellClassification).where(
                BarrierLoadCellClassification.test_no == 20001
            )
        )
        assert vehicle is not None
        assert vehicle.body_type == "FOUR DOOR SEDAN"
        assert vehicle.curb_weight == 1324
        assert vehicle.vehicle_length == 4563
        assert vehicle.vehicle_width == 1790
        assert vehicle.wheelbase == 2700
        assert vehicle.vax_crush_distance == 557
        assert summary is not None
        assert summary.has_load_cell_barrier is True
        assert summary.load_cell_barrier_classification_ids_json == ["legacy_4x9_us_ncap"]
        assert summary.load_cell_barrier_families_json == ["frontal_or_flat_load_cell_wall"]
        assert classification is not None
        assert classification.classification_id == "legacy_4x9_us_ncap"
        assert session.scalar(select(BarrierLoadCellChannelMap)) is None

    with sqlite3.connect(source_path) as connection:
        source_vehicle = connection.execute(
            "select body_type, curb_weight, vehicle_length from vehicles where test_no = 20001"
        ).fetchone()
    assert source_vehicle == (None, None, None)
