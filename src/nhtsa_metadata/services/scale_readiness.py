from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    CrashTest,
    InstrumentationChannel,
    MediaAsset,
    SourcePayload,
    SourcePayloadObservation,
    TestFilterSummary,
)


@dataclass(frozen=True)
class ScaleReadinessReport:
    tests: int
    source_payloads: int
    source_payload_observations: int
    instrumentation_channels: int
    media_assets: int
    filter_summaries: int
    ready_for_larger_fixture: bool
    notes: list[str]


class ScaleReadinessService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def report(self) -> ScaleReadinessReport:
        tests = _count(self.session, CrashTest.id)
        source_payloads = _count(self.session, SourcePayload.id)
        observations = _count(self.session, SourcePayloadObservation.id)
        instrumentation = _count(self.session, InstrumentationChannel.id)
        media_assets = _count(self.session, MediaAsset.id)
        summaries = _count(self.session, TestFilterSummary.id)
        return ScaleReadinessReport(
            tests=tests,
            source_payloads=source_payloads,
            source_payload_observations=observations,
            instrumentation_channels=instrumentation,
            media_assets=media_assets,
            filter_summaries=summaries,
            ready_for_larger_fixture=source_payloads >= tests and summaries == tests,
            notes=[
                "raw payload JSON is not indexed as a whole",
                "read models are rebuildable from canonical tables",
                "fixture collection is idempotent and can be resumed by re-running collect",
            ],
        )


def _count(session: Session, column: Any) -> int:
    return int(session.scalar(select(func.count(column))) or 0)
