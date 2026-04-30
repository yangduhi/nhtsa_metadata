from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import CollectionRun


def mark_stale_started_runs(session: Session, reason: str) -> int:
    """Close previously interrupted runs before starting resumable work."""
    runs = list(
        session.scalars(
            select(CollectionRun).where(
                CollectionRun.status == "started",
                CollectionRun.finished_at.is_(None),
            )
        )
    )
    now = datetime.utcnow()
    for run in runs:
        run.status = "interrupted"
        run.finished_at = now
        run.error_json = {
            "error_type": "InterruptedRun",
            "message": reason,
        }
    session.flush()
    return len(runs)
