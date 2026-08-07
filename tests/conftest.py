"""Shared pytest fixtures.

Lives here rather than in a single test module so every test file gets the
same catalog and orchestrator without re-loading the CSV or recomputing paths.
"""

import logging

import pytest

from src import config
from src.data_loader import load_songs
from src.orchestrator import Orchestrator


@pytest.fixture(autouse=True)
def _propagating_logs():
    """Keep ``src.*`` log records flowing to the root logger during tests.

    ``configure_logging()`` sets ``propagate = False`` so the app never double
    prints. pytest's ``caplog`` fixture captures at the root, so if anything in
    a test session calls ``configure_logging()``, every later caplog assertion
    would silently capture nothing. Forcing propagation per test makes log
    assertions independent of whether the app logger has been configured.
    """
    logger = logging.getLogger("src")
    previous = logger.propagate
    logger.propagate = True
    yield
    logger.propagate = previous


@pytest.fixture(scope="session")
def catalog():
    """The real song catalog, loaded once for the whole test session."""
    return load_songs(config.CATALOG_PATH)


@pytest.fixture(scope="session")
def orchestrator(catalog):
    """An orchestrator wired to the real catalog."""
    return Orchestrator(catalog)
