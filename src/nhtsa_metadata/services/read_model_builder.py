from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from nhtsa_metadata.config import get_settings
from nhtsa_metadata.db.models import (
    AssetSummary,
    Barrier,
    CrashTest,
    DeformationMeasurement,
    InjuryMetric,
    InstrumentationChannel,
    MediaAsset,
    Occupant,
    Restraint,
    TestClassification,
    TestFacet,
    TestFilterSummary,
    TestParticipant,
    Vehicle,
)
from nhtsa_metadata.services.barrier_load_cell_classifier import BarrierLoadCellClassifier
from nhtsa_metadata.services.scope import is_in_scope_test_record


class ReadModelBuilder:
    def __init__(self, session: Session, min_test_date: date | None = None) -> None:
        self.session = session
        self.min_test_date = min_test_date or get_settings().min_test_date

    def rebuild_for_test(self, test_no: int, rebuild_facets: bool = True) -> None:
        test = self.session.scalar(select(CrashTest).where(CrashTest.test_no == test_no))
        if test is None:
            return
        self.session.execute(delete(TestFilterSummary).where(TestFilterSummary.test_id == test.id))
        self.session.execute(
            delete(TestClassification).where(TestClassification.test_id == test.id)
        )
        self.session.execute(delete(AssetSummary).where(AssetSummary.test_id == test.id))
        load_cell_classifier = BarrierLoadCellClassifier(self.session)
        load_cell_classifier.clear_for_test(test.test_no)
        if not is_in_scope_test_record(
            test.test_date, test.test_date_parse_status, self.min_test_date
        ):
            self.session.flush()
            if rebuild_facets:
                self.rebuild_facets()
            return
        vehicles = list(self.session.scalars(select(Vehicle).where(Vehicle.test_id == test.id)))
        barriers = list(self.session.scalars(select(Barrier).where(Barrier.test_id == test.id)))
        assets = list(self.session.scalars(select(MediaAsset).where(MediaAsset.test_id == test.id)))
        participants = list(
            self.session.scalars(select(TestParticipant).where(TestParticipant.test_id == test.id))
        )
        asset_kinds = sorted({asset.asset_kind for asset in assets})
        asset_subtypes = {asset.asset_subtype for asset in assets if asset.asset_subtype}
        impact_angle = float(test.impact_angle) if test.impact_angle is not None else None
        impact_direction = _impact_direction(impact_angle)
        counterparty_kind = _counterparty_kind(participants)
        test_family = _test_family(test, impact_direction, counterparty_kind)
        load_cell_summary = load_cell_classifier.rebuild_for_test(test.test_no)
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
                vehicle_test_weight_min=_numeric_min_or_none(
                    vehicle.vehicle_test_weight for vehicle in vehicles
                ),
                vehicle_test_weight_max=_numeric_max_or_none(
                    vehicle.vehicle_test_weight for vehicle in vehicles
                ),
                curb_weight_min=_numeric_min_or_none(vehicle.curb_weight for vehicle in vehicles),
                curb_weight_max=_numeric_max_or_none(vehicle.curb_weight for vehicle in vehicles),
                vehicle_length_min=_numeric_min_or_none(
                    vehicle.vehicle_length for vehicle in vehicles
                ),
                vehicle_length_max=_numeric_max_or_none(
                    vehicle.vehicle_length for vehicle in vehicles
                ),
                vehicle_width_min=_numeric_min_or_none(
                    vehicle.vehicle_width for vehicle in vehicles
                ),
                vehicle_width_max=_numeric_max_or_none(
                    vehicle.vehicle_width for vehicle in vehicles
                ),
                wheelbase_min=_numeric_min_or_none(vehicle.wheelbase for vehicle in vehicles),
                wheelbase_max=_numeric_max_or_none(vehicle.wheelbase for vehicle in vehicles),
                vax_crush_distance_min=_numeric_min_or_none(
                    vehicle.vax_crush_distance for vehicle in vehicles
                ),
                vax_crush_distance_max=_numeric_max_or_none(
                    vehicle.vax_crush_distance for vehicle in vehicles
                ),
                has_load_cell_barrier=bool(load_cell_summary.classification_ids)
                or _has_load_cell_barrier(barriers),
                load_cell_barrier_classification_ids_json=load_cell_summary.classification_ids,
                load_cell_barrier_families_json=load_cell_summary.families,
                load_cell_barrier_config_version=load_cell_summary.config_version
                if load_cell_summary.classification_ids
                else None,
                load_cell_barrier_channel_count=load_cell_summary.channel_count or None,
                load_cell_barrier_force_channel_count=load_cell_summary.force_channel_count
                or None,
                load_cell_barrier_moment_channel_count=load_cell_summary.moment_channel_count
                or None,
                has_uds_or_tdms_package=bool(
                    {"uds", "tdms"} & {kind.lower() for kind in asset_kinds}
                    or {"UDS", "TDMS"} & asset_subtypes
                ),
            )
        )
        self.session.add(
            TestClassification(
                test_id=test.id,
                test_no=test.test_no,
                source_test_configuration_key=test.test_configuration_key,
                source_test_configuration=test.test_configuration,
                impact_angle=test.impact_angle,
                impact_direction=impact_direction,
                counterparty_kind=counterparty_kind,
                test_family=test_family,
                classification_status=_classification_status(test_family),
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
        if rebuild_facets:
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
            if summary.has_uds_or_tdms_package:
                _add(facet_counts, "data_package_subtype", "UDS_OR_TDMS")
            for value in summary.load_cell_barrier_classification_ids_json or []:
                _add(facet_counts, "load_cell_barrier_classification", value)
            for value in summary.load_cell_barrier_families_json or []:
                _add(facet_counts, "load_cell_barrier_family", value)
        self._add_grouped_facets(
            facet_counts,
            TestClassification.source_test_configuration_key,
            "test_configuration_key",
        )
        self._add_grouped_facets(facet_counts, TestClassification.test_family, "test_family")
        self._add_grouped_facets(
            facet_counts,
            TestClassification.classification_status,
            "classification_status",
        )
        self._add_grouped_facets(facet_counts, Vehicle.model_year, "model_year")
        self._add_grouped_facets(facet_counts, Barrier.rigidity, "barrier_rigidity")
        self._add_grouped_facets(facet_counts, Barrier.shape, "barrier_shape")
        self._add_grouped_facets(
            facet_counts,
            Occupant.occupant_location_normalized,
            "occupant_location",
        )
        self._add_grouped_facets(facet_counts, Occupant.occupant_type, "occupant_type")
        self._add_grouped_facets(facet_counts, Occupant.dummy_type, "dummy_type")
        self._add_grouped_facets(facet_counts, Restraint.restraint_type, "restraint_type")
        self._add_grouped_facets(facet_counts, Restraint.deployment_status, "restraint_deployment")
        self._add_grouped_facets(facet_counts, InstrumentationChannel.sensor_type, "sensor_type")
        self._add_grouped_facets(
            facet_counts,
            InstrumentationChannel.sensor_location,
            "sensor_location",
        )
        self._add_grouped_facets(
            facet_counts,
            InstrumentationChannel.sensor_attachment,
            "sensor_attachment",
        )
        self._add_grouped_facets(facet_counts, InstrumentationChannel.sensor_axis, "sensor_axis")
        self._add_grouped_facets(facet_counts, InstrumentationChannel.unit_raw, "sensor_unit")
        self._add_grouped_facets(
            facet_counts,
            InstrumentationChannel.channel_status,
            "channel_status",
        )
        self._add_grouped_facets(facet_counts, InstrumentationChannel.data_status, "data_status")
        self._add_grouped_facets(facet_counts, InjuryMetric.metric_code, "injury_metric_code")
        self._add_grouped_facets(
            facet_counts,
            DeformationMeasurement.measurement_code,
            "deformation_code",
        )
        self._add_grouped_facets(facet_counts, MediaAsset.asset_subtype, "asset_subtype")
        for (name, value), count in facet_counts.items():
            self.session.add(TestFacet(facet_name=name, facet_value=value, test_count=count))
        self.session.flush()

    def _add_grouped_facets(
        self,
        facet_counts: dict[tuple[str, str], int],
        column: Any,
        facet_name: str,
    ) -> None:
        model = column.class_
        statement = (
            select(column, func.count(func.distinct(model.test_id)))
            .where(column.is_not(None))
            .group_by(column)
        )
        for value, count in self.session.execute(statement):
            if value not in (None, ""):
                facet_counts[(facet_name, str(value))] = int(count)


def _add(counts: dict[tuple[str, str], int], name: str, value: str | None) -> None:
    if value:
        counts[(name, value)] = counts.get((name, value), 0) + 1


def _min_or_none(values: Iterable[int | None]) -> int | None:
    valid = [value for value in values if value is not None]
    return min(valid) if valid else None


def _max_or_none(values: Iterable[int | None]) -> int | None:
    valid = [value for value in values if value is not None]
    return max(valid) if valid else None


def _numeric_min_or_none(values: Iterable[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return min(valid) if valid else None


def _numeric_max_or_none(values: Iterable[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return max(valid) if valid else None


def _has_load_cell_barrier(barriers: Iterable[Barrier]) -> bool:
    for barrier in barriers:
        raw_row = barrier.raw_row_json
        raw = raw_row if isinstance(raw_row, dict) else {}
        values = (
            barrier.shape,
            raw.get("barrierShape"),
            raw.get("BARSHPD"),
            raw.get("barrierCommentary"),
            raw.get("BARCOM"),
        )
        if any("LOAD CELL" in str(value).upper() for value in values if value is not None):
            return True
    return False


def _impact_direction(angle: float | None) -> str:
    if angle is None:
        return "unknown"
    normalized = angle % 360
    if normalized <= 45 or normalized >= 315:
        return "frontal"
    if 45 < normalized < 135 or 225 < normalized < 315:
        return "side"
    if 135 <= normalized <= 225:
        return "rear"
    return "unknown"


def _counterparty_kind(participants: list[TestParticipant]) -> str:
    kinds = {participant.participant_kind for participant in participants}
    if "barrier" in kinds:
        return "barrier"
    if "impactor_vehicle" in kinds:
        return "impactor_vehicle"
    subject_count = sum(
        1 for participant in participants if participant.participant_kind == "subject_vehicle"
    )
    if subject_count >= 2:
        return "vehicle"
    return "unknown"


def _test_family(
    test: CrashTest, impact_direction: str, counterparty_kind: str
) -> str:
    text = " ".join(
        value.upper()
        for value in (
            test.test_configuration_key,
            test.test_configuration,
            test.test_type,
            test.contractor_study_title,
        )
        if value
    )
    if "FORWARD COLLISION WARNING" in text or " FCW" in text:
        return "adas_fcw"
    if "LANE DEPARTURE WARNING" in text or " LDW" in text:
        return "adas_ldw"
    if "TRAFFIC JAM ASSIST" in text:
        return "adas_other"
    if "PEDESTRIAN" in text:
        return "pedestrian"
    if "LOW RISK DEPLOYMENT" in text:
        return "low_risk_deployment"
    if "SLED WITH VEHICLE BODY" in text:
        return "sled_with_body"
    if "SLED WITHOUT VEHICLE BODY" in text:
        return "sled_without_body"
    if "STATIC AIR BAG TEST SIDE" in text or "OUT OF POSITION" in text:
        return "static_airbag"
    if "ROLLOVER" in text:
        return "rollover"
    if "FMVSS 213" in text or "CHILD RESTRAINT" in text:
        return "child_restraint"
    if "CALIBRATION" in text:
        return "calibration"
    if "RESEARCH" in text:
        return "research_other"
    if impact_direction == "frontal" and counterparty_kind == "barrier":
        return "frontal_barrier"
    if impact_direction == "side" and counterparty_kind == "impactor_vehicle":
        return "side_impactor"
    if impact_direction in {"frontal", "side", "rear"}:
        return impact_direction
    return "unknown"


def _classification_status(test_family: str) -> str:
    return "classified" if test_family != "unknown" else "needs_review"
