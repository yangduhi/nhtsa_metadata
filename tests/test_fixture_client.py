import pytest

from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient, FixtureNotFoundError


def test_fixture_client_fetches_payload_without_http() -> None:
    client = FixtureNhtsaClient()
    result = client.fetch("test_summary", test_no=10001)
    assert result.http_status == 200
    assert result.payload["results"][0]["testNo"] == 10001
    assert result.request.url.startswith("fixture://")


def test_fixture_client_fetches_instrumentation_pages() -> None:
    client = FixtureNhtsaClient()
    pages = client.fetch_all_pages("instrumentation_info", test_no=10001)
    assert [page.meta.pagination.page_number for page in pages if page.meta.pagination] == [0, 1]
    assert pages[0].meta.pagination.total == 634


def test_fixture_client_missing_fixture_raises() -> None:
    client = FixtureNhtsaClient()
    with pytest.raises(FixtureNotFoundError):
        client.fetch("test_summary", test_no=99999)
