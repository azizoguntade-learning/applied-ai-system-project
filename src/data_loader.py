"""Catalog loading.

Reads the CSV catalog into typed :class:`Song` objects. This fixes the
original inconsistency where ``load_songs`` returned dicts while the
``Recommender`` expected ``Song`` instances.
"""

import csv
import logging
from typing import List

from .models import Song

logger = logging.getLogger(__name__)


def load_songs(csv_path: str) -> List[Song]:
    """Load songs from a CSV file into a list of Song objects."""
    songs: List[Song] = []
    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            songs.append(
                Song(
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
            )

    logger.info("Loaded %d songs from %s", len(songs), csv_path)
    return songs
