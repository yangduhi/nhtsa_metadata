from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from nhtsa_metadata.api.app import create_app
from nhtsa_metadata.config import Settings
from nhtsa_metadata.db.models import CrashTest, MediaAsset
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.downloads import DownloadFetchResult


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'api.sqlite'}",
        environment="test",
        download_dir=str(tmp_path / "downloads"),
    )


def _seed_asset(settings: Settings) -> int:
    ensure_schema(create_engine_for_settings(settings))
    session_factory = create_session_factory(settings)
    with session_factory() as session:
        test = CrashTest(
            test_no=10001,
            test_date=date(2016, 12, 12),
            test_date_parse_status="parsed",
        )
        session.add(test)
        session.flush()
        asset = MediaAsset(
            test_id=test.id,
            asset_kind="document",
            asset_subtype="pdf",
            source_url="https://example.test/nhtsa/report.pdf",
            canonical_url_hash="api-hash-report-pdf",
            file_ext="pdf",
            suggested_filename="report.pdf",
            content_type="application/pdf",
        )
        session.add(asset)
        session.commit()
        return asset.id


def test_download_asset_listing_and_queue_api(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    asset_id = _seed_asset(settings)
    app = create_app(settings)
    client = TestClient(app)

    assets = client.get("/api/download-assets", params={"test_no": 10001})
    assert assets.status_code == 200
    assert assets.json()["items"][0]["id"] == asset_id

    created = client.post("/api/download-jobs", json={"media_asset_id": asset_id})
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "queued"
    assert body["media_asset_id"] == asset_id

    jobs = client.get("/api/download-jobs")
    assert jobs.status_code == 200
    assert jobs.json()["count"] == 1


def test_download_job_run_api_uses_injected_fetcher(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    asset_id = _seed_asset(settings)
    app = create_app(settings)
    seen_urls: list[str] = []

    def fake_fetch(url: str) -> DownloadFetchResult:
        seen_urls.append(url)
        return DownloadFetchResult(content=b"pdf", content_type="application/pdf")

    app.state.download_fetcher = fake_fetch
    client = TestClient(app)
    created = client.post("/api/download-jobs", json={"media_asset_id": asset_id}).json()

    completed = client.post(f"/api/download-jobs/{created['id']}/run")

    assert completed.status_code == 200
    body = completed.json()
    assert seen_urls == ["https://example.test/nhtsa/report.pdf"]
    assert body["status"] == "completed"
    assert Path(body["destination_path"]).read_bytes() == b"pdf"
