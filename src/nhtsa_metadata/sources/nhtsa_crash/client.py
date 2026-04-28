from __future__ import annotations

from typing import Protocol

from nhtsa_metadata.config import Settings
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient


class LiveAccessNotAllowedError(RuntimeError):
    pass


class SourceClientProtocol(Protocol):
    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult: ...

    def fetch_all_pages(
        self, endpoint_name: str, **path_and_query: object
    ) -> list[SourceFetchResult]: ...


class LiveNhtsaClient:
    """Live client safety skeleton. Actual HTTP transport is added in Phase 7."""

    def __init__(self, settings: Settings, allow_live: bool = False) -> None:
        if not allow_live or not settings.allow_live:
            raise LiveAccessNotAllowedError("live NHTSA access requires explicit opt-in")
        self.settings = settings

    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        raise NotImplementedError("live HTTP transport is implemented in Phase 7")

    def fetch_all_pages(
        self, endpoint_name: str, **path_and_query: object
    ) -> list[SourceFetchResult]:
        return [self.fetch(endpoint_name, **path_and_query)]


__all__ = [
    "FixtureNhtsaClient",
    "LiveAccessNotAllowedError",
    "LiveNhtsaClient",
    "SourceClientProtocol",
]
