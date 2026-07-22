"""Backward-compatible facade.

The original project exposed everything from this module. After the refactor the
logic lives in focused modules (:mod:`src.models`, :mod:`src.scoring`,
:mod:`src.data_loader`), but the public names are re-exported here so existing
imports and tests keep working:

    from src.recommender import Song, UserProfile, Recommender
"""

from typing import List

from .data_loader import load_songs  # noqa: F401  (re-exported)
from .models import Recommendation, Song, UserProfile
from .scoring import rank_songs, score_song  # noqa: F401  (re-exported)


class Recommender:
    """Object-oriented wrapper over the pure scoring functions."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top ``k`` recommended songs for a user profile."""
        ranked = rank_songs(user, self.songs, k=k)
        return [rec.song for rec in ranked]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a string explaining why ``song`` matches the user."""
        _, reasons = score_song(user, song)
        return ", ".join(reasons)
