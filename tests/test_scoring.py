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
        assert any("Acoustic fit" in r for r in reasons)

    def test_low_acousticness_is_penalised_not_merely_unrewarded(self):
        """The term is centred, so a non-acoustic track loses ground."""
        user = UserProfile("pop", "happy", target_energy=0.5, likes_acoustic=True)
        indifferent = UserProfile("pop", "happy", target_energy=0.5, likes_acoustic=False)
        loud = _song(acousticness=0.05)

        assert score_song(user, loud)[0] < score_song(indifferent, loud)[0]

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

    def test_acoustic_preference_changes_the_ranking(self, catalog):
        """Asking for acoustic must actually move the results, not be inert."""
        relaxed_only = UserProfile("", "relaxed", target_energy=0.2, likes_acoustic=False)
        wants_acoustic = UserProfile("", "relaxed", target_energy=0.2, likes_acoustic=True)

        without = [r.song.title for r in rank_songs(relaxed_only, catalog, k=5)]
        with_acoustic = [r.song.title for r in rank_songs(wants_acoustic, catalog, k=5)]

        assert without != with_acoustic

    def test_acoustic_preference_raises_mean_acousticness_of_top_results(self, catalog):
        """Measured on the top 3 -- the cut the CLI actually shows.

        Over a wider window the *set* of candidates is unchanged and only the
        order moves, so a top-5 mean would look flat even though the ranking
        genuinely improved.
        """
        relaxed_only = UserProfile("", "relaxed", target_energy=0.2, likes_acoustic=False)
        wants_acoustic = UserProfile("", "relaxed", target_energy=0.2, likes_acoustic=True)

        def mean_acousticness(profile):
            picks = rank_songs(profile, catalog, k=3)
            return sum(r.song.acousticness for r in picks) / len(picks)

        # 0.75 without the preference -> 0.92 with it.
        assert mean_acousticness(wants_acoustic) > mean_acousticness(relaxed_only)

    def test_weakly_acoustic_track_no_longer_outranks_a_strongly_acoustic_one(self, catalog):
        """Regression for the inversion the centred term was written to fix.

        With a bonus-only term, Island Breeze (reggae, relaxed, acousticness
        0.40) scored 2.00 and beat Midnight Sonata (classical, melancholic,
        0.95) at 1.90 -- the +1.0 mood match outweighed the acousticness gap
        and the bonus could not demote anything. Centring the term flips it.
        """
        user = UserProfile("", "relaxed", target_energy=0.2, likes_acoustic=True)
        by_title = {rec.song.title: rec for rec in rank_songs(user, catalog, k=len(catalog))}

        island, sonata = by_title["Island Breeze"], by_title["Midnight Sonata"]
        assert island.song.acousticness < sonata.song.acousticness
        assert sonata.score > island.score


class TestRankingInvariants:
    def test_ranking_is_descending_with_acoustic_preference(self, catalog):
        user = UserProfile("lofi", "chill", target_energy=0.35, likes_acoustic=True)
        scores = [rec.score for rec in rank_songs(user, catalog, k=len(catalog))]
        assert scores == sorted(scores, reverse=True)
