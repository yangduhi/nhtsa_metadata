from pathlib import Path

import pytest

from nhtsa_metadata.config import Settings


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    return Settings(database_url=f"sqlite:///{tmp_path / 'test.sqlite'}", environment="test")


# Tests marked `live` must never run in default verification.
