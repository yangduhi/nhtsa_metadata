import csv
import sqlite3
from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from nhtsa_metadata.cli import app
from nhtsa_metadata.services.discovery_authority import (
    build_authoritative_manifest,
    load_reference_seeds,
    stable_row_hash,
    validate_reference_discovery,
)
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult, SourceRequest


class FakeLiveDiscoveryClient:
    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        test_no = int(path_and_query["test_no"])
        if test_no == 7202:
            rows = [
                {
                    "testNo": 7202,
                    "testDate": "2011-01-04",
                    "testConfiguration": "VEHICLE INTO POLE",
                    "testType": "NEW CAR ASSESSMENT TEST",
                    "modelYear": 2011,
                    "vehicleMake": "A",
                    "vehicleModel": "B",
                }
            ]
        elif test_no == 7203:
            rows = [
                {
                    "testNo": 7203,
                    "testDate": "2011-01-06",
                    "testConfiguration": "VEHICLE INTO BARRIER",
                }
            ]
        elif test_no == 7204:
            rows = [{"testNo": 7204}]
        else:
            rows = []
        return SourceFetchResult(
            request=SourceRequest(endpoint_name=endpoint_name, url=f"fake://{endpoint_name}"),
            payload={"results": rows},
            http_status=200,
        )


def test_reference_db_seed_filters_scope_and_is_not_canonical(tmp_path: Path) -> None:
    database = _reference_db(tmp_path)

    seeds = load_reference_seeds(database, date(2011, 1, 1))

    assert sorted(seeds) == [7202, 7203, 7204, 7205]
    assert seeds[7202].test_configuration == "VEHICLE INTO BARRIER"


def test_reference_only_requires_live_validation_for_authoritative_manifest(
    tmp_path: Path,
) -> None:
    database = _reference_db(tmp_path)
    live_manifest = _live_manifest(tmp_path / "live.csv")
    validation = validate_reference_discovery(
        client=FakeLiveDiscoveryClient(),
        reference_database=database,
        live_manifest=live_manifest,
        min_test_date=date(2011, 1, 1),
        validation_endpoints=["test_summary"],
    )
    authoritative = tmp_path / "authoritative.csv"
    meta = tmp_path / "authoritative.meta.json"

    build_authoritative_manifest(
        live_manifest=live_manifest,
        reference_database=database,
        validation_payload=validation,
        output=authoritative,
        meta_output=meta,
        min_test_date=date(2011, 1, 1),
    )

    with authoritative.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    test_numbers = {int(row["test_no"]) for row in rows}
    assert 7202 in test_numbers
    assert 7203 not in test_numbers
    assert 7204 not in test_numbers
    assert all(row["authority_status"] == "authoritative_included" for row in rows)
    assert all(row["row_hash"] for row in rows)


def test_live_value_takes_precedence_and_row_hash_is_deterministic(tmp_path: Path) -> None:
    database = _reference_db(tmp_path)
    live_manifest = _live_manifest(tmp_path / "live.csv")

    validation = validate_reference_discovery(
        client=FakeLiveDiscoveryClient(),
        reference_database=database,
        live_manifest=live_manifest,
        min_test_date=date(2011, 1, 1),
        validation_endpoints=["test_summary"],
    )
    row = next(item for item in validation["rows"] if item["test_no"] == 7202)

    assert row["test_configuration"] == "VEHICLE INTO POLE"
    assert row["validation_status"] == "validated_live_with_metadata_drift"
    assert stable_row_hash({"test_no": 1, "test_date": "2011-01-01"}) == stable_row_hash(
        {"test_date": "2011-01-01", "test_no": 1}
    )


def test_reference_discovery_cli_requires_live_safety_gate(tmp_path: Path) -> None:
    output = tmp_path / "should_not_exist.json"
    result = CliRunner().invoke(
        app,
        [
            "catalog",
            "validate-reference-discovery",
            "--source",
            "live",
            "--reference-database",
            str(tmp_path / "missing.sqlite"),
            "--live-manifest",
            str(tmp_path / "missing.csv"),
            "--output",
            str(output),
            "--validated-manifest-output",
            str(tmp_path / "validated.csv"),
            "--markdown-output",
            str(tmp_path / "report.md"),
        ],
    )

    assert result.exit_code != 0
    assert not output.exists()


def _reference_db(tmp_path: Path) -> Path:
    database = tmp_path / "reference.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE crash_tests (
                test_no INTEGER PRIMARY KEY,
                test_date TEXT,
                crash_type TEXT,
                make TEXT,
                model TEXT,
                year INTEGER
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO crash_tests
            (test_no, test_date, crash_type, make, model, year)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (7100, "2010-12-31", "VEHICLE INTO BARRIER", "A", "B", 2010),
                (7202, "2011-01-04", "VEHICLE INTO BARRIER", "A", "B", 2011),
                (7203, "2011-01-05", "VEHICLE INTO BARRIER", "A", "B", 2011),
                (7204, "2011-01-06", "VEHICLE INTO BARRIER", "A", "B", 2011),
                (7205, "2011-01-07", "VEHICLE INTO BARRIER", "A", "B", 2011),
            ],
        )
    return database


def _live_manifest(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "test_no,test_date,test_year,test_configuration_key,test_configuration,"
                "test_type,model_year,vehicle_make,vehicle_model,reason,scope_status,"
                "selection_priority,balance_status",
                "7201,2011-01-03,2011,VTB,VEHICLE INTO BARRIER,"
                "NEW CAR ASSESSMENT TEST,2011,A,B,live,in_scope,1,full_scope",
                "7205,2011-01-07,2011,VTB,VEHICLE INTO BARRIER,"
                "NEW CAR ASSESSMENT TEST,2011,A,B,live,in_scope,2,full_scope",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path
