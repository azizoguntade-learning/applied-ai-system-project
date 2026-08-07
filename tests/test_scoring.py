"""Scoring rule tests, with emphasis on the acoustic term.

`likes_acoustic` was carried on Intent and UserProfile, parsed by the routing
agent, and documented in the README long before `score_song` ever read it --
the field looked implemented from every angle except the one that mattered.
These tests pin the behaviour down so it cannot quietly regress again.
"""

from src.models import Song, UserProfile
from src.scoring import rank_songs, score_song


def _song(song_id=1, title="Test", genre="pop", mood="happy",
          energy=0.5, acousticness=0.5):
    return Song(
        id=song_id, title=title, artist="Test Artist", genre=genre, mood=mood,
        energy=energy, tempo_bpm=120, valence=0.5, danceability=0.5,
        acousticness=acousticness,
    )


class TestAcousticTerm:
    def test_acousticness_ignored_when_not_requested(self):
        """The original three-term rule must be untouched for everyone else."""
        user = UserProfile("pop", "happy", target_energy=0.5, likes_acoustic=False)
        quiet = _song(acousticness=0.95)
        loud = _song(acousticness=0.05)

        assert score_song(user, quiet)[0] == score_song(user, loud)[0]

    def test_acousticness_scored_when_requested(self):
        user = UserProfile("pop", "happy", target_energy=0.5, likes_acoustic=True)
        quiet_score, reasons = score_song(user, _song(acousticness=0.95))
        loud_score, _ = score_song(user, _song(acousticness=0.05))

        assert quiet_score > loud_score
        assert any("Acoustic match" in r for r in reasons)

    def test_max_score_stays_4_without_an_acoustic_preference(self):
        """Perfect match on genre + mood + energy tops out at the original 4.0."""
        user = UserProfile("pop", "happy", target_energy=0.5, likes_acoustic=False)
        score, _ = score_song(user, _song(energy=0.5, acousticness=1.0))
        assert score == 4.0

    def test_max_score_becomes_5_with_an_acoustic_preference(self):
        user = UserProfile("pop", "happy", target_energy=0.5, likes_acoustic=True)
        score, _ = score_song(user, _song(energy=0.5, acousticness=1.0))
        assert score == 5.0

    def test_reason_omitted_when_not_requested(self):
        user = UserProfile("pop", "happy", target_energy=0.5, likes_acoustic=False)
        _, reasons = score_song(user, _song(acousticness=0.9))
        assert not any("Acoustic" in r for r in reasons)


class TestAcousticRankingOnRealCatalog:
    """The bug as a user would have hit it: 'something acoustic and relaxed'."""

    def test_acoustic_request_promotes_acoustic_tracks(self, catalog):
        user = UserProfile("", "relaxed", target_energy=0.2, likes_acoustic=True)
        top = rank_songs(user, catalog, k=3)

        # Every pick should be genuinely acoustic, not merely relaxed.
        assert all(rec.song.acousticness >= 0.5 for rec in top), \
            [(r.song.title, r.song.acousticness) for r in top]

    def test_low_acousticness_track_no_longer_outranks_a_high_one(self, catalog):
        """Regression: Island Breeze (0.40) used to beat Midnight Sonata (0.95)."""
        user = UserProfile("", "relaxed", target_energy=0.2, likes_acoustic=True)
        ranked = rank_songs(user, catalog, k=len(catalog))
        order = [rec.song.title for rec in ranked]

        assert order.index("Midnight Sonata") < order.index("Island Breeze")


class TestRankingInvariants:
    def test_ranking_is_descending_with_acoustic_preference(self, catalog):
        user = UserProfile("lofi", "chill", target_energy=0.35, likes_acoustic=True)
        scores = [rec.score for rec in rank_songs(user, catalog, k=len(catalog))]
        assert scores == sorted(scores, reverse=True)
