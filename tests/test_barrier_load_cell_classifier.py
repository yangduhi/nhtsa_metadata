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
)
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.barrier_load_cell_classifier import BarrierLoadCellClassifier
from nhtsa_metadata.services.read_model_builder import ReadModelBuilder


def test_read_model_records_legacy_flat_barrier_load_cell_classification(
    tmp_settings: Settings,
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        test = _add_test(session, 20001)
        _add_barrier(session, test, "FLAT BARRIER")
        curve_no = 1
        for row_letter in ("A", "B", "C", "D"):
            for col in range(1, 10):
                _add_channel(
                    session,
                    test,
                    curve_no,
                    f"LOAD CELL {row_letter}{col}",
                    ytype="FORCE",
                )
                curve_no += 1
        ReadModelBuilder(session).rebuild_for_test(20001)
        summary = session.scalar(
            select(TestFilterSummary).where(TestFilterSummary.test_no == 20001)
        )
        classification = session.scalar(
            select(BarrierLoadCellClassification).where(
                BarrierLoadCellClassification.test_no == 20001
            )
        )
        assert summary is not None
        assert classification is not None
        assert summary.has_load_cell_barrier is True
        assert summary.load_cell_barrier_classification_ids_json == ["legacy_4x9_us_ncap"]
        assert summary.load_cell_barrier_force_channel_count == 36
        assert classification.normalized_barrier_shape_key == "FLAT_BARRIER_LEGACY_LOAD_CELL"
        assert classification.shape_alias_is_conditional is True
        assert classification.row_count == 4
        assert classification.col_count == 9


def test_classifies_other_shape_only_with_load_cell_barrier_evidence(
    tmp_settings: Settings,
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        test = _add_test(session, 20002, title="ADVANCED RESEARCH LOAD CELL BARRIER")
        _add_barrier(
            session,
            test,
            "OTHER",
            commentary="ADVANCED RESEARCH LOAD CELL BARRIER",
        )
        curve_no = 1
        for row in range(2, 12):
            for col in range(1, 17):
                _add_channel(
                    session,
                    test,
                    curve_no,
                    f"LOAD CELL ROW {row} COLUMN {col}",
                    ytype=None,
                    unit="NEWTONS",
                )
                curve_no += 1
        summary = BarrierLoadCellClassifier(session).rebuild_for_test(20002)
        classification = session.scalar(
            select(BarrierLoadCellClassification).where(
                BarrierLoadCellClassification.test_no == 20002
            )
        )
        assert classification is not None
        assert summary.classification_ids == ["extended_height_10x16_160"]
        assert classification.normalized_barrier_shape_key == "OTHER_LOAD_CELL_BARRIER_REVIEWED"
        assert classification.shape_alias_rule_id == (
            "other_high_resolution_load_cell_barrier_by_evidence"
        )
        assert classification.force_channel_count == 160


def test_pole_load_cell_duplicate_channel_is_preserved_as_mask(
    tmp_settings: Settings,
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        test = _add_test(session, 20003)
        _add_barrier(session, test, "POLE")
        curve_no = 1
        for pole_index in [1, 2, 3, 4, 5, 6, 7, 8, 8]:
            _add_channel(
                session,
                test,
                curve_no,
                f"LOAD CELL POLE {pole_index}",
                ytype="FORCE",
            )
            curve_no += 1
        BarrierLoadCellClassifier(session).rebuild_for_test(20003)
        classification = session.scalar(
            select(BarrierLoadCellClassification).where(
                BarrierLoadCellClassification.test_no == 20003
            )
        )
        maps = list(
            session.scalars(
                select(BarrierLoadCellChannelMap).where(
                    BarrierLoadCellChannelMap.test_no == 20003
                )
            )
        )
        assert classification is not None
        assert classification.classification_id == "side_pole_load_cell_8"
        assert classification.force_channel_count == 9
        assert classification.duplicate_channels_json == [{"pole_index": 8, "count": 2}]
        assert len(maps) == 9


def _add_test(session, test_no: int, title: str | None = None) -> CrashTest:  # type: ignore[no-untyped-def]
    test = CrashTest(
        test_no=test_no,
        test_date=date(2024, 1, 1),
        test_date_parse_status="parsed",
        contractor_study_title=title,
    )
    session.add(test)
    session.flush()
    return test


def _add_barrier(
    session,
    test: CrashTest,
    shape: str,
    commentary: str | None = None,
) -> Barrier:  # type: ignore[no-untyped-def]
    barrier = Barrier(
        test_id=test.id,
        test_no=test.test_no,
        shape=shape,
        raw_row_json={
            "barrierShape": shape,
            "barrierCommentary": commentary,
            "BARCOM": commentary,
        },
    )
    session.add(barrier)
    session.flush()
    return barrier


def _add_channel(
    session,
    test: CrashTest,
    curve_no: int,
    attachment: str,
    *,
    ytype: str | None,
    unit: str = "kN",
) -> InstrumentationChannel:  # type: ignore[no-untyped-def]
    channel = InstrumentationChannel(
        test_id=test.id,
        test_no=test.test_no,
        curve_no=curve_no,
        sensor_type="LOAD CELL",
        sensor_attachment=attachment,
        sensor_axis="1",
        unit_raw=unit,
        raw_row_json={
            "SENTYPD": "LOAD CELL",
            "SENATTD": attachment,
            "AXISD": "1",
            "YTYPE": ytype,
            "YUNITSD": unit,
        },
    )
    session.add(channel)
    return channel
