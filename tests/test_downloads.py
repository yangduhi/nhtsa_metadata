from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from nhtsa_metadata.config import Settings
from nhtsa_metadata.db.models import CrashTest, MediaAsset
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.downloads import (
    DownloadFetchResult,
    enqueue_download,
    list_download_jobs,
    list_downloadable_assets,
    run_download_job,
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
            canonical_url_hash="hash-report-pdf",
            file_ext="pdf",
            suggested_filename="../unsafe report.pdf",
            content_type="application/pdf",
            size_bytes=3,
        )
        session.add(asset)
        session.commit()
        return asset.id


def test_list_downloadable_assets_uses_media_asset_registry(tmp_settings: Settings) -> None:
    asset_id = _seed_asset(tmp_settings)
    session_factory = create_session_factory(tmp_settings)

    with session_factory() as session:
        assets = list_downloadable_assets(session, test_no=10001)

    assert len(assets) == 1
    assert assets[0]["id"] == asset_id
    assert assets[0]["test_no"] == 10001
    assert assets[0]["asset_kind"] == "document"
    assert assets[0]["source_url"] == "https://example.test/nhtsa/report.pdf"


def test_enqueue_download_creates_queued_job_with_sanitized_destination(
    tmp_settings: Settings, tmp_path: Path
) -> None:
    asset_id = _seed_asset(tmp_settings)
    session_factory = create_session_factory(tmp_settings)

    with session_factory() as session:
        job = enqueue_download(session, asset_id, tmp_path / "downloads")
        session.commit()

    assert job["status"] == "queued"
    assert job["media_asset_id"] == asset_id
    assert job["filename"] == "unsafe_report.pdf"
    assert Path(job["destination_path"]).parent == tmp_path / "downloads"

    with session_factory() as session:
        jobs = list_download_jobs(session)
    assert jobs[0]["status"] == "queued"


def test_run_download_job_writes_file_using_registered_asset_url(
    tmp_settings: Settings, tmp_path: Path
) -> None:
    asset_id = _seed_asset(tmp_settings)
    session_factory = create_session_factory(tmp_settings)
    seen_urls: list[str] = []

    def fake_fetch(url: str) -> DownloadFetchResult:
        seen_urls.append(url)
        return DownloadFetchResult(content=b"pdf", content_type="application/pdf")

    with session_factory() as session:
        job = enqueue_download(session, asset_id, tmp_path / "downloads")
        session.commit()
        completed = run_download_job(session, int(job["id"]), fetcher=fake_fetch)
        session.commit()

    assert seen_urls == ["https://example.test/nhtsa/report.pdf"]
    assert completed["status"] == "completed"
    assert completed["size_bytes"] == 3
    assert Path(completed["destination_path"]).read_bytes() == b"pdf"


def test_enqueue_download_rejects_unknown_asset(tmp_settings: Settings, tmp_path: Path) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)

    with session_factory() as session:
        with pytest.raises(ValueError, match="media asset not found"):
            enqueue_download(session, 9999, tmp_path / "downloads")
