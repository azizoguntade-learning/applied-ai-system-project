"""Logging configuration for the recommender pipeline.

Two sinks with deliberately different levels:

- **Console** at WARNING, so a normal ``python -m src.main`` run shows only
  things that need attention and the recommendation output stays readable.
- **File** (``logs/run.log``) at DEBUG, capturing the full record of what the
  system did: catalog loads, guardrail blocks and their category, which router
  handled each request, and every critic verdict.

The file half is what makes the system auditable after the fact -- the
"track what it does" half of the logging-and-guardrails requirement.
"""

import logging
from pathlib import Path
from typing import Optional

from . import config

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# The package logger. Module loggers (``src.agents``, ``src.guardrails``, ...)
# are children of this one, so configuring it once covers all of them.
_PACKAGE_LOGGER = "src"

_configured = False


def configure_logging(verbose: bool = False, log_file: Optional[Path] = None) -> logging.Logger:
    """Set up console and file logging. Safe to call more than once.

    Args:
        verbose: lower the console threshold to DEBUG. The file always records
            at DEBUG regardless.
        log_file: override the log destination (used by tests so they never
            write to the committed ``logs/run.log``).

    Returns:
        The configured package logger.
    """
    global _configured

    logger = logging.getLogger(_PACKAGE_LOGGER)

    # Idempotent: repeated calls (common in tests) must not stack handlers and
    # multiply every log line.
    if _configured and log_file is None:
        if verbose:
            for handler in logger.handlers:
                if getattr(handler, "_is_console", False):
                    handler.setLevel(logging.DEBUG)
        return logger

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    logger.setLevel(logging.DEBUG)
    # Don't hand records to the root logger as well, or pytest's capture and
    # any library config would print everything a second time.
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console.setFormatter(formatter)
    console._is_console = True  # type: ignore[attr-defined]
    logger.addHandler(console)

    target = log_file if log_file is not None else config.LOG_FILE
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(target, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        # A read-only or missing logs/ directory must not stop the app. Warn on
        # the console and carry on with console-only logging.
        logger.warning("Could not open log file %s (%s); logging to console only.", target, exc)

    if log_file is None:
        _configured = True
    return logger
