from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    AssetSummary,
    CrashTest,
    MediaAsset,
    TestFacet,
    TestFilterSummary,
    TestParticipant,
    Vehicle,
)


class ReadModelBuilder:
    def __init__(self, session: Session) -> None:
        self.session = session

    def rebuild_for_test(self, test_no: int) -> None:
        test = self.session.scalar(select(CrashTest).where(CrashTest.test_no == test_no))
        if test is None:
            return
        self.session.execute(delete(TestFilterSummary).where(TestFilterSummary.test_id == test.id))
        self.session.execute(delete(AssetSummary).where(AssetSummary.test_id == test.id))
        vehicles = list(self.session.scalars(select(Vehicle).where(Vehicle.test_id == test.id)))
        assets = list(self.session.scalars(select(MediaAsset).where(MediaAsset.test_id == test.id)))
        participants = list(
            self.session.scalars(select(TestParticipant).where(TestParticipant.test_id == test.id))
        )
        asset_kinds = sorted({asset.asset_kind for asset in assets})
        self.session.add(
            TestFilterSummary(
                test_id=test.id,
                test_no=test.test_no,
                test_type=test.test_type,
                test_configuration=test.test_configuration,
                test_date=test.test_date,
                model_year_min=_min_or_none(vehicle.model_year for vehicle in vehicles),
                model_year_max=_max_or_none(vehicle.model_year for vehicle in vehicles),
                vehicle_makes_json=sorted({vehicle.make for vehicle in vehicles if vehicle.make}),
                vehicle_models_json=sorted(
                    {vehicle.model for vehicle in vehicles if vehicle.model}
                ),
                participant_kinds_json=sorted(
                    {participant.participant_kind for participant in participants}
                ),
                asset_kinds_json=asset_kinds,
                has_uds_or_tdms_package=bool({"uds", "tdms"} & set(asset_kinds)),
            )
        )
        for asset_kind, count in self.session.execute(
            select(MediaAsset.asset_kind, func.count(MediaAsset.id))
            .where(MediaAsset.test_id == test.id)
            .group_by(MediaAsset.asset_kind)
        ):
            self.session.add(
                AssetSummary(
                    test_id=test.id,
                    test_no=test.test_no,
                    asset_kind=asset_kind,
                    asset_count=count,
                )
            )
        self.session.flush()
        self.rebuild_facets()

    def rebuild_facets(self) -> None:
        self.session.execute(delete(TestFacet))
        summaries = list(self.session.scalars(select(TestFilterSummary)))
        facet_counts: dict[tuple[str, str], int] = {}
        for summary in summaries:
            _add(facet_counts, "test_type", summary.test_type)
            _add(facet_counts, "test_configuration", summary.test_configuration)
            for value in summary.vehicle_makes_json or []:
                _add(facet_counts, "vehicle_make", value)
            for value in summary.vehicle_models_json or []:
                _add(facet_counts, "vehicle_model", value)
            for value in summary.participant_kinds_json or []:
                _add(facet_counts, "participant_kind", value)
            for value in summary.asset_kinds_json or []:
                _add(facet_counts, "asset_kind", value)
        for (name, value), count in facet_counts.items():
            self.session.add(TestFacet(facet_name=name, facet_value=value, test_count=count))
        self.session.flush()


def _add(counts: dict[tuple[str, str], int], name: str, value: str | None) -> None:
    if value:
        counts[(name, value)] = counts.get((name, value), 0) + 1


def _min_or_none(values: Iterable[int | None]) -> int | None:
    valid = [value for value in values if value is not None]
    return min(valid) if valid else None


def _max_or_none(values: Iterable[int | None]) -> int | None:
    valid = [value for value in values if value is not None]
    return max(valid) if valid else None
