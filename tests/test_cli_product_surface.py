from typer.testing import CliRunner

from nhtsa_metadata.cli import app


def test_top_level_help_shows_product_surface_and_hides_legacy_aliases() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "catalog" in result.stdout
    assert "db" in result.stdout
    assert "download" in result.stdout
    assert "ops" in result.stdout
    assert "legacy" in result.stdout
    assert "coverage" not in result.stdout
    assert "scale" not in result.stdout
    assert "schema" not in result.stdout


def test_ops_and_legacy_groups_expose_research_commands() -> None:
    runner = CliRunner()

    assert runner.invoke(app, ["ops", "coverage", "--help"]).exit_code == 0
    assert runner.invoke(app, ["ops", "scale", "--help"]).exit_code == 0
    assert runner.invoke(app, ["legacy", "schema", "--help"]).exit_code == 0


def test_hidden_legacy_aliases_remain_backward_compatible() -> None:
    runner = CliRunner()

    assert runner.invoke(app, ["coverage", "--help"]).exit_code == 0
    assert runner.invoke(app, ["scale", "--help"]).exit_code == 0
    assert runner.invoke(app, ["schema", "--help"]).exit_code == 0


def test_catalog_exposes_materialize_filter_db_as_product_build_command() -> None:
    result = CliRunner().invoke(app, ["catalog", "materialize-filter-db", "--help"])

    assert result.exit_code == 0
    assert "--source-db" in result.stdout
    assert "--output-db" in result.stdout
