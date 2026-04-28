from typer.testing import CliRunner

from nhtsa_metadata.cli import app


def test_cli_collect_test_dry_run() -> None:
    result = CliRunner().invoke(
        app,
        ["catalog", "collect-test", "--test-no", "10001", "--dry-run"],
    )
    assert result.exit_code == 0
    assert '"dry_run": true' in result.stdout


def test_cli_live_without_allow_live_fails() -> None:
    result = CliRunner().invoke(
        app,
        ["catalog", "collect-test", "--test-no", "10001", "--source", "live"],
    )
    assert result.exit_code != 0
