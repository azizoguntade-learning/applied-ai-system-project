"""Catalog loading.

Reads the CSV catalog into typed :class:`Song` objects. This fixes the
original inconsistency where ``load_songs`` returned dicts while the
``Recommender`` expected ``Song`` instances.

Loading is deliberately fault-tolerant in one direction only:

- A missing or unreadable file is **fatal** -- there is nothing to recommend
  from, so it raises :class:`~src.errors.CatalogError` with a message that
  names the path it actually tried.
- A single malformed row is **survivable** -- it is logged and skipped so one
  bad line (a typo, a truncated export) cannot take down the whole catalog.
"""

import csv
import logging
from pathlib import Path
from typing import List, Optional, Union

from .errors import CatalogError
from .models import Song

logger = logging.getLogger(__name__)

# Columns every row must supply. Checked up front so a missing column is
# reported as one clear error rather than 17 identical row failures.
REQUIRED_COLUMNS = (
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
)


def _parse_row(row: dict, line_number: int) -> Optional[Song]:
    """Convert one CSV row into a Song, or return None if it is unusable."""
    try:
        return Song(
            id=int(row["id"]),
            title=row["title"],
            artist=row["artist"],
            genre=row["genre"],
            mood=row["mood"],
            energy=float(row["energy"]),
            tempo_bpm=float(row["tempo_bpm"]),
            valence=float(row["valence"]),
            danceability=float(row["danceability"]),
            acousticness=float(row["acousticness"]),
        )
    except (KeyError, TypeError) as exc:
        logger.warning("Skipping catalog row %d: missing field %s", line_number, exc)
    except ValueError as exc:
        logger.warning("Skipping catalog row %d: bad numeric value (%s)", line_number, exc)
    return None


def load_songs(csv_path: Union[str, Path]) -> List[Song]:
    """Load songs from a CSV file into a list of Song objects.

    Raises:
        CatalogError: the file is missing, unreadable, has the wrong columns,
            or yielded no usable rows.
    """
    path = Path(csv_path)
    songs: List[Song] = []

    try:
        with open(path, mode="r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)

            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise CatalogError(
                    "Catalog {} is missing required column(s): {}.".format(
                        path, ", ".join(missing)
                    )
                )

            # start=2 because line 1 is the header, so numbers match the file.
            for line_number, row in enumerate(reader, start=2):
                song = _parse_row(row, line_number)
                if song is not None:
                    songs.append(song)

    except FileNotFoundError:
        raise CatalogError(
            "Song catalog not found at {}. Check that the file exists, or point "
            "config.CATALOG_PATH somewhere else.".format(path)
        )
    except PermissionError:
        raise CatalogError("No permission to read the song catalog at {}.".format(path))
    except UnicodeDecodeError:
        raise CatalogError("Song catalog at {} is not valid UTF-8 text.".format(path))
    except OSError as exc:
        raise CatalogError("Could not read the song catalog at {}: {}".format(path, exc))

    if not songs:
        raise CatalogError(
            "Song catalog at {} contained no usable rows. See logs/run.log for the "
            "rows that were skipped.".format(path)
        )

    logger.info("Loaded %d songs from %s", len(songs), path)
    return songs
