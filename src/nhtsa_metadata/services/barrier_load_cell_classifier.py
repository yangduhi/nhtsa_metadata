from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    Barrier,
    BarrierLoadCellChannelMap,
    BarrierLoadCellClassification,
    CrashTest,
    InstrumentationChannel,
)

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "nhtsa_barrier_load_cell_classification_config_v2.2.2.json"
)

LEGACY_4X9_RE = re.compile(r"^LOAD CELL (?P<row_letter>[A-D])(?P<col>[1-9])$")
ROW_COLUMN_RE = re.compile(r"^LOAD CELL ROW (?P<row>\d+) COLUMN (?P<col>\d+)$")
POLE_MODERN_RE = re.compile(r"^LOAD CELL POLE (?P<pole_index>\d+)$")
POLE_ATTACHMENT_RE = re.compile(r"^POLE$")
POLE_COMMENTARY_RE = re.compile(r"LOAD CELL (?P<pole_index>\d+)")
WHITESPACE_RE = re.compile(r"\s+")

CONFIG_VERSION_FALLBACK = "2.2.2-db2011plus-shape-normalized-metadata-explicit-final"
WALL_FAMILY = "frontal_or_flat_load_cell_wall"
POLE_FAMILY = "side_pole_load_cell_barrier"
MINIMAL_RULES: tuple[dict[str, str], ...] = (
    {
        "id": "legacy_4x9_us_ncap",
        "family": WALL_FAMILY,
        "classification_status": "covered",
        "source_status": "official_reference_and_db_observed",
    },
    {
        "id": "high_res_8x16_128",
        "family": WALL_FAMILY,
        "classification_status": "covered_with_geometry_caveat",
        "source_status": "official_reference_and_db_observed",
    },
    {
        "id": "partial_8x16_127_missing_one_force_channel",
        "family": WALL_FAMILY,
        "classification_status": "covered_with_mask",
        "source_status": "db_observed",
    },
    {
        "id": "extended_height_10x16_160",
        "family": WALL_FAMILY,
        "classification_status": "covered",
        "source_status": "db_observed",
    },
    {
        "id": "advanced_11x16_128_active",
        "family": WALL_FAMILY,
        "classification_status": "covered_with_active_cell_mask",
        "source_status": "db_observed",
    },
    {
        "id": "advanced_11x16_176_full",
        "family": WALL_FAMILY,
        "classification_status": "covered",
        "source_status": "db_observed",
    },
    {
        "id": "side_pole_load_cell_8",
        "family": POLE_FAMILY,
        "classification_status": "covered_with_mask",
        "source_status": "db_observed",
    },
)


@dataclass(frozen=True)
class ParsedLoadCellChannel:
    channel_id: int
    test_id: int
    test_no: int
    curve_no: int
    attachment_raw: str | None
    commentary_raw: str | None
    pattern_kind: str
    parsed_row: int | None
    parsed_col: int | None
    parsed_row_letter: str | None
    parsed_pole_index: int | None
    quantity_type: str
    raw_axis: str | None
    canonical_axis: str | None
    unit_raw: str | None
    generated_loma_name: str | None
    evidence_json: dict[str, Any]


@dataclass(frozen=True)
class ShapeAlias:
    raw_barrier_shape: str | None
    normalized_key: str
    alias_rule_id: str
    confidence: float
    is_conditional: bool
    evidence_json: dict[str, Any]


@dataclass(frozen=True)
class ClassificationDraft:
    barrier: Barrier
    alias: ShapeAlias
    classification_id: str
    family: str
    classification_status: str
    channels: list[ParsedLoadCellChannel]
    expected_force_cells: set[tuple[int, int]]
    evidence_json: dict[str, Any]


@dataclass(frozen=True)
class LoadCellClassificationSummary:
    config_version: str
    classification_ids: list[str]
    families: list[str]
    channel_count: int
    force_channel_count: int
    moment_channel_count: int


class BarrierLoadCellClassifier:
    def __init__(self, session: Session, config_path: Path | None = None) -> None:
        self.session = session
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config = _load_config(self.config_path)
        self.config_version = _config_version(self.config)
        self.rule_by_id = {
            str(rule["id"]): rule for rule in self.config.get("classification_rules", [])
        }

    def classify_test(self, test_no: int) -> list[ClassificationDraft]:
        test = self.session.scalar(select(CrashTest).where(CrashTest.test_no == test_no))
        if test is None:
            return []
        barriers = list(self.session.scalars(select(Barrier).where(Barrier.test_id == test.id)))
        channels = list(
            self.session.scalars(
                select(InstrumentationChannel).where(InstrumentationChannel.test_id == test.id)
            )
        )
        parsed_channels = [
            parsed
            for channel in channels
            if (parsed := _parse_load_cell_channel(channel)) is not None
        ]
        drafts: list[ClassificationDraft] = []
        for barrier in barriers:
            alias = _normalize_barrier_shape(test, barrier, parsed_channels)
            if alias is None:
                continue
            draft = self._classify_barrier(barrier, alias, parsed_channels)
            if draft is not None:
                drafts.append(draft)
        return drafts

    def rebuild_for_test(self, test_no: int) -> LoadCellClassificationSummary:
        self._delete_existing(test_no)
        drafts = self.classify_test(test_no)
        for draft in drafts:
            self._persist_draft(draft)
        self.session.flush()
        return _summary_from_drafts(self.config_version, drafts)

    def clear_for_test(self, test_no: int) -> None:
        self._delete_existing(test_no)

    def _delete_existing(self, test_no: int) -> None:
        classification_ids = list(
            self.session.scalars(
                select(BarrierLoadCellClassification.id).where(
                    BarrierLoadCellClassification.test_no == test_no,
                    BarrierLoadCellClassification.config_version == self.config_version,
                )
            )
        )
        if classification_ids:
            self.session.execute(
                delete(BarrierLoadCellChannelMap).where(
                    BarrierLoadCellChannelMap.classification_id.in_(classification_ids)
                )
            )
        self.session.execute(
            delete(BarrierLoadCellClassification).where(
                BarrierLoadCellClassification.test_no == test_no,
                BarrierLoadCellClassification.config_version == self.config_version,
            )
        )
        self.session.flush()

    def _classify_barrier(
        self,
        barrier: Barrier,
        alias: ShapeAlias,
        channels: list[ParsedLoadCellChannel],
    ) -> ClassificationDraft | None:
        legacy_channels = [
            channel for channel in channels if channel.pattern_kind == "legacy_4x9"
        ]
        row_column_channels = [
            channel for channel in channels if channel.pattern_kind == "row_column_wall"
        ]
        pole_channels = [
            channel for channel in channels if channel.pattern_kind.startswith("pole_")
        ]
        if alias.normalized_key == "POLE":
            return self._classify_pole(barrier, alias, pole_channels)
        if (
            alias.normalized_key in {"LOAD_CELL_BARRIER", "FLAT_BARRIER_LEGACY_LOAD_CELL"}
            and _force_count(legacy_channels) == 36
            and _row_letters(legacy_channels) == ["A", "B", "C", "D"]
            and _col_range(legacy_channels) == [1, 9]
        ):
            return self._make_draft(
                barrier,
                alias,
                "legacy_4x9_us_ncap",
                legacy_channels,
                _grid(1, 4, 1, 9),
            )
        if alias.normalized_key not in {"LOAD_CELL_BARRIER", "OTHER_LOAD_CELL_BARRIER_REVIEWED"}:
            return None
        return self._classify_wall_grid(barrier, alias, row_column_channels)

    def _classify_pole(
        self,
        barrier: Barrier,
        alias: ShapeAlias,
        pole_channels: list[ParsedLoadCellChannel],
    ) -> ClassificationDraft | None:
        force_count = _force_count(pole_channels)
        if force_count not in {6, 8, 9}:
            return None
        return self._make_draft(
            barrier,
            alias,
            "side_pole_load_cell_8",
            [channel for channel in pole_channels if channel.quantity_type == "force"],
            set(),
        )

    def _classify_wall_grid(
        self,
        barrier: Barrier,
        alias: ShapeAlias,
        channels: list[ParsedLoadCellChannel],
    ) -> ClassificationDraft | None:
        force_count = _force_count(channels)
        row_range = _row_range(channels)
        col_range = _col_range(channels)
        unique_rows = len(_row_set(channels))
        unique_cols = len(_col_set(channels))
        if force_count == 127 and row_range == [2, 9] and col_range == [1, 16]:
            return self._make_draft(
                barrier,
                alias,
                "partial_8x16_127_missing_one_force_channel",
                channels,
                _grid(2, 9, 1, 16),
            )
        if force_count == 176 and row_range == [1, 11] and col_range == [1, 16]:
            return self._make_draft(
                barrier,
                alias,
                "advanced_11x16_176_full",
                channels,
                _grid(1, 11, 1, 16),
            )
        if force_count == 160 and row_range == [2, 11] and col_range == [1, 16]:
            return self._make_draft(
                barrier,
                alias,
                "extended_height_10x16_160",
                channels,
                _grid(2, 11, 1, 16),
            )
        if force_count == 128 and row_range == [4, 11] and col_range == [1, 16]:
            return self._make_draft(
                barrier,
                alias,
                "advanced_11x16_128_active",
                channels,
                _grid(4, 11, 1, 16),
            )
        if force_count == 128 and unique_rows == 8 and unique_cols == 16 and col_range == [1, 16]:
            return self._make_draft(
                barrier,
                alias,
                "high_res_8x16_128",
                channels,
                {
                    (channel.parsed_row, channel.parsed_col)
                    for channel in channels
                    if channel.quantity_type == "force"
                    and channel.parsed_row is not None
                    and channel.parsed_col is not None
                },
            )
        return None

    def _make_draft(
        self,
        barrier: Barrier,
        alias: ShapeAlias,
        classification_id: str,
        channels: list[ParsedLoadCellChannel],
        expected_force_cells: set[tuple[int, int]],
    ) -> ClassificationDraft:
        rule = self.rule_by_id[classification_id]
        family = str(rule["family"])
        status = str(rule["classification_status"])
        return ClassificationDraft(
            barrier=barrier,
            alias=alias,
            classification_id=classification_id,
            family=family,
            classification_status=status,
            channels=[
                channel for channel in channels if channel.quantity_type in {"force", "moment"}
            ],
            expected_force_cells=expected_force_cells,
            evidence_json={
                "config_version": self.config_version,
                "rule_source_status": rule.get("source_status"),
                "shape_alias_evidence": alias.evidence_json,
                "rule_required_masks": rule.get("required_masks", []),
            },
        )

    def _persist_draft(self, draft: ClassificationDraft) -> None:
        force_channels = [channel for channel in draft.channels if channel.quantity_type == "force"]
        moment_channels = [
            channel for channel in draft.channels if channel.quantity_type == "moment"
        ]
        row_values = sorted(
            {
                channel.parsed_row
                for channel in draft.channels
                if channel.parsed_row is not None
            }
        )
        col_values = sorted(
            {
                channel.parsed_col
                for channel in draft.channels
                if channel.parsed_col is not None
            }
        )
        pole_values = sorted(
            {
                channel.parsed_pole_index
                for channel in draft.channels
                if channel.parsed_pole_index is not None
            }
        )
        missing = _missing_force_cells(force_channels, draft.expected_force_cells)
        duplicates = _duplicate_cells(force_channels)
        classification = BarrierLoadCellClassification(
            test_id=draft.barrier.test_id,
            test_no=draft.barrier.test_no,
            barrier_id=draft.barrier.id,
            config_version=self.config_version,
            classification_id=draft.classification_id,
            family=draft.family,
            classification_status=draft.classification_status,
            raw_barrier_shape=draft.alias.raw_barrier_shape,
            normalized_barrier_shape_key=draft.alias.normalized_key,
            shape_alias_rule_id=draft.alias.alias_rule_id,
            shape_alias_confidence=draft.alias.confidence,
            shape_alias_is_conditional=draft.alias.is_conditional,
            row_count=len(row_values) or None,
            col_count=len(col_values) or None,
            row_range_json=_range_from_values(row_values),
            col_range_json=_range_from_values(col_values),
            pole_index_range_json=_range_from_values(pole_values),
            channel_count=len(draft.channels),
            force_channel_count=len(force_channels),
            moment_channel_count=len(moment_channels),
            missing_expected_channels_json=missing,
            duplicate_channels_json=duplicates,
            occupancy_map_json=_occupancy_map(force_channels),
            mask_summary_json={
                "missing_expected_channel_count": len(missing),
                "duplicate_channel_count": len(duplicates),
                "force_channel_count": len(force_channels),
                "moment_channel_count": len(moment_channels),
            },
            evidence_json=draft.evidence_json,
        )
        self.session.add(classification)
        self.session.flush()
        for channel in draft.channels:
            self.session.add(
                BarrierLoadCellChannelMap(
                    classification_id=classification.id,
                    test_id=channel.test_id,
                    test_no=channel.test_no,
                    instrumentation_channel_id=channel.channel_id,
                    curve_no=channel.curve_no,
                    sensor_attachment_raw=channel.attachment_raw,
                    instrumentation_commentary=channel.commentary_raw,
                    parsed_row=channel.parsed_row,
                    parsed_col=channel.parsed_col,
                    parsed_row_letter=channel.parsed_row_letter,
                    parsed_pole_index=channel.parsed_pole_index,
                    quantity_type=channel.quantity_type,
                    raw_axis=channel.raw_axis,
                    canonical_axis=channel.canonical_axis,
                    unit_raw=channel.unit_raw,
                    generated_loma_name=channel.generated_loma_name,
                    mask_flags_json=_mask_flags(channel, missing, duplicates),
                    evidence_json=channel.evidence_json,
                )
            )


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "meta_info": {"version": CONFIG_VERSION_FALLBACK},
            "classification_rules": list(MINIMAL_RULES),
        }
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _config_version(config: dict[str, Any]) -> str:
    meta_info = config.get("meta_info", {})
    if isinstance(meta_info, dict):
        version = meta_info.get("version")
        if isinstance(version, str):
            return version
    return CONFIG_VERSION_FALLBACK


def _parse_load_cell_channel(
    channel: InstrumentationChannel,
) -> ParsedLoadCellChannel | None:
    raw = channel.raw_row_json if isinstance(channel.raw_row_json, dict) else {}
    sensor_type = _first_text(channel.sensor_type, raw.get("SENTYPD"), raw.get("sensorType"))
    if sensor_type is None or "LOAD CELL" not in _clean(sensor_type):
        return None
    attachment = _first_text(channel.sensor_attachment, raw.get("SENATTD"))
    attachment_key = _clean(attachment)
    commentary = _first_text(raw.get("INSCOM"), raw.get("instrumentationCommentary"))
    commentary_key = _clean(commentary)
    quantity_type = _quantity_type(raw.get("YTYPE"), raw.get("YUNITSD"), channel.unit_raw)
    if quantity_type == "other":
        return None
    match = LEGACY_4X9_RE.match(attachment_key)
    if match is not None:
        row_letter = match.group("row_letter")
        parsed_col = int(match.group("col"))
        parsed_row = {"A": 1, "B": 2, "C": 3, "D": 4}[row_letter]
        return _parsed_channel(
            channel,
            raw,
            attachment,
            commentary,
            "legacy_4x9",
            parsed_row,
            parsed_col,
            row_letter,
            None,
            quantity_type,
        )
    match = ROW_COLUMN_RE.match(attachment_key)
    if match is not None:
        return _parsed_channel(
            channel,
            raw,
            attachment,
            commentary,
            "row_column_wall",
            int(match.group("row")),
            int(match.group("col")),
            None,
            None,
            quantity_type,
        )
    match = POLE_MODERN_RE.match(attachment_key)
    if match is not None:
        return _parsed_channel(
            channel,
            raw,
            attachment,
            commentary,
            "pole_modern",
            None,
            None,
            None,
            int(match.group("pole_index")),
            quantity_type,
        )
    match = POLE_ATTACHMENT_RE.match(attachment_key)
    commentary_match = POLE_COMMENTARY_RE.search(commentary_key)
    if match is not None and commentary_match is not None:
        return _parsed_channel(
            channel,
            raw,
            attachment,
            commentary,
            "pole_legacy",
            None,
            None,
            None,
            int(commentary_match.group("pole_index")),
            quantity_type,
        )
    return None


def _parsed_channel(
    channel: InstrumentationChannel,
    raw: dict[str, Any],
    attachment: str | None,
    commentary: str | None,
    pattern_kind: str,
    parsed_row: int | None,
    parsed_col: int | None,
    parsed_row_letter: str | None,
    parsed_pole_index: int | None,
    quantity_type: str,
) -> ParsedLoadCellChannel:
    raw_axis = _first_text(channel.sensor_axis, raw.get("AXISD"))
    unit_raw = _first_text(channel.unit_raw, raw.get("YUNITSD"))
    return ParsedLoadCellChannel(
        channel_id=channel.id,
        test_id=channel.test_id,
        test_no=channel.test_no,
        curve_no=channel.curve_no,
        attachment_raw=attachment,
        commentary_raw=commentary,
        pattern_kind=pattern_kind,
        parsed_row=parsed_row,
        parsed_col=parsed_col,
        parsed_row_letter=parsed_row_letter,
        parsed_pole_index=parsed_pole_index,
        quantity_type=quantity_type,
        raw_axis=raw_axis,
        canonical_axis=_canonical_axis(raw_axis, quantity_type),
        unit_raw=unit_raw,
        generated_loma_name=_generated_loma_name(
            parsed_row,
            parsed_col,
            quantity_type,
            raw_axis,
        ),
        evidence_json={
            "curve_no": channel.curve_no,
            "sensor_type": channel.sensor_type,
            "sensor_attachment": channel.sensor_attachment,
            "sensor_axis": channel.sensor_axis,
            "unit_raw": channel.unit_raw,
            "raw_YTYPE": raw.get("YTYPE"),
            "raw_YUNITSD": raw.get("YUNITSD"),
            "raw_SENATTD": raw.get("SENATTD"),
            "raw_AXISD": raw.get("AXISD"),
            "raw_INSCOM": raw.get("INSCOM"),
        },
    )


def _normalize_barrier_shape(
    test: CrashTest,
    barrier: Barrier,
    channels: list[ParsedLoadCellChannel],
) -> ShapeAlias | None:
    raw = barrier.raw_row_json if isinstance(barrier.raw_row_json, dict) else {}
    raw_shape = _first_text(barrier.shape, raw.get("barrierShape"), raw.get("BARSHPD"))
    shape_key = _clean(raw_shape)
    if shape_key in {
        "LOAD CELL BARRIER",
        "8 X 16 + 6 LOAD CELL BARRIER",
        "8 X 16 LOAD CELL BARRIER",
    }:
        return ShapeAlias(
            raw_shape,
            "LOAD_CELL_BARRIER",
            "load_cell_barrier_wall_unconditional",
            1.0,
            False,
            {"raw_shape": raw_shape},
        )
    if shape_key == "POLE":
        return ShapeAlias(
            raw_shape,
            "POLE",
            "pole_barrier_unconditional",
            1.0,
            False,
            {"raw_shape": raw_shape},
        )
    legacy_channels = [channel for channel in channels if channel.pattern_kind == "legacy_4x9"]
    if (
        shape_key == "FLAT BARRIER"
        and _force_count(legacy_channels) == 36
        and _row_letters(legacy_channels) == ["A", "B", "C", "D"]
        and _col_range(legacy_channels) == [1, 9]
        and not any(channel.pattern_kind.startswith("pole_") for channel in channels)
    ):
        return ShapeAlias(
            raw_shape,
            "FLAT_BARRIER_LEGACY_LOAD_CELL",
            "flat_barrier_legacy_4x9_load_cell",
            0.95,
            True,
            {
                "raw_shape": raw_shape,
                "force_channel_count": _force_count(legacy_channels),
                "row_letters": _row_letters(legacy_channels),
                "col_range": _col_range(legacy_channels),
            },
        )
    row_channels = [channel for channel in channels if channel.pattern_kind == "row_column_wall"]
    if (
        shape_key == "OTHER"
        and _force_count(row_channels) == 160
        and _row_range(row_channels) == [2, 11]
        and _col_range(row_channels) == [1, 16]
        and _has_load_cell_evidence_text(test, barrier, channels)
    ):
        return ShapeAlias(
            raw_shape,
            "OTHER_LOAD_CELL_BARRIER_REVIEWED",
            "other_high_resolution_load_cell_barrier_by_evidence",
            0.9,
            True,
            {
                "raw_shape": raw_shape,
                "force_channel_count": _force_count(row_channels),
                "row_range": _row_range(row_channels),
                "col_range": _col_range(row_channels),
            },
        )
    return None


def _has_load_cell_evidence_text(
    test: CrashTest,
    barrier: Barrier,
    channels: list[ParsedLoadCellChannel],
) -> bool:
    raw = barrier.raw_row_json if isinstance(barrier.raw_row_json, dict) else {}
    values: list[Any] = [
        barrier.shape,
        raw.get("barrierShape"),
        raw.get("BARSHPD"),
        raw.get("barrierCommentary"),
        raw.get("BARCOM"),
        test.contractor_study_title,
        test.test_type,
        test.test_configuration,
    ]
    values.extend(channel.commentary_raw for channel in channels)
    text = " ".join(str(value) for value in values if value not in (None, ""))
    return "LOAD CELL" in _clean(text)


def _summary_from_drafts(
    config_version: str,
    drafts: list[ClassificationDraft],
) -> LoadCellClassificationSummary:
    return LoadCellClassificationSummary(
        config_version=config_version,
        classification_ids=sorted({draft.classification_id for draft in drafts}),
        families=sorted({draft.family for draft in drafts}),
        channel_count=sum(len(draft.channels) for draft in drafts),
        force_channel_count=sum(_force_count(draft.channels) for draft in drafts),
        moment_channel_count=sum(_moment_count(draft.channels) for draft in drafts),
    )


def _quantity_type(*values: Any) -> str:
    text = " ".join(_clean(value) for value in values if value not in (None, ""))
    if (
        "MOMENT" in text
        or "KN*M" in text
        or "N*M" in text
        or "LBF*FT" in text
        or "NEWTON-METER" in text
        or "NEWTON METER" in text
    ):
        return "moment"
    if (
        "FORCE" in text
        or text in {"KN", "N", "LBF"}
        or "NEWTONS" in text
        or "NEWTON" in text
        or "LBF" in text
    ):
        return "force"
    return "other"


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value not in (None, ""):
            return str(value)
    return None


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return WHITESPACE_RE.sub(" ", str(value).strip().upper())


def _canonical_axis(raw_axis: str | None, quantity_type: str) -> str | None:
    axis = _clean(raw_axis)
    if not axis:
        return None
    if quantity_type == "force":
        return f"force_axis_{axis}"
    if quantity_type == "moment":
        return f"moment_axis_{axis}"
    return axis


def _generated_loma_name(
    row: int | None,
    col: int | None,
    quantity_type: str,
    raw_axis: str | None,
) -> str | None:
    if row is None or col is None:
        return None
    quantity_code = "FO" if quantity_type == "force" else "MO"
    axis_digits = "".join(char for char in _clean(raw_axis) if char.isdigit())
    axis = axis_digits[-1:] or "0"
    return f"00LOMA{row:02d}{col:02d}00{quantity_code}{axis}P"


def _force_count(channels: list[ParsedLoadCellChannel]) -> int:
    return sum(1 for channel in channels if channel.quantity_type == "force")


def _moment_count(channels: list[ParsedLoadCellChannel]) -> int:
    return sum(1 for channel in channels if channel.quantity_type == "moment")


def _row_set(channels: list[ParsedLoadCellChannel]) -> set[int]:
    return {
        channel.parsed_row
        for channel in channels
        if channel.quantity_type == "force" and channel.parsed_row is not None
    }


def _col_set(channels: list[ParsedLoadCellChannel]) -> set[int]:
    return {
        channel.parsed_col
        for channel in channels
        if channel.quantity_type == "force" and channel.parsed_col is not None
    }


def _row_range(channels: list[ParsedLoadCellChannel]) -> list[int] | None:
    return _range_from_values(sorted(_row_set(channels)))


def _col_range(channels: list[ParsedLoadCellChannel]) -> list[int] | None:
    return _range_from_values(sorted(_col_set(channels)))


def _row_letters(channels: list[ParsedLoadCellChannel]) -> list[str]:
    return sorted(
        {
            channel.parsed_row_letter
            for channel in channels
            if channel.quantity_type == "force" and channel.parsed_row_letter is not None
        }
    )


def _range_from_values(values: list[int]) -> list[int] | None:
    if not values:
        return None
    return [min(values), max(values)]


def _grid(row_min: int, row_max: int, col_min: int, col_max: int) -> set[tuple[int, int]]:
    return {
        (row, col)
        for row in range(row_min, row_max + 1)
        for col in range(col_min, col_max + 1)
    }


def _channel_cell(channel: ParsedLoadCellChannel) -> tuple[int, int] | None:
    if channel.parsed_row is None or channel.parsed_col is None:
        return None
    return (channel.parsed_row, channel.parsed_col)


def _missing_force_cells(
    force_channels: list[ParsedLoadCellChannel],
    expected_cells: set[tuple[int, int]],
) -> list[dict[str, int]]:
    if not expected_cells:
        return []
    observed = {
        cell for channel in force_channels if (cell := _channel_cell(channel)) is not None
    }
    return [
        {"row": row, "col": col}
        for row, col in sorted(expected_cells - observed)
    ]


def _duplicate_cells(force_channels: list[ParsedLoadCellChannel]) -> list[dict[str, int]]:
    wall_counts = Counter(
        cell for channel in force_channels if (cell := _channel_cell(channel)) is not None
    )
    pole_counts = Counter(
        channel.parsed_pole_index
        for channel in force_channels
        if channel.parsed_pole_index is not None
    )
    duplicates = [
        {"row": row, "col": col, "count": count}
        for (row, col), count in sorted(wall_counts.items())
        if count > 1
    ]
    duplicates.extend(
        {"pole_index": pole_index, "count": count}
        for pole_index, count in sorted(pole_counts.items())
        if count > 1
    )
    return duplicates


def _occupancy_map(force_channels: list[ParsedLoadCellChannel]) -> dict[str, Any]:
    cells = sorted(
        cell for channel in force_channels if (cell := _channel_cell(channel)) is not None
    )
    pole_indices = sorted(
        channel.parsed_pole_index
        for channel in force_channels
        if channel.parsed_pole_index is not None
    )
    return {
        "wall_cells": [{"row": row, "col": col} for row, col in cells],
        "pole_indices": pole_indices,
    }


def _mask_flags(
    channel: ParsedLoadCellChannel,
    missing: list[dict[str, int]],
    duplicates: list[dict[str, int]],
) -> list[str]:
    flags = ["active_channel"]
    if channel.quantity_type == "force":
        flags.append("valid_force")
    if channel.quantity_type == "moment":
        flags.append("valid_moment")
    cell = _channel_cell(channel)
    if cell is not None and any(
        item.get("row") == cell[0] and item.get("col") == cell[1] for item in duplicates
    ):
        flags.append("duplicate_channel")
    if channel.parsed_pole_index is not None and any(
        item.get("pole_index") == channel.parsed_pole_index for item in duplicates
    ):
        flags.append("duplicate_channel")
    if missing:
        flags.append("expected_channel_mask_available")
    return flags
