from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    BarrierLoadCellClassification,
    CrashTest,
    TestFilterSummary,
)


def build_filter_db_read_model_report(
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
