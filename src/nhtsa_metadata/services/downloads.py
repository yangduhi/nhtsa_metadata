from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import CrashTest, DownloadJob, MediaAsset


@dataclass(frozen=True)
class DownloadFetchResult:
    content: bytes
    content_type: str | None = None


DownloadFetcher = Callable[[str], DownloadFetchResult]


def list_downloadable_assets(
    session: Session,
    *,
    test_no: int | None = None,
    asset_kind: str | None = None,
) -> list[dict[str, object]]:
    """List DB-registered assets that the GUI may offer for controlled download."""
    statement = select(MediaAsset, CrashTest).join(CrashTest, MediaAsset.test_id == CrashTest.id)
    if test_no is not None:
        statement = statement.where(CrashTest.test_no == test_no)
    if asset_kind is not None:
        statement = statement.where(MediaAsset.asset_kind == asset_kind)
    rows = session.execute(statement.order_by(CrashTest.test_no, MediaAsset.id)).all()
    return [_asset_summary(asset, test) for asset, test in rows]


def enqueue_download(
    session: Session,
    media_asset_id: int,
    download_dir: str | Path,
) -> dict[str, object]:
    """Create a queued download job from an existing media asset record."""
    asset = session.get(MediaAsset, media_asset_id)
    if asset is None:
        raise ValueError(f"media asset not found: {media_asset_id}")
    test = session.get(CrashTest, asset.test_id)
    filename = _safe_filename(asset)
    destination_path = Path(download_dir) / filename
    job = DownloadJob(
        media_asset_id=asset.id,
        test_no=test.test_no if test is not None else None,
        status="queued",
        source_url=asset.source_url,
        destination_path=str(destination_path),
        filename=filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
    )
    session.add(job)
    session.flush()
    return _job_summary(job)


def list_download_jobs(
    session: Session,
    *,
    status: str | None = None,
) -> list[dict[str, object]]:
    statement = select(DownloadJob).order_by(DownloadJob.id)
    if status is not None:
        statement = statement.where(DownloadJob.status == status)
    return [_job_summary(job) for job in session.scalars(statement)]


def run_download_job(
    session: Session,
    job_id: int,
    *,
    fetcher: DownloadFetcher | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    """Run a queued DB-registered download job.

    The default path performs a real HTTP(S) download. Tests and default verification inject a fake
    fetcher so they do not perform live downloads.
    """
    job = session.get(DownloadJob, job_id)
    if job is None:
        raise ValueError(f"download job not found: {job_id}")
    destination = Path(job.destination_path)
    job.status = "running"
    job.started_at = datetime.utcnow()
    session.flush()
    try:
        if fetcher is None:
            size_bytes, content_type = _download_url_to_path(
                job.source_url, destination, timeout_seconds=timeout_seconds
            )
        else:
            result = fetcher(job.source_url)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(result.content)
            size_bytes = len(result.content)
            content_type = result.content_type
        job.status = "completed"
        job.content_type = content_type or job.content_type
        job.size_bytes = size_bytes
        job.finished_at = datetime.utcnow()
        job.error_json = None
        session.flush()
        return _job_summary(job)
    except Exception as exc:
        job.status = "failed"
        job.finished_at = datetime.utcnow()
        job.error_json = {"type": exc.__class__.__name__, "message": str(exc)}
        session.flush()
        raise


def _download_url_to_path(
    source_url: str,
    destination: Path,
    *,
    timeout_seconds: float,
) -> tuple[int, str | None]:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only HTTP(S) media asset URLs can be downloaded")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_suffix(destination.suffix + ".part")
    size_bytes = 0
    content_type: str | None = None
    try:
        with httpx.stream(
            "GET",
            source_url,
            follow_redirects=True,
            timeout=timeout_seconds,
        ) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type")
            with temp_path.open("wb") as output:
                for chunk in response.iter_bytes():
                    output.write(chunk)
                    size_bytes += len(chunk)
        temp_path.replace(destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return size_bytes, content_type


def _asset_summary(asset: MediaAsset, test: CrashTest) -> dict[str, object]:
    return {
        "id": asset.id,
        "test_id": asset.test_id,
        "test_no": test.test_no,
        "asset_kind": asset.asset_kind,
        "asset_subtype": asset.asset_subtype,
        "source_url": asset.source_url,
        "suggested_filename": asset.suggested_filename,
        "content_type": asset.content_type,
        "size_bytes": asset.size_bytes,
    }


def _job_summary(job: DownloadJob) -> dict[str, object]:
    return {
        "id": job.id,
        "media_asset_id": job.media_asset_id,
        "test_no": job.test_no,
        "status": job.status,
        "source_url": job.source_url,
        "destination_path": job.destination_path,
        "filename": job.filename,
        "content_type": job.content_type,
        "size_bytes": job.size_bytes,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error": job.error_json,
    }


def _safe_filename(asset: MediaAsset) -> str:
    parsed = urlparse(asset.source_url)
    candidate = asset.suggested_filename or Path(parsed.path).name or f"asset_{asset.id}"
    candidate = Path(candidate).name
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate).strip("._")
    if not candidate:
        candidate = f"asset_{asset.id}"
    if "." not in candidate and asset.file_ext:
        candidate = f"{candidate}.{asset.file_ext.lstrip('.')}"
    return candidate[:180]
