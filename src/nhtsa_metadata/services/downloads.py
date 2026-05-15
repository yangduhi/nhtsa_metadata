from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.orm import Session

from nhtsa_metadata.constants import DEFAULT_MAX_DOWNLOAD_BYTES
from nhtsa_metadata.db.models import CrashTest, DownloadJob, MediaAsset

ACTIVE_JOB_STATUSES = ("queued", "running")


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
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    """List DB-registered assets that the GUI may offer for controlled download."""
    items, _total = list_downloadable_asset_page(
        session,
        test_no=test_no,
        asset_kind=asset_kind,
        q=q,
        limit=limit,
        offset=offset,
    )
    return items


def list_downloadable_asset_page(
    session: Session,
    *,
    test_no: int | None = None,
    asset_kind: str | None = None,
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    """Return a bounded page plus the filtered total for the GUI asset browser."""
    statement = _downloadable_asset_statement(test_no=test_no, asset_kind=asset_kind, q=q)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    statement = statement.order_by(CrashTest.test_no, MediaAsset.id)
    if offset > 0:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    rows = session.execute(statement).all()
    active_jobs = _active_jobs_by_asset_id(session, [asset.id for asset, _test in rows])
    return [_asset_summary(asset, test, active_jobs.get(asset.id)) for asset, test in rows], total


def _downloadable_asset_statement(
    *,
    test_no: int | None,
    asset_kind: str | None,
    q: str | None,
) -> Select[tuple[MediaAsset, CrashTest]]:
    statement = select(MediaAsset, CrashTest).join(CrashTest, MediaAsset.test_id == CrashTest.id)
    if test_no is not None:
        statement = statement.where(CrashTest.test_no == test_no)
    if asset_kind is not None:
        statement = statement.where(MediaAsset.asset_kind == asset_kind)
    query = q.strip() if q is not None else ""
    if query:
        pattern = f"%{query}%"
        statement = statement.where(
            or_(
                MediaAsset.suggested_filename.ilike(pattern),
                MediaAsset.source_url.ilike(pattern),
                MediaAsset.asset_kind.ilike(pattern),
                MediaAsset.asset_subtype.ilike(pattern),
                cast(CrashTest.test_no, String).like(pattern),
            )
        )
    return statement


def enqueue_download(
    session: Session,
    media_asset_id: int,
    download_dir: str | Path,
) -> dict[str, object]:
    """Create a queued download job from an existing media asset record."""
    asset = session.get(MediaAsset, media_asset_id)
    if asset is None:
        raise ValueError(f"media asset not found: {media_asset_id}")
    existing_job = session.scalar(
        select(DownloadJob)
        .where(
            DownloadJob.media_asset_id == media_asset_id,
            DownloadJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(DownloadJob.id)
    )
    if existing_job is not None:
        return _job_summary(existing_job, already_queued=True)
    test = session.get(CrashTest, asset.test_id)
    filename = _safe_filename(asset)
    destination_path = _destination_path(download_dir, filename)
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


def _active_jobs_by_asset_id(
    session: Session,
    asset_ids: list[int],
) -> dict[int, DownloadJob]:
    if not asset_ids:
        return {}
    jobs = session.scalars(
        select(DownloadJob)
        .where(
            DownloadJob.media_asset_id.in_(asset_ids),
            DownloadJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(DownloadJob.id)
    )
    active_jobs: dict[int, DownloadJob] = {}
    for job in jobs:
        active_jobs.setdefault(job.media_asset_id, job)
    return active_jobs


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
    max_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
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
                job.source_url,
                destination,
                timeout_seconds=timeout_seconds,
                max_bytes=max_bytes,
            )
        else:
            result = fetcher(job.source_url)
            size_bytes = _write_download_content(destination, result.content, max_bytes=max_bytes)
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
        session.commit()
        raise


def _download_url_to_path(
    source_url: str,
    destination: Path,
    *,
    timeout_seconds: float,
    max_bytes: int,
) -> tuple[int, str | None]:
    _validate_max_bytes(max_bytes)
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
            content_length = _content_length(response.headers.get("content-length"))
            if content_length is not None and content_length > max_bytes:
                raise ValueError(_max_download_size_message(content_length, max_bytes))
            with temp_path.open("wb") as output:
                for chunk in response.iter_bytes():
                    if not chunk:
                        continue
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        raise ValueError(_max_download_size_message(size_bytes, max_bytes))
                    output.write(chunk)
        temp_path.replace(destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return size_bytes, content_type


def _write_download_content(destination: Path, content: bytes, *, max_bytes: int) -> int:
    _validate_max_bytes(max_bytes)
    size_bytes = len(content)
    if size_bytes > max_bytes:
        raise ValueError(_max_download_size_message(size_bytes, max_bytes))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return size_bytes


def _destination_path(download_dir: str | Path, filename: str) -> Path:
    root = Path(download_dir).expanduser().resolve(strict=False)
    destination = (root / filename).resolve(strict=False)
    if not destination.is_relative_to(root):
        raise ValueError("download destination escapes configured download directory")
    return destination


def _content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _validate_max_bytes(max_bytes: int) -> None:
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")


def _max_download_size_message(size_bytes: int, max_bytes: int) -> str:
    return f"download size {size_bytes} exceeds maximum download size {max_bytes}"


def _asset_summary(
    asset: MediaAsset,
    test: CrashTest,
    active_job: DownloadJob | None = None,
) -> dict[str, object]:
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
        "queued_job_id": active_job.id if active_job is not None else None,
        "queued_job_status": active_job.status if active_job is not None else None,
    }


def _job_summary(job: DownloadJob, *, already_queued: bool = False) -> dict[str, object]:
    return {
        "id": job.id,
        "media_asset_id": job.media_asset_id,
        "test_no": job.test_no,
        "status": job.status,
        "already_queued": already_queued,
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
