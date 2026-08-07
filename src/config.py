"""Central configuration: filesystem paths and tuning knobs.

Every path is derived from this file's own location rather than the current
working directory, so ``python -m src.main`` behaves the same no matter where
it is invoked from. Tests import the same constants instead of recomputing
them, which keeps the test suite and the app pointed at one catalog.

The system is fully deterministic and offline: no API keys, no network calls,
no secrets. That is a design decision, not an omission -- see README.md.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
CATALOG_PATH = DATA_DIR / "songs.csv"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "run.log"
TRACE_FILE = LOG_DIR / "traces.jsonl"
EVIDENCE_DIR = LOG_DIR / "evidence"

# --------------------------------------------------------------------------- #
# Retrieval / scoring
# --------------------------------------------------------------------------- #
DEFAULT_K = 5   # recommendations returned by the pipeline
DEMO_K = 3      # shorter list for the CLI demo, so output stays readable

# The critic may ask for exactly one retry. Bounded on purpose: an unbounded
# repair loop is the classic way an "agentic" system spins forever.
MAX_CRITIC_RETRIES = 1

# Thresholds the CriticAgent judges a result against.
CRITIC_ENERGY_TOLERANCE = 0.35   # |intent energy - song energy| must be <= this
CRITIC_MIN_ACOUSTICNESS = 0.5    # when the user asked for acoustic
