from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, RowMapping

RATING_CANDIDATE_TABLE = "nhtsa_rating_match_candidates"

RATING_FIELD_MAP = {
    "OverallRating": "overall_rating",
    "OverallFrontCrashRating": "overall_front_crash_rating",
    "FrontCrashDriversideRating": "front_crash_driver_side_rating",
    "FrontCrashPassengersideRating": "front_crash_passenger_side_rating",
    "OverallSideCrashRating": "overall_side_crash_rating",
    "SideCrashDriversideRating": "side_crash_driver_side_rating",
    "SideCrashPassengersideRating": "side_crash_passenger_side_rating",
    "sideBarrierRating-Overall": "side_barrier_rating_overall",
    "combinedSideBarrierAndPoleRating-Front": "combined_side_barrier_and_pole_rating_front",
    "combinedSideBarrierAndPoleRating-Rear": "combined_side_barrier_and_pole_rating_rear",
    "SidePoleCrashRating": "side_pole_crash_rating",
    "RolloverRating": "rollover_rating",
    "RolloverPossibility": "rollover_possibility",
    "dynamicTipResult": "dynamic_tip_result",
    "NHTSAElectronicStabilityControl": "nhtsa_electronic_stability_control",
    "NHTSAForwardCollisionWarning": "nhtsa_forward_collision_warning",
    "NHTSALaneDepartureWarning": "nhtsa_lane_departure_warning",
    "ComplaintsCount": "complaints_count",
    "RecallsCount": "recalls_count",
    "InvestigationCount": "investigation_count",
}

BASE_COLUMNS = {
    "row_key": "TEXT NOT NULL",
    "test_no": "INTEGER NOT NULL",
    "source_vehicle_no": "INTEGER",
    "db_make": "TEXT",
    "db_model": "TEXT",
    "db_model_year": "INTEGER",
    "db_body_type": "TEXT",
    "db_body_style": "TEXT",
    "db_vin": "TEXT",
    "match_method": "TEXT",
    "match_confidence": "TEXT",
    "query_make": "TEXT",
    "query_model": "TEXT",
    "variant_count": "INTEGER",
    "candidate_rank": "INTEGER NOT NULL",
    "candidate_score": "INTEGER",
    "candidate_score_reasons": "TEXT",
    "rating_vehicle_id": "INTEGER NOT NULL",
    "rating_vehicle_description": "TEXT",
    "vpic_make": "TEXT",
    "vpic_model": "TEXT",
    "vpic_series": "TEXT",
    "vpic_trim": "TEXT",
    "vpic_body_class": "TEXT",
    "vpic_drive_type": "TEXT",
    "generated_at": "TEXT NOT NULL",
}

OFFICIAL_HANDLING = {
    "source_url": "https://www.nhtsa.gov/nhtsa-datasets-and-apis#ratings",
    "variant_query": "modelyear/{year}/make/{make}/model/{model}",
    "rating_query": "VehicleId/{vehicle_id}",
    "selection_rule": (
        "NHTSA first returns available vehicle variants for a selected Model Year, Make "
        "and Model; ratings are then requested for the selected variant Vehicle Id."
    ),
    "local_policy": (
        "Store all VehicleId candidates in an overlay. Auto-select only single-variant "
        "or high-confidence DB/vPIC-disambiguated candidates; keep ambiguous candidates "
        "visible for review."
    ),
}


def ensure_safety_rating_overlay_schema(engine: Engine) -> None:
    column_sql = [f"{name} {ddl}" for name, ddl in BASE_COLUMNS.items()]
    column_sql.extend(f"{db_column} TEXT" for db_column in RATING_FIELD_MAP.values())
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {RATING_CANDIDATE_TABLE} (
        {', '.join(column_sql)},
        PRIMARY KEY (row_key, rating_vehicle_id)
    )
    """
    with engine.begin() as connection:
        connection.execute(text(ddl))
        connection.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_{RATING_CANDIDATE_TABLE}_test_no "
                f"ON {RATING_CANDIDATE_TABLE}(test_no)"
            )
        )
        connection.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_{RATING_CANDIDATE_TABLE}_confidence "
                f"ON {RATING_CANDIDATE_TABLE}(match_confidence)"
            )
        )
        connection.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_{RATING_CANDIDATE_TABLE}_rank "
                f"ON {RATING_CANDIDATE_TABLE}(candidate_rank)"
            )
        )


def safety_rating_overlay_available(engine: Engine) -> bool:
    return RATING_CANDIDATE_TABLE in set(inspect(engine).get_table_names())


def upsert_safety_rating_overlay_rows(
    engine: Engine,
    rows: list[dict[str, Any]],
    *,
    generated_at: str | None = None,
    replace_existing: bool = False,
) -> None:
    ensure_safety_rating_overlay_schema(engine)
    generated = generated_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    insert_columns = list(BASE_COLUMNS) + list(RATING_FIELD_MAP.values())
    placeholders = ", ".join(f":{column}" for column in insert_columns)
    update_columns = [
        column for column in insert_columns if column not in {"row_key", "rating_vehicle_id"}
    ]
    update_sql = ", ".join(f"{column}=excluded.{column}" for column in update_columns)
    sql = text(
        f"INSERT INTO {RATING_CANDIDATE_TABLE} ({', '.join(insert_columns)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT(row_key, rating_vehicle_id) DO UPDATE SET {update_sql}"
    )
    normalized = [_normalize_overlay_row(row, generated) for row in rows]
    with engine.begin() as connection:
        if replace_existing:
            connection.execute(text(f"DELETE FROM {RATING_CANDIDATE_TABLE}"))
        if normalized:
            connection.execute(sql, normalized)


def safety_rating_overlay_summary(engine: Engine) -> dict[str, object]:
    if not safety_rating_overlay_available(engine):
        return {
            "available": False,
            "source": "nhtsa_safety_ratings_overlay",
            "reason": "overlay_table_not_installed",
            "official_handling": OFFICIAL_HANDLING,
            "metrics": {},
        }
    with engine.connect() as connection:
        metrics = {
            "candidate_rows": _scalar_int(
                connection.execute(text(f"SELECT COUNT(*) FROM {RATING_CANDIDATE_TABLE}")).scalar()
            ),
            "matched_subject_rows": _scalar_int(
                connection.execute(
                    text(f"SELECT COUNT(DISTINCT row_key) FROM {RATING_CANDIDATE_TABLE}")
                ).scalar()
            ),
            "ambiguous_subject_rows": _scalar_int(
                connection.execute(
                    text(
                        f"SELECT COUNT(DISTINCT row_key) FROM {RATING_CANDIDATE_TABLE} "
                        "WHERE variant_count > 1"
                    )
                ).scalar()
            ),
            "review_subject_rows": _scalar_int(
                connection.execute(
                    text(
                        f"SELECT COUNT(DISTINCT row_key) FROM {RATING_CANDIDATE_TABLE} "
                        "WHERE candidate_rank = 1 "
                        "AND match_confidence IN "
                        "('REVIEW_AMBIGUOUS_VARIANT', 'MEDIUM_RANKED')"
                    )
                ).scalar()
            ),
            "auto_selected_subject_rows": _scalar_int(
                connection.execute(
                    text(
                        f"SELECT COUNT(DISTINCT row_key) FROM {RATING_CANDIDATE_TABLE} "
                        "WHERE candidate_rank = 1 "
                        "AND match_confidence IN "
                        "('HIGH_SINGLE_VARIANT', 'HIGH_DISAMBIGUATED', "
                        "'HIGH_EQUIVALENT_RATING', 'HIGH_TOP_EQUIVALENT_RATING', "
                        "'HIGH_REPORT_DISAMBIGUATED')"
                    )
                ).scalar()
            ),
        }
        confidence_rows = connection.execute(
            text(
                f"SELECT match_confidence, COUNT(DISTINCT row_key) AS count "
                f"FROM {RATING_CANDIDATE_TABLE} WHERE candidate_rank = 1 "
                "GROUP BY match_confidence ORDER BY count DESC, match_confidence"
            )
        ).mappings()
        method_rows = connection.execute(
            text(
                f"SELECT match_method, COUNT(DISTINCT row_key) AS count "
                f"FROM {RATING_CANDIDATE_TABLE} WHERE candidate_rank = 1 "
                "GROUP BY match_method ORDER BY count DESC, match_method"
            )
        ).mappings()
        generated_at = connection.execute(
            text(f"SELECT MAX(generated_at) FROM {RATING_CANDIDATE_TABLE}")
        ).scalar()
    return {
        "available": True,
        "source": "nhtsa_safety_ratings_overlay",
        "official_handling": OFFICIAL_HANDLING,
        "generated_at": generated_at,
        "metrics": metrics,
        "confidence_counts": {
            str(row["match_confidence"]): row["count"] for row in confidence_rows
        },
        "method_counts": {str(row["match_method"]): row["count"] for row in method_rows},
    }


def safety_rating_match_for_test(engine: Engine, test_no: int) -> dict[str, object]:
    if not safety_rating_overlay_available(engine):
        return {"available": False, "test_no": test_no, "found": False, "subjects": []}
    with engine.connect() as connection:
        rows = list(
            connection.execute(
                text(
                    f"SELECT * FROM {RATING_CANDIDATE_TABLE} "
                    "WHERE test_no = :test_no "
                    "ORDER BY source_vehicle_no, row_key, candidate_rank, rating_vehicle_id"
                ),
                {"test_no": test_no},
            )
            .mappings()
            .all()
        )
    if not rows:
        return {"available": True, "test_no": test_no, "found": False, "subjects": []}
    grouped: dict[str, list[RowMapping]] = defaultdict(list)
    for row in rows:
        grouped[str(row["row_key"])].append(row)
    subjects = [_subject_group_out(group_rows) for group_rows in grouped.values()]
    return {"available": True, "test_no": test_no, "found": True, "subjects": subjects}


def _normalize_overlay_row(row: dict[str, Any], generated_at: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for column in BASE_COLUMNS:
        if column == "generated_at":
            normalized[column] = row.get(column) or generated_at
        else:
            normalized[column] = row.get(column)
    for api_field, db_column in RATING_FIELD_MAP.items():
        normalized[db_column] = row.get(api_field, row.get(db_column))
    return normalized


def _subject_group_out(rows: list[RowMapping]) -> dict[str, object]:
    sorted_rows = sorted(rows, key=lambda row: int(row["candidate_rank"] or 0))
    top = sorted_rows[0]
    candidates = [_candidate_out(row) for row in sorted_rows]
    return {
        "row_key": top["row_key"],
        "test_no": top["test_no"],
        "source_vehicle_no": top["source_vehicle_no"],
        "db_vehicle": {
            "make": top["db_make"],
            "model": top["db_model"],
            "model_year": top["db_model_year"],
            "body_type": top["db_body_type"],
            "body_style": top["db_body_style"],
            "vin": top["db_vin"],
        },
        "query": {"make": top["query_make"], "model": top["query_model"]},
        "match_method": top["match_method"],
        "match_confidence": top["match_confidence"],
        "selection_status": _selection_status(str(top["match_confidence"] or "")),
        "variant_count": top["variant_count"],
        "top_candidate": candidates[0],
        "candidates": candidates,
    }


def _candidate_out(row: RowMapping) -> dict[str, object]:
    candidate: dict[str, object] = {
        "candidate_rank": row["candidate_rank"],
        "candidate_score": row["candidate_score"],
        "candidate_score_reasons": row["candidate_score_reasons"],
        "rating_vehicle_id": row["rating_vehicle_id"],
        "rating_vehicle_description": row["rating_vehicle_description"],
    }
    for api_field, db_column in RATING_FIELD_MAP.items():
        candidate[api_field] = row[db_column]
    return candidate


def _selection_status(match_confidence: str) -> str:
    if match_confidence == "HIGH_SINGLE_VARIANT":
        return "auto_selected_single_variant"
    if match_confidence == "HIGH_DISAMBIGUATED":
        return "auto_high_candidate"
    if match_confidence == "HIGH_REPORT_DISAMBIGUATED":
        return "auto_report_evidence"
    if match_confidence == "HIGH_EQUIVALENT_RATING":
        return "auto_equivalent_rating"
    if match_confidence == "HIGH_TOP_EQUIVALENT_RATING":
        return "auto_top_equivalent_rating"
    if match_confidence == "MEDIUM_RANKED":
        return "ranked_candidate_reviewable"
    return "review_required"


def _scalar_int(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, (str, bytes, float)):
        return int(value)
    return 0
