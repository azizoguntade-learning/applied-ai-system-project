"""Pure scoring and ranking logic.

This is the deterministic heart of the retrieval step. It is kept free of any
I/O or agent state so it is trivial to unit-test and reason about. The scoring
rule is intentionally unchanged from the original project so behavior and
scores stay identical:

- +2.0 for an exact genre match
- +1.0 for an exact mood match
- up to +1.0 for energy proximity (1.0 - |target - song|)
"""

from typing import List, Tuple

from .models import Recommendation, Song, UserProfile


def score_song(user: UserProfile, song: Song) -> Tuple[float, List[str]]:
    """Score one song against a user profile, returning (score, reasons)."""
    score = 0.0
    reasons: List[str] = []

    # 1. Genre match (+2.0)
    if song.genre == user.favorite_genre:
        score += 2.0
        reasons.append("Matched genre (+2.0)")

    # 2. Mood match (+1.0)
    if song.mood == user.favorite_mood:
        score += 1.0
        reasons.append("Matched mood (+1.0)")

    # 3. Energy proximity (up to +1.0)
    energy_proximity = 1.0 - abs(user.target_energy - song.energy)
    score += energy_proximity
    reasons.append(
        f"Energy proximity {song.energy} vs {user.target_energy} "
        f"(+{energy_proximity:.2f})"
    )

    return float(score), reasons


def rank_songs(user: UserProfile, songs: List[Song], k: int = 5) -> List[Recommendation]:
    """Score every song and return the top ``k`` as Recommendation objects."""
    scored: List[Recommendation] = []
    for song in songs:
        score, reasons = score_song(user, song)
        scored.append(Recommendation(song=song, score=score, reasons=reasons))

    scored.sort(key=lambda rec: rec.score, reverse=True)
    return scored[: max(0, k)]
