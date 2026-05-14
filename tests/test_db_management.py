from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from nhtsa_metadata.cli import app
from nhtsa_metadata.config import Settings
from nhtsa_metadata.db.models import CrashTest
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.db_management import backup_database, inspect_database, vacuum_database


def _seed_database(settings: Settings) -> None:
    ensure_schema(create_engine_for_settings(settings))
    session_factory = create_session_factory(settings)
    with session_factory() as session:
        session.add(CrashTest(test_no=12345, test_date_parse_status="missing"))
        session.commit()


def test_inspect_database_reports_sqlite_path_and_table_counts(tmp_settings: Settings) -> None:
    _seed_database(tmp_settings)

    report = inspect_database(tmp_settings.database_url)

    assert report["status"] == "ok"
    assert report["dialect"] == "sqlite"
    assert report["exists"] is True
    assert report["table_count"] > 0
    assert report["tables"]["tests"] == 1
    assert report["size_bytes"] > 0
    assert "test.sqlite" in str(report["sqlite_path"])


def test_backup_database_copies_sqlite_file(tmp_settings: Settings, tmp_path: Path) -> None:
    _seed_database(tmp_settings)
    backup_path = tmp_path / "backup.sqlite"

    result = backup_database(tmp_settings.database_url, backup_path)

    assert result["status"] == "ok"
    assert result["backup_path"] == str(backup_path)
    assert backup_path.exists()
    with sqlite3.connect(backup_path) as connection:
        assert connection.execute("select count(*) from tests").fetchone()[0] == 1


def test_vacuum_database_returns_maintenance_report(tmp_settings: Settings) -> None:
    _seed_database(tmp_settings)

    result = vacuum_database(tmp_settings.database_url, analyze=True)

    assert result["status"] == "ok"
    assert result["vacuumed"] is True
    assert result["analyzed"] is True
    assert result["size_after_bytes"] > 0


def test_db_cli_status_backup_and_vacuum(tmp_settings: Settings, tmp_path: Path) -> None:
    _seed_database(tmp_settings)
    runner = CliRunner()

    status = runner.invoke(app, ["db", "status", "--database-url", tmp_settings.database_url])
    assert status.exit_code == 0
    assert json.loads(status.stdout)["tables"]["tests"] == 1

    backup_path = tmp_path / "cli-backup.sqlite"
    backup = runner.invoke(
        app,
        [
            "db",
            "backup",
            "--database-url",
            tmp_settings.database_url,
            "--output",
            str(backup_path),
        ],
    )
    assert backup.exit_code == 0
    assert backup_path.exists()

    vacuum = runner.invoke(app, ["db", "vacuum", "--database-url", tmp_settings.database_url])
    assert vacuum.exit_code == 0
    assert json.loads(vacuum.stdout)["vacuumed"] is True
