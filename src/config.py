"""Central configuration: filesystem paths, model settings, and tuning knobs.

Every path is derived from this file's own location rather than the current
working directory, so ``python -m src.main`` behaves the same no matter where
it is invoked from. Tests import the same constants instead of recomputing
them, which keeps the test suite and the app pointed at one catalog.
"""

import os
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

ENV_FILE = PROJECT_ROOT / ".env"

# --------------------------------------------------------------------------- #
# Retrieval / scoring
# --------------------------------------------------------------------------- #
DEFAULT_K = 5   # recommendations returned by the pipeline
DEMO_K = 3      # shorter list for the CLI demo, so output stays readable

# The critic may ask for exactly one retry. Bounded on purpose: an unbounded
# repair loop is the classic way an "agentic" system burns tokens forever.
MAX_CRITIC_RETRIES = 1

# Thresholds the CriticAgent judges a result against.
CRITIC_ENERGY_TOLERANCE = 0.35   # |intent energy - song energy| must be <= this
CRITIC_MIN_ACOUSTICNESS = 0.5    # when the user asked for acoustic

# --------------------------------------------------------------------------- #
# Claude API
# --------------------------------------------------------------------------- #
API_KEY_ENV = "ANTHROPIC_API_KEY"

MODEL_ID = "claude-opus-5"

# Routing is a small extraction task, so it runs cheap. Reasoning gets a little
# more room because it writes prose.
ROUTER_EFFORT = "low"
ROUTER_MAX_TOKENS = 4096
REASONER_EFFORT = "low"
REASONER_MAX_TOKENS = 4096


def load_env_file(path: Path = ENV_FILE) -> None:
    """Load ``KEY=value`` pairs from a .env file into os.environ.

    A deliberately tiny parser so the project needs no python-dotenv
    dependency. Real environment variables always win, so exporting a key in
    the shell overrides the file. Missing or malformed files are ignored --
    a broken .env should never stop the app from starting.
    """
    if not path.is_file():
        return

    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and value and key not in os.environ:
                os.environ[key] = value
    except OSError:
        return


def has_api_key() -> bool:
    """True when an Anthropic API key is present in the environment."""
    return bool(os.environ.get(API_KEY_ENV, "").strip())
