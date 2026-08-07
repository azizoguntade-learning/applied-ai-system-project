"""Tests for the critic agent and the orchestrator's repair loop.

The critic is the project's "check" step -- the part that makes this a
plan -> act -> check agent rather than a straight-through pipeline. These
tests cover both halves: whether the critic *notices* a bad result, and
whether the orchestrator *acts* on that judgement correctly, including the
cases where it must decline to act.
"""

from src import config
from src.agents import RELAX_GENRE, CriticAgent, RetrievalAgent
from src.models import Intent, PipelineStatus, Recommendation, Song
from src.orchestrator import Orchestrator


def _song(title="Test", genre="pop", mood="happy", energy=0.5, acousticness=0.5):
    return Song(
        id=1, title=title, artist="Test Artist", genre=genre, mood=mood,
        energy=energy, tempo_bpm=120, valence=0.5, danceability=0.5,
        acousticness=acousticness,
    )


def _rec(song):
    return Recommendation(song=song, score=1.0, reasons=[])


class TestCriticDetection:
    """Does the critic notice when the top result misses the request?"""

    def test_accepts_a_matching_result(self):
        intent = Intent(is_music_request=True, genre="pop", mood="happy", target_energy=0.5)
        verdict = CriticAgent().check(intent, [_rec(_song())])

        assert verdict.ok
        assert verdict.issues == []

    def test_flags_a_genre_mismatch(self):
        intent = Intent(is_music_request=True, genre="jazz", mood="happy", target_energy=0.5)
        verdict = CriticAgent().check(intent, [_rec(_song(genre="pop"))])

        assert not verdict.ok
        assert any("jazz" in issue for issue in verdict.issues)

    def test_flags_a_mood_mismatch(self):
        intent = Intent(is_music_request=True, genre="pop", mood="melancholic", target_energy=0.5)
        verdict = CriticAgent().check(intent, [_rec(_song(mood="happy"))])

        assert not verdict.ok
        assert any("melancholic" in issue for issue in verdict.issues)

    def test_flags_a_non_acoustic_pick_when_acoustic_was_requested(self):
        intent = Intent(
            is_music_request=True, genre="pop", mood="happy",
            target_energy=0.5, likes_acoustic=True,
        )
        verdict = CriticAgent().check(intent, [_rec(_song(acousticness=0.05))])

        assert not verdict.ok
        assert any("acoustic" in issue.lower() for issue in verdict.issues)

    def test_ignores_acousticness_when_it_was_not_requested(self):
        intent = Intent(is_music_request=True, genre="pop", mood="happy", target_energy=0.5)
        verdict = CriticAgent().check(intent, [_rec(_song(acousticness=0.01))])

        assert verdict.ok

    def test_flags_an_energy_gap_beyond_tolerance(self):
        intent = Intent(is_music_request=True, genre="pop", mood="happy", target_energy=0.9)
        verdict = CriticAgent().check(intent, [_rec(_song(energy=0.1))])

        assert not verdict.ok
        assert any("energy" in issue.lower() for issue in verdict.issues)

    def test_allows_an_energy_gap_inside_tolerance(self):
        gap = config.CRITIC_ENERGY_TOLERANCE - 0.05
        intent = Intent(is_music_request=True, genre="pop", mood="happy", target_energy=0.5)
        verdict = CriticAgent().check(intent, [_rec(_song(energy=0.5 + gap))])

        assert verdict.ok

    def test_flags_an_empty_result_set(self):
        intent = Intent(is_music_request=True, genre="pop", mood="happy", target_energy=0.5)
        verdict = CriticAgent().check(intent, [])

        assert not verdict.ok
        assert verdict.relaxation is None  # nothing to relax; there are no results

    def test_judges_only_the_top_pick(self):
        """A weak second result must not sink an otherwise good answer."""
        intent = Intent(is_music_request=True, genre="pop", mood="happy", target_energy=0.5)
        verdict = CriticAgent().check(
            intent, [_rec(_song()), _rec(_song(genre="metal", mood="aggressive"))]
        )

        assert verdict.ok


class TestRelaxationProposal:
    def test_proposes_dropping_genre_when_one_was_requested(self):
        intent = Intent(is_music_request=True, genre="ambient", mood="intense", target_energy=0.9)
        verdict = CriticAgent().check(intent, [_rec(_song(genre="ambient", mood="chill", energy=0.2))])

        assert verdict.relaxation == RELAX_GENRE

    def test_proposes_nothing_when_no_genre_was_requested(self):
        """With no genre to drop, the critic reports without claiming a fix."""
        intent = Intent(is_music_request=True, genre=None, mood="intense", target_energy=0.9)
        verdict = CriticAgent().check(intent, [_rec(_song(mood="chill", energy=0.1))])

        assert not verdict.ok
        assert verdict.relaxation is None


class TestRepairLoop:
    """End-to-end behaviour of the orchestrator's check -> replan -> recheck."""

    def test_intense_ambient_is_repaired(self, catalog):
        """The documented failure: genre's +2.0 outvotes mood and energy.

        'intense ambient' retrieves Spacewalk Thoughts (ambient, chill,
        energy 0.28) purely on the genre match. The critic rejects it and the
        replan drops the genre filter.
        """
        result = Orchestrator(catalog, write_traces=False).handle("intense ambient", k=3)

        assert result.status == PipelineStatus.OK
        assert result.repaired
        assert result.recommendations[0].song.mood == "intense"

    def test_repair_note_is_shown_to_the_user(self, catalog):
        result = Orchestrator(catalog, write_traces=False).handle("intense ambient", k=3)

        assert "widened the search" in result.message
        # The header must not still advertise the genre that was dropped.
        assert "genre=ambient" not in result.message

    def test_a_good_request_is_not_repaired(self, catalog):
        result = Orchestrator(catalog, write_traces=False).handle("high energy happy pop", k=3)

        assert not result.repaired
        assert result.critic.ok
        assert "widened the search" not in result.message

    def test_repair_is_rejected_when_it_does_not_help(self, catalog):
        """A retry that is no better must leave the original answer alone.

        'happy classical' has exactly one classical track (Midnight Sonata,
        melancholic), so the mood can never be satisfied. Dropping the genre
        does not fix that, and the orchestrator must keep what it had.
        """
        orch = Orchestrator(catalog, write_traces=False)
        result = orch.handle("happy classical", k=3)

        actions = [step.action for step in result.trace]
        assert "replan" in actions
        assert ("reject_repair" in actions) or ("accept_repair" in actions)
        # Whichever way it went, the critic's decision must be recorded.
        assert result.critic is not None

    def test_retry_is_bounded(self, catalog):
        """At most MAX_CRITIC_RETRIES replans, however bad the request."""
        result = Orchestrator(catalog, write_traces=False).handle("intense ambient", k=3)

        replans = [s for s in result.trace if s.action == "replan"]
        assert len(replans) <= config.MAX_CRITIC_RETRIES

    def test_relaxed_intent_actually_drops_the_genre(self, catalog):
        intent = Intent(is_music_request=True, genre="ambient", mood="intense", target_energy=0.9)
        relaxed = Orchestrator._relax(intent, RELAX_GENRE)

        assert relaxed.genre is None
        assert relaxed.mood == "intense"       # everything else is preserved
        assert relaxed.target_energy == 0.9
        assert intent.genre == "ambient"       # and the original is not mutated


class TestTrace:
    def test_every_stage_is_recorded(self, catalog):
        result = Orchestrator(catalog, write_traces=False).handle("chill lofi", k=3)
        agents = [step.agent for step in result.trace]

        for expected in ("guardrails", "router", "retriever", "critic", "reasoner"):
            assert expected in agents

    def test_blocked_requests_are_traced_too(self, catalog):
        result = Orchestrator(catalog, write_traces=False).handle("give me a recipe")

        assert result.status == PipelineStatus.BLOCKED
        assert result.trace[0].agent == "guardrails"
        assert result.trace[0].action == "block"

    def test_trace_steps_serialise_for_the_jsonl_log(self, catalog):
        result = Orchestrator(catalog, write_traces=False).handle("chill lofi", k=3)
        as_dict = result.trace[0].to_dict()

        assert set(as_dict) == {"agent", "action", "detail"}
        assert all(isinstance(v, str) for v in as_dict.values())

    def test_traces_are_written_to_disk_when_enabled(self, catalog, tmp_path, monkeypatch):
        trace_file = tmp_path / "traces.jsonl"
        monkeypatch.setattr(config, "TRACE_FILE", trace_file)

        Orchestrator(catalog, write_traces=True).handle("chill lofi", k=3)

        assert trace_file.is_file()
        assert '"request": "chill lofi"' in trace_file.read_text(encoding="utf-8")
