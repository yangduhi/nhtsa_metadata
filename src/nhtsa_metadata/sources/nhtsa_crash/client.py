from __future__ import annotations

from typing import Protocol

from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient
from nhtsa_metadata.sources.nhtsa_crash.live_client import (
    LiveAccessNotAllowedError,
    LiveNhtsaClient,
)


class SourceClientProtocol(Protocol):
    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult: ...

    def fetch_all_pages(
        self, endpoint_name: str, **path_and_query: object
    ) -> list[SourceFetchResult]: ...


__all__ = [
    "FixtureNhtsaClient",
    "LiveAccessNotAllowedError",
    "LiveNhtsaClient",
    "SourceClientProtocol",
]
