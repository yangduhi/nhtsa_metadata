import csv
import sqlite3
from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from nhtsa_metadata.cli import app
from nhtsa_metadata.services.manifest_builder import (
    StratifiedManifestBuilder,
    load_reference_manifest_candidates,
)
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult, SourceRequest


class FakeDiscoveryClient:
    def __init__(self) -> None:
        self.discovery_calls: list[dict[str, object]] = []

    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        if endpoint_name == "test_summary":
            test_no = int(path_and_query["test_no"])
            if test_no == 7201:
                row = {
                    "testNo": 7201,
                    "testType": "NEW CAR ASSESSMENT TEST",
                    "testDate": "2011-01-03",
                    "testConfigurationKey": "VTB",
                    "testConfiguration": "VEHICLE INTO BARRIER",
                    "modelYear": 2011,
                    "vehicleMake": "KIA",
                    "vehicleModel": "FORTE",
                }
                return _result(endpoint_name, [row])
            row = {
                "testNo": test_no,
                "testType": "NEW CAR ASSESSMENT TEST",
                "testDate": "2016-12-12" if test_no == 10001 else "2016-12-14",
                "testConfigurationKey": "VTB" if test_no == 10001 else "ITV",
                "testConfiguration": "VEHICLE INTO BARRIER"
                if test_no == 10001
                else "IMPACTOR INTO VEHICLE",
                "impactAngle": 0 if test_no == 10001 else 270,
            }
            return _result(endpoint_name, [row])
        self.discovery_calls.append(path_and_query)
        return _result(
            endpoint_name,
            [
                {
                    "testNo": 10001,
                    "testDate": "2016-12-12",
                    "testConfigurationKey": "VTB",
                    "testConfiguration": "VEHICLE INTO BARRIER",
                },
                {
                    "testNo": 10003,
                    "testDate": "2016-12-14",
                    "testConfigurationKey": "ITV",
                    "testConfiguration": "IMPACTOR INTO VEHICLE",
                },
                {
                    "testNo": 20001,
                    "testDate": "2010-12-31",
                    "testConfigurationKey": "VTB",
                    "testConfiguration": "VEHICLE INTO BARRIER",
                },
                {
                    "testNo": 20002,
                    "testDate": "2015-01-01",
                    "testConfigurationKey": "ITV",
                    "testConfiguration": "IMPACTOR INTO VEHICLE",
                },
                {
                    "testNo": 20003,
                    "testDate": "2018-01-01",
                    "testConfigurationKey": "ANGLED",
                    "testConfiguration": "ANGLED IMPACT",
                },
            ],
        )


def test_stratified_manifest_builder_writes_required_columns(tmp_path: Path) -> None:
    output = tmp_path / "pilot_manifest.csv"
    report = StratifiedManifestBuilder(FakeDiscoveryClient()).build(
        output=output,
        limit=4,
        max_per_configuration=1,
        max_discovery_pages=1,
        discovery_page_size=10,
    )
    with output.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert report.count == 4
    assert rows[0].keys() == {
        "test_no",
        "test_date",
        "test_year",
        "test_configuration_key",
        "test_configuration",
        "test_type",
        "model_year",
        "vehicle_make",
        "vehicle_model",
        "reason",
        "scope_status",
        "selection_priority",
        "balance_status",
    }
    assert {int(row["test_no"]) for row in rows} == {7201, 10001, 10003, 20003}
    assert all(row["test_date"] >= "2011-01-01" for row in rows)
    assert all(row["scope_status"] == "in_scope" for row in rows)
    assert rows[0]["reason"] == "required_anchor_2011_start"
    assert rows[1]["reason"] == "required_baseline_frontal_barrier"
    assert rows[2]["reason"] == "required_baseline_side_impactor"


def test_stratified_manifest_builder_sends_test_date_from(tmp_path: Path) -> None:
    client = FakeDiscoveryClient()
    output = tmp_path / "pilot_manifest.csv"
    StratifiedManifestBuilder(client).build(
        output=output,
        limit=4,
        max_per_configuration=1,
        max_discovery_pages=1,
        discovery_page_size=10,
    )
    assert client.discovery_calls[0]["testDateFrom"] == "2011-01-01"


def test_reference_database_seed_filters_2011_plus_scope(tmp_path: Path) -> None:
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
                (7199, "2010-12-17 00:00:00", "IMPACTOR INTO VEHICLE", "A", "B", 2010),
                (7200, "2010-12-20 00:00:00", "VEHICLE INTO BARRIER", "A", "B", 2010),
                (7201, "2011-01-03 00:00:00", "VEHICLE INTO BARRIER", "A", "B", 2011),
                (7202, "2011-01-04 00:00:00", "VEHICLE INTO POLE", "A", "B", 2011),
                (7203, None, "VEHICLE INTO BARRIER", "A", "B", 2011),
            ],
        )

    candidates = load_reference_manifest_candidates(database, min_test_date=date(2011, 1, 1))

    assert [candidate.test_no for candidate in candidates] == [7201, 7202]


def test_stratified_manifest_builder_uses_reference_database_seed(tmp_path: Path) -> None:
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
                (7201, "2011-01-03 00:00:00", "VEHICLE INTO BARRIER", "A", "B", 2011),
                (7202, "2011-01-04 00:00:00", "VEHICLE INTO POLE", "A", "B", 2011),
                (7203, "2011-01-05 00:00:00", "VEHICLE INTO BARRIER", "A", "B", 2011),
            ],
        )

    output = tmp_path / "pilot_manifest.csv"
    report = StratifiedManifestBuilder(FakeDiscoveryClient()).build(
        output=output,
        limit=6,
        max_per_configuration=2,
        max_discovery_pages=1,
        discovery_page_size=10,
        reference_database=database,
    )
    with output.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert report.reference_database == str(database)
    assert {int(row["test_no"]) for row in rows} == {10001, 10003, 20002, 20003, 7201, 7202}


def test_type_year_manifest_builder_sends_test_date_to_and_uses_global_search(
    tmp_path: Path,
) -> None:
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
                (7201, "2011-01-03 00:00:00", "VEHICLE INTO BARRIER", "KIA", "FORTE", 2011),
                (
                    10001,
                    "2016-12-12 00:00:00",
                    "VEHICLE INTO BARRIER",
                    "CADILLAC",
                    "ESCALADE",
                    2017,
                ),
                (10003, "2016-12-14 00:00:00", "IMPACTOR INTO VEHICLE", "NHTSA", "IMPACTOR", 0),
            ],
        )
    client = FakeDiscoveryClient()
    output = tmp_path / "pilot_manifest.csv"

    report = StratifiedManifestBuilder(client).build(
        output=output,
        limit=4,
        max_discovery_pages=1,
        discovery_page_size=10,
        reference_database=database,
        year_from=2011,
        year_to=2026,
        balance_strategy="type-year",
        balance_priority="type-first",
        relax_balance=True,
    )

    assert report.balance_strategy == "type-year"
    assert any(call.get("testDateTo") == "2026-12-31" for call in client.discovery_calls)
    assert all("testConfiguration" not in call for call in client.discovery_calls)
    with output.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 4
    assert rows[0]["balance_status"].startswith("relaxed")


def test_cli_build_manifest_requires_allow_live(tmp_path: Path) -> None:
    output = tmp_path / "pilot_manifest.csv"
    result = CliRunner().invoke(
        app,
        ["catalog", "build-manifest", "--source", "live", "--output", str(output)],
    )
    assert result.exit_code != 0
    assert not output.exists()


def test_cli_build_manifest_requires_settings_live_opt_in(tmp_path: Path) -> None:
    output = tmp_path / "pilot_manifest.csv"
    result = CliRunner().invoke(
        app,
        [
            "catalog",
            "build-manifest",
            "--source",
            "live",
            "--allow-live",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0
    assert not output.exists()


def _result(endpoint_name: str, rows: list[dict[str, object]]) -> SourceFetchResult:
    return SourceFetchResult(
        request=SourceRequest(endpoint_name=endpoint_name, url=f"fixture://{endpoint_name}"),
        payload={
            "meta": {
                "pagination": {
                    "pageNumber": 0,
                    "count": len(rows),
                    "total": len(rows),
                    "nextUrl": None,
                }
            },
            "results": rows,
        },
        http_status=200,
    )
