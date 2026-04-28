import csv
from pathlib import Path

from typer.testing import CliRunner

from nhtsa_metadata.cli import app
from nhtsa_metadata.services.manifest_builder import StratifiedManifestBuilder
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult, SourceRequest


class FakeDiscoveryClient:
    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        if endpoint_name == "test_summary":
            test_no = int(path_and_query["test_no"])
            row = {
                "testNo": test_no,
                "testType": "NEW CAR ASSESSMENT TEST",
                "testConfigurationKey": "VTB" if test_no == 10001 else "ITV",
                "testConfiguration": "VEHICLE INTO BARRIER"
                if test_no == 10001
                else "IMPACTOR INTO VEHICLE",
                "impactAngle": 0 if test_no == 10001 else 270,
            }
            return _result(endpoint_name, [row])
        return _result(
            endpoint_name,
            [
                {
                    "testNo": 10001,
                    "testConfigurationKey": "VTB",
                    "testConfiguration": "VEHICLE INTO BARRIER",
                },
                {
                    "testNo": 10003,
                    "testConfigurationKey": "ITV",
                    "testConfiguration": "IMPACTOR INTO VEHICLE",
                },
                {
                    "testNo": 20001,
                    "testConfigurationKey": "VTB",
                    "testConfiguration": "VEHICLE INTO BARRIER",
                },
                {
                    "testNo": 20002,
                    "testConfigurationKey": "ITV",
                    "testConfiguration": "IMPACTOR INTO VEHICLE",
                },
                {
                    "testNo": 20003,
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
    assert report.count == 3
    assert rows[0].keys() == {
        "test_no",
        "note",
        "test_type",
        "test_configuration_key",
        "test_configuration",
        "selection_reason",
    }
    assert {int(row["test_no"]) for row in rows} == {10001, 10003, 20003}
    assert rows[0]["selection_reason"] == "required_baseline_frontal_barrier"
    assert rows[1]["selection_reason"] == "required_baseline_side_impactor"


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
