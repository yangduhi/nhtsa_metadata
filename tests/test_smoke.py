from fastapi.testclient import TestClient

import nhtsa_metadata
from nhtsa_metadata.api.app import create_app
from nhtsa_metadata.cli import app as cli_app
from nhtsa_metadata.config import Settings


def test_package_imports() -> None:
    assert nhtsa_metadata.__version__ == "0.1.0"


def test_create_app(tmp_settings: Settings) -> None:
    app = create_app(tmp_settings)
    assert app.title == "nhtsa_metadata"


def test_health_endpoint(tmp_settings: Settings) -> None:
    client = TestClient(create_app(tmp_settings))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "nhtsa_metadata",
        "environment": "test",
        "database_url_configured": True,
        "min_test_date": "2011-01-01",
    }


def test_cli_app_imports() -> None:
    assert cli_app is not None


def test_default_min_test_date_is_2011() -> None:
    assert Settings().min_test_date.isoformat() == "2011-01-01"


def test_reference_db_path_env_alias(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    expected = r"D:\vscode\pulse_analysis\data\db\nhtsa_data.db"
    monkeypatch.setenv("NHTSA_METADATA_REFERENCE_DB_PATH", expected)
    assert Settings(_env_file=None).reference_database_path == expected
