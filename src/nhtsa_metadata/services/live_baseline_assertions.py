from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    Barrier,
    CrashTest,
    InstrumentationChannel,
    MediaAsset,
    SourcePayload,
    TestParticipant,
    Vehicle,
)


@dataclass(frozen=True)
class BaselineAssertionResult:
    passed: bool
    messages: list[str]


class LiveBaselineAssertionError(AssertionError):
    pass


def assert_live_baseline(session: Session) -> BaselineAssertionResult:
    messages: list[str] = []
    _require(session.scalar(select(func.count(CrashTest.id))) or 0 >= 1, messages, "tests exist")
    _assert_10001(session, messages)
    _assert_10003(session, messages)
    if messages:
        raise LiveBaselineAssertionError("; ".join(messages))
    return BaselineAssertionResult(True, ["baseline assertions passed"])


def _assert_10001(session: Session, messages: list[str]) -> None:
    test = session.scalar(select(CrashTest).where(CrashTest.test_no == 10001))
    if test is None:
        messages.append("10001 test row missing")
        return
    _require(
        (session.scalar(select(func.count(Vehicle.id)).where(Vehicle.test_id == test.id)) or 0)
        >= 1,
        messages,
        "10001 vehicle rows missing",
    )
    _require(
        (session.scalar(select(func.count(Barrier.id)).where(Barrier.test_id == test.id)) or 0)
        >= 1,
        messages,
        "10001 barrier rows missing",
    )
    _require(
        (
            session.scalar(
                select(func.count(InstrumentationChannel.id)).where(
                    InstrumentationChannel.test_id == test.id
                )
            )
            or 0
        )
        >= 2,
        messages,
        "10001 instrumentation rows missing",
    )
    _require(
        (
            session.scalar(select(func.count(MediaAsset.id)).where(MediaAsset.test_id == test.id))
            or 0
        )
        >= 1,
        messages,
        "10001 media assets missing",
    )


def _assert_10003(session: Session, messages: list[str]) -> None:
    test = session.scalar(select(CrashTest).where(CrashTest.test_no == 10003))
    if test is None:
        messages.append("10003 test row missing")
        return
    _require(
        (session.scalar(select(func.count(Vehicle.id)).where(Vehicle.test_id == test.id)) or 0)
        >= 2,
        messages,
        "10003 vehicle rows missing",
    )
    _require(
        session.scalar(
            select(TestParticipant).where(
                TestParticipant.test_id == test.id,
                TestParticipant.participant_kind == "impactor_vehicle",
            )
        )
        is not None,
        messages,
        "10003 impactor participant missing",
    )
    _require(
        session.scalar(
            select(SourcePayload).where(
                SourcePayload.test_no == 10003,
                SourcePayload.endpoint_name == "barrier_info",
            )
        )
        is not None,
        messages,
        "10003 barrier source payload missing",
    )


def _require(condition: bool, messages: list[str], message: str) -> None:
    if not condition:
        messages.append(message)
