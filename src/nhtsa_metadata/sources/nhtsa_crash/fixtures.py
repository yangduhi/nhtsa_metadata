from __future__ import annotations

from pathlib import Path
from typing import Any

from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult, SourceRequest


class FixtureNotFoundError(FileNotFoundError):
    pass


class FixtureNhtsaClient:
    """Filesystem-backed source client. Full fixture mapping is added in Phase 3."""

    def __init__(self, fixture_root: Path | str = "tests/fixtures/nhtsa") -> None:
        self.fixture_root = Path(fixture_root)

    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        raise FixtureNotFoundError(
            f"fixture mapping is not implemented for {endpoint_name}: {path_and_query}"
        )

    def fetch_all_pages(
        self, endpoint_name: str, **path_and_query: object
    ) -> list[SourceFetchResult]:
        return [self.fetch(endpoint_name, **path_and_query)]


def fixture_result(endpoint_name: str, url: str, payload: dict[str, Any]) -> SourceFetchResult:
    return SourceFetchResult(
        request=SourceRequest(endpoint_name=endpoint_name, url=url),
        payload=payload,
        http_status=200,
    )
