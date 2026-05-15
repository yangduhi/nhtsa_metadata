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


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'gui.sqlite'}",
        environment="test",
        download_dir=str(tmp_path / "downloads"),
    )


def _seed_gui_assets(settings: Settings) -> tuple[int, int]:
    ensure_schema(create_engine_for_settings(settings))
    session_factory = create_session_factory(settings)
    with session_factory() as session:
        test = CrashTest(
            test_no=20001,
            test_date=date(2020, 6, 1),
            test_date_parse_status="parsed",
            test_type="frontal",
        )
        session.add(test)
        session.flush()
        report = MediaAsset(
            test_id=test.id,
            asset_kind="report",
            asset_subtype="pdf",
            source_url="https://example.test/nhtsa/report-20001.pdf",
            canonical_url_hash="gui-report-20001",
            file_ext="pdf",
            suggested_filename="frontal_report_20001.pdf",
            content_type="application/pdf",
        )
        video = MediaAsset(
            test_id=test.id,
            asset_kind="video",
            asset_subtype="mp4",
            source_url="https://example.test/nhtsa/video-20001.mp4",
            canonical_url_hash="gui-video-20001",
            file_ext="mp4",
            suggested_filename="impact_video_20001.mp4",
            content_type="video/mp4",
        )
        session.add_all([report, video])
        session.commit()
        return report.id, video.id


def test_gui_shell_and_static_assets_are_served(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)
    client = TestClient(app)

    shell = client.get("/")

    assert shell.status_code == 200
    assert "NHTSA Crash Test Asset Console" in shell.text
    assert "assetConsoleApp" in shell.text
    assert "/static/gui.css" in shell.text
    assert "/static/gui.js" in shell.text
    assert "rel=\"icon\"" in shell.text
    assert "data:image/svg+xml" in shell.text

    script = client.get("/static/gui.js")
    assert script.status_code == 200
    assert "fetchJson('/api/download-assets" in script.text
    assert "createDownloadJob" in script.text
    assert "queued_job_id" in script.text
    assert "Queued #" in script.text


def test_download_assets_api_supports_gui_pagination_and_search(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    report_id, video_id = _seed_gui_assets(settings)
    client = TestClient(create_app(settings))

    first_page = client.get("/api/download-assets", params={"limit": 1, "offset": 0})
    assert first_page.status_code == 200
    assert first_page.json()["count"] == 1
    assert first_page.json()["total"] == 2

    second_page = client.get("/api/download-assets", params={"limit": 1, "offset": 1})
    assert second_page.status_code == 200
    assert second_page.json()["items"][0]["id"] == video_id

    searched = client.get("/api/download-assets", params={"q": "frontal_report"})
    assert searched.status_code == 200
    assert searched.json()["count"] == 1
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["id"] == report_id

    videos = client.get("/api/download-assets", params={"asset_kind": "video"})
    assert videos.status_code == 200
    assert videos.json()["count"] == 1
    assert videos.json()["items"][0]["id"] == video_id
