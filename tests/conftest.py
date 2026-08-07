"""Shared pytest fixtures.

Lives here rather than in a single test module so every test file gets the
same catalog and orchestrator without re-loading the CSV or recomputing paths.
"""

import pytest

from src import config
from src.data_loader import load_songs
from src.orchestrator import Orchestrator


@pytest.fixture(scope="session")
def catalog():
    """The real song catalog, loaded once for the whole test session."""
    return load_songs(config.CATALOG_PATH)


@pytest.fixture(scope="session")
def orchestrator(catalog):
    """An orchestrator wired to the real catalog."""
    return Orchestrator(catalog)
