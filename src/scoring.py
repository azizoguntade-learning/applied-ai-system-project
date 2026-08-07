"""Pure scoring and ranking logic.

This is the deterministic heart of the retrieval step. It is kept free of any
I/O or agent state so it is trivial to unit-test and reason about. The scoring
rule is intentionally unchanged from the original project so behavior and
scores stay identical:

- +2.0 for an exact genre match
- +1.0 for an exact mood match
- up to +1.0 for energy proximity (1.0 - |target - song|)
- -1.0 to +1.0 for acoustic fit, but *only* when the user asked for acoustic

The acoustic term is conditional on purpose. It leaves the original three-term
rule untouched for every profile that expresses no acoustic preference, so the
maximum score is 4.0 as before and rises to 5.0 only for a user who asked.

It is also *centred*, not a bonus: ``(acousticness - 0.5) * 2``. A bonus-only
term was tried first and measured to be inert -- adding a non-negative number
to every candidate shifted all the scores but reordered nothing on real
queries, because it can never demote a track. Since asking for acoustic music
is an explicit preference, a track at 0.05 acousticness should lose ground,
not merely fail to gain it.
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

    # 4. Acoustic fit (-1.0 to +1.0), only when the user expressed a preference.
    #    Guarded so it never reshuffles rankings for profiles that said nothing
    #    about acoustic music; centred so it can demote, not just promote.
    if user.likes_acoustic:
        acoustic_fit = (song.acousticness - 0.5) * 2
        score += acoustic_fit
        reasons.append(
            f"Acoustic fit {song.acousticness} ({acoustic_fit:+.2f})"
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
