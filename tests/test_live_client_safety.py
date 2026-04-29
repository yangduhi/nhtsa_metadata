import httpx
import pytest
from typer.testing import CliRunner

from nhtsa_metadata.cli import app
from nhtsa_metadata.config import Settings
from nhtsa_metadata.sources.nhtsa_crash.live_client import (
    LiveAccessNotAllowedError,
    LiveNhtsaClient,
)


def test_live_client_blocked_without_command_allow() -> None:
    with pytest.raises(LiveAccessNotAllowedError):
        LiveNhtsaClient(Settings(allow_live=True), allow_live=False)


def test_live_client_blocked_without_settings_allow() -> None:
    with pytest.raises(LiveAccessNotAllowedError):
        LiveNhtsaClient(Settings(allow_live=False), allow_live=True)


def test_live_client_uses_fake_transport_only() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "get-test-detail/10001" in str(request.url)
        return httpx.Response(
            200,
            json={
                "meta": {"pagination": {"pageNumber": 0, "count": 1, "total": 1}},
                "results": [{"testNo": 10001}],
            },
        )

    client = LiveNhtsaClient(
        Settings(allow_live=True),
        allow_live=True,
        transport=httpx.MockTransport(handler),
    )
    result = client.fetch("test_detail", test_no=10001)
    assert result.payload["results"][0]["testNo"] == 10001


def test_live_client_passes_test_date_from_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["testDateFrom"] == "2011-01-01"
        return httpx.Response(
            200,
            json={
                "meta": {"pagination": {"pageNumber": 0, "count": 0, "total": 0}},
                "results": [],
            },
        )

    client = LiveNhtsaClient(
        Settings(allow_live=True),
        allow_live=True,
        transport=httpx.MockTransport(handler),
    )
    client.fetch("search", testDateFrom="2011-01-01")


def test_cli_live_without_allow_live_fails_before_http() -> None:
    result = CliRunner().invoke(
        app,
        ["catalog", "collect-test", "--test-no", "10001", "--source", "live"],
    )
    assert result.exit_code != 0
