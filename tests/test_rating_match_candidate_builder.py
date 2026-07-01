from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_nhtsa_rating_match_candidates.py"
)
spec = importlib.util.spec_from_file_location("rating_match_builder", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
rating_match_builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rating_match_builder
spec.loader.exec_module(rating_match_builder)


class FakeClient:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def get_json(self, url: str) -> dict[str, Any]:
        self.urls.append(url)
        return {
            "Results": [
                {
                    "Make": "FORD",
                    "Model": "F-150",
                    "ModelYear": "2011",
                    "DriveType": "4x2",
                }
            ]
        }


class ModelListClient:
    def __init__(self, models: list[str]) -> None:
        self.models = models

    def get_json(self, url: str) -> dict[str, Any]:
        return {"Results": [{"Model": model} for model in self.models]}


def test_key_ready_values_accepts_test_level_consumer_identity() -> None:
    assert rating_match_builder.is_key_ready_values("TOYOTA", "RAV4", 2019)
    assert not rating_match_builder.is_key_ready_values("NHTSA", "RESEARCH MDB", 0)
    assert not rating_match_builder.is_key_ready_values("OTHER", "OTHER", 2013)


def test_decode_vin_accepts_valid_vin_with_x_character() -> None:
    client = FakeClient()

    result = rating_match_builder.decode_vin(client, "1FTEX1CMXBFA43718")

    assert result is not None
    assert result["Model"] == "F-150"
    assert client.urls == [
        "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/1FTEX1CMXBFA43718?format=json"
    ]


def test_decode_vin_rejects_masked_placeholder_x_sequences() -> None:
    client = FakeClient()

    assert rating_match_builder.decode_vin(client, "WBAKC6C59CDXXXXX") is None
    assert client.urls == []


def test_model_aliases_cover_official_model_list_variants() -> None:
    assert "SL" in rating_match_builder.model_aliases("SATURN", "SL1")
    assert "F-150" in rating_match_builder.model_aliases("FORD", "F150 PICKUP")
    assert "E-CLASS" in rating_match_builder.model_aliases("MERCEDES", "E350")
    assert "ML-CLASS" in rating_match_builder.model_aliases("MERCEDES", "ML350")
    assert "ED" in rating_match_builder.model_aliases("SMART", "Electric Drive")
    assert rating_match_builder.make_aliases("ALFA ROMEO")[0] == "ALFA"


def test_model_from_title_extracts_ram_quad_cab() -> None:
    assert (
        rating_match_builder.model_from_title(
            "RAM", "NCAP - 2025 RAM 1500 TRADESMAN QUAD CAB TRUCK"
        )
        == "RAM 1500 QUAD CAB"
    )


def test_model_list_candidates_match_make_prefixed_official_models() -> None:
    candidates = rating_match_builder.model_list_candidates(
        ModelListClient(["AUDI Q4 E-TRON", "AUDI Q4 SPORTBACK E-TRON"]),
        2022,
        "AUDI",
        "Q4 e-tron",
    )

    assert ("AUDI", "AUDI Q4 E-TRON", 100) in candidates


def test_model_list_candidates_match_trimmed_model_tokens() -> None:
    candidates = rating_match_builder.model_list_candidates(
        ModelListClient(["CLUBMAN", "CONVERTIBLE", "COUNTRYMAN"]),
        2019,
        "MINI",
        "Cooper Convertible",
    )

    assert candidates == [("MINI", "CONVERTIBLE", 76)]


def test_drive_tokens_treat_4x2_as_non_4wd_variant_evidence() -> None:
    tokens = rating_match_builder.weighted_drive_tokens({"DriveType": "4x2"})

    assert ("4X2", 20) in tokens
    assert ("FWD", 18) in tokens
    assert ("RWD", 18) in tokens


def test_body_tokens_use_vpic_cab_and_powertrain_details() -> None:
    subject = rating_match_builder.SubjectVehicle(
        row_key="1::1",
        test_no=1,
        test_type="NEW CAR ASSESSMENT TEST",
        test_configuration_key="VTB",
        test_title="",
        source_vehicle_no=1,
        make="FORD",
        model="F150",
        model_year=2021,
        body_type="PICKUP TRUCK",
        body_style="PICKUP TRUCK",
        vin="1FTEX1CB1MFA00000",
        curb_weight=None,
        vehicle_test_weight=None,
        wheelbase=None,
        vehicle_length=None,
        vehicle_width=None,
        transmission_type=None,
    )

    tokens = rating_match_builder.weighted_body_tokens(
        subject,
        {
            "BodyClass": "Pickup",
            "BodyCabType": "Extra/Super/Quad/Double/King/Extended",
            "Series2": "Extra Cab",
            "Trim2": "",
            "Doors": "4",
            "ElectrificationLevel": "BEV (Battery Electric Vehicle)",
            "FuelTypePrimary": "Electric",
        },
    )

    assert ("PU/EC", 14) in tokens
    assert ("EXTENDED", 18) in tokens
    assert ("ELECTRIC", 16) in tokens


def test_confidence_promotes_all_identical_candidate_ratings() -> None:
    detail = {"OverallRating": "5", "OverallFrontCrashRating": "4"}
    candidates = [
        {"score": 1, "detail": detail},
        {"score": 1, "detail": dict(detail)},
    ]

    assert (
        rating_match_builder.confidence_with_rating_equivalence(
            candidates, "REVIEW_AMBIGUOUS_VARIANT"
        )
        == "HIGH_EQUIVALENT_RATING"
    )


def test_confidence_promotes_identical_top_rating_group_only() -> None:
    candidates = [
        {"score": 40, "detail": {"OverallRating": "5"}},
        {"score": 40, "detail": {"OverallRating": "5"}},
        {"score": 20, "detail": {"OverallRating": "4"}},
    ]

    assert (
        rating_match_builder.confidence_with_rating_equivalence(
            candidates, "REVIEW_AMBIGUOUS_VARIANT"
        )
        == "HIGH_TOP_EQUIVALENT_RATING"
    )


def test_safercar_rollover_index_sniffs_delimiter_and_preserves_official_fields(
    tmp_path: Path,
) -> None:
    safercar_csv = tmp_path / "Safercar_data.csv"
    safercar_csv.write_text(
        "MODEL_YR,MAKE,MODEL,STATIC_STABI_FACTOR,TIP,ROLLOVER_POSSIBILITY,"
        "ROLLOVER_STARS,ROLL_SAFETY_CONCERN,ROLL_FOOT_NOTES\n"
        "2019,TOYOTA,RAV4,1.27,No Tip,0.155,4,None,fixture note\n",
        encoding="utf-8",
    )
    subject = rating_match_builder.SubjectVehicle(
        row_key="9100::1",
        test_no=9100,
        test_type="NEW CAR ASSESSMENT TEST",
        test_configuration_key="ROL",
        test_title="",
        source_vehicle_no=1,
        make="Toyota",
        model="RAV4",
        model_year=2019,
        body_type="SUV",
        body_style="SUV",
        vin=None,
        curb_weight=None,
        vehicle_test_weight=None,
        wheelbase=None,
        vehicle_length=None,
        vehicle_width=None,
        transmission_type=None,
    )

    index = rating_match_builder.load_safercar_rollover_index(safercar_csv)
    fields = index.lookup(
        subject,
        rating_vehicle_id=14082,
        rating_vehicle_description="2019 Toyota RAV4 SUV AWD",
    )

    assert fields == {
        "STATIC_STABI_FACTOR": "1.27",
        "TIP": "No Tip",
        "ROLLOVER_POSSIBILITY": "0.155",
        "ROLLOVER_STARS": "4",
        "ROLL_SAFETY_CONCERN": "None",
        "ROLL_FOOT_NOTES": "fixture note",
        "safercar_source_file": str(safercar_csv),
        "safercar_source_sha256": rating_match_builder.sha256_file(safercar_csv),
        "safercar_source_row_index": "1",
    }


def test_safercar_rollover_index_prefers_drive_train_variant_from_rating_description(
    tmp_path: Path,
) -> None:
    safercar_csv = tmp_path / "Safercar_data.csv"
    safercar_csv.write_text(
        "MODEL_YR,MAKE,MODEL,DRIVE_TRAIN,STATIC_STABI_FACTOR,TIP,"
        "ROLLOVER_POSSIBILITY,ROLLOVER_STARS,ROLL_SAFETY_CONCERN,ROLL_FOOT_NOTES\n"
        "2019,TOYOTA,RAV4,FWD,1.19,No Tip,0.170,4,,fwd note\n"
        "2019,TOYOTA,RAV4,AWD,1.27,No Tip,0.155,4,,awd note\n",
        encoding="utf-8",
    )
    subject = rating_match_builder.SubjectVehicle(
        row_key="9100::1",
        test_no=9100,
        test_type="NEW CAR ASSESSMENT TEST",
        test_configuration_key="ROL",
        test_title="",
        source_vehicle_no=1,
        make="Toyota",
        model="RAV4",
        model_year=2019,
        body_type="SUV",
        body_style="SUV",
        vin=None,
        curb_weight=None,
        vehicle_test_weight=None,
        wheelbase=None,
        vehicle_length=None,
        vehicle_width=None,
        transmission_type=None,
    )

    index = rating_match_builder.load_safercar_rollover_index(safercar_csv)
    fields = index.lookup(
        subject,
        rating_vehicle_id=14082,
        rating_vehicle_description="2019 Toyota RAV4 SUV AWD",
    )

    assert fields["STATIC_STABI_FACTOR"] == "1.27"
    assert fields["ROLLOVER_POSSIBILITY"] == "0.155"
    assert fields["ROLL_FOOT_NOTES"] == "awd note"


def test_safercar_rollover_index_prefers_production_release_from_rating_description(
    tmp_path: Path,
) -> None:
    safercar_csv = tmp_path / "Safercar_data.csv"
    safercar_csv.write_text(
        "MODEL_YR,MAKE,MODEL,DRIVE_TRAIN,PRODUCTION_RELEASE,STATIC_STABI_FACTOR,TIP,"
        "ROLLOVER_POSSIBILITY,ROLLOVER_STARS,ROLL_SAFETY_CONCERN,ROLL_FOOT_NOTES\n"
        "2011,HYUNDAI,SONATA,FWD,1,1.43,No Tip,0.100,5,,early note\n"
        "2011,HYUNDAI,SONATA,FWD,2,1.31,No Tip,0.130,4,,later note\n",
        encoding="utf-8",
    )
    subject = rating_match_builder.SubjectVehicle(
        row_key="7203::1",
        test_no=7203,
        test_type="NEW CAR ASSESSMENT TEST",
        test_configuration_key="",
        test_title="",
        source_vehicle_no=1,
        make="Hyundai",
        model="Sonata",
        model_year=2011,
        body_type="4 DR",
        body_style="4 DR",
        vin=None,
        curb_weight=None,
        vehicle_test_weight=None,
        wheelbase=None,
        vehicle_length=None,
        vehicle_width=None,
        transmission_type=None,
    )

    index = rating_match_builder.load_safercar_rollover_index(safercar_csv)
    fields = index.lookup(
        subject,
        rating_vehicle_id=111,
        rating_vehicle_description="2011 Hyundai Sonata 4 DR FWD Later Release",
    )

    assert fields["STATIC_STABI_FACTOR"] == "1.31"
    assert fields["ROLLOVER_POSSIBILITY"] == "0.130"
    assert fields["ROLL_FOOT_NOTES"] == "later note"


def test_safercar_rollover_index_repairs_shifted_rollover_columns(tmp_path: Path) -> None:
    safercar_csv = tmp_path / "Safercar_data.csv"
    safercar_csv.write_text(
        "MODEL_YR,MAKE,MODEL,DRIVE_TRAIN,BODY_STYLE,PRODUCTION_RELEASE,"
        "STATIC_STABI_FACTOR,TIP,ROLLOVER_POSSIBILITY,ROLLOVER_STARS,"
        "ROLL_SAFETY_CONCERN,ROLL_FOOT_NOTES\n"
        "2016,FORD,F-150,4x2,PU/CC,1,0.191,1.19,2058.73600,4,No Tip,\n",
        encoding="utf-8",
    )
    subject = rating_match_builder.SubjectVehicle(
        row_key="9571::1",
        test_no=9571,
        test_type="NEW CAR ASSESSMENT TEST",
        test_configuration_key="",
        test_title="",
        source_vehicle_no=1,
        make="Ford",
        model="F-150",
        model_year=2016,
        body_type="PU/CC",
        body_style="PU/CC",
        vin=None,
        curb_weight=None,
        vehicle_test_weight=None,
        wheelbase=None,
        vehicle_length=None,
        vehicle_width=None,
        transmission_type=None,
    )

    index = rating_match_builder.load_safercar_rollover_index(safercar_csv)
    fields = index.lookup(
        subject,
        rating_vehicle_id=10239,
        rating_vehicle_description="2016 Ford F-150 Super Crew PU/CC 4x2",
    )

    assert fields["STATIC_STABI_FACTOR"] == "1.19"
    assert fields["ROLLOVER_POSSIBILITY"] == "0.191"
    assert fields["TIP"] == "No Tip"
    assert fields["ROLL_SAFETY_CONCERN"] == ""
