"""Tests for the evaluation harness.

The harness is what the README cites as evidence that the system works, so it
needs to be trustworthy itself. The failure mode that matters most is a harness
that reports PASS when it should not -- these tests check that it fails when it
should, including on a typo in the golden file.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.run_eval import (  # noqa: E402
    FAIL,
    PASS,
    check_case,
    load_golden,
    main,
    run_cases,
    summarise,
)
from src.models import (  # noqa: E402
    CriticVerdict,
    Intent,
    PipelineResult,
    PipelineStatus,
    Recommendation,
    Song,
)


def _song(genre="pop", mood="happy", energy=0.5, acousticness=0.5, title="Test"):
    return Song(id=1, title=title, artist="A", genre=genre, mood=mood,
                energy=energy, tempo_bpm=120, valence=0.5, danceability=0.5,
                acousticness=acousticness)


def _result(song=None, status=PipelineStatus.OK, repaired=False, flagged=False,
            energy=0.5, confidence=1.0):
    recs = [Recommendation(song=song, score=1.0, reasons=[])] if song else []
    return PipelineResult(
        status=status, message="", recommendations=recs, repaired=repaired,
        critic_flagged=flagged, critic=CriticVerdict(ok=not flagged),
        intent=Intent(is_music_request=True, target_energy=energy, confidence=confidence),
    )


class TestExpectationChecking:
    def test_matching_expectations_produce_no_failures(self):
        assert check_case({"status": "ok", "top_genre": "pop"}, _result(_song())) == []

    @pytest.mark.parametrize("expect", [
        {"status": "blocked"},
        {"top_genre": "jazz"},
        {"top_mood": "melancholic"},
        {"top_title": "Nonexistent"},
        {"repaired": True},
        {"critic_flagged": True},
        {"min_top_acousticness": 0.9},
        {"max_top_energy_gap": 0.01},
        {"contains_title": "Nonexistent"},
        {"min_confidence": 1.1},
    ])
    def test_each_expectation_can_fail(self, expect):
        """Every supported key must be capable of failing, or it checks nothing."""
        result = _result(_song(energy=0.95), confidence=0.5)
        assert check_case(expect, result) != []

    def test_unknown_key_is_a_failure_not_a_silent_pass(self):
        """A typo in golden.json must never be mistaken for a passing case."""
        failures = check_case({"top_genr": "pop"}, _result(_song()))
        assert len(failures) == 1
        assert "unknown expectation key" in failures[0]

    def test_expectation_on_missing_recommendations_fails_cleanly(self):
        failures = check_case({"top_genre": "pop"}, _result(song=None))
        assert failures and "no recommendations" in failures[0]

    def test_empty_expectation_passes(self):
        assert check_case({}, _result(_song())) == []


class TestSummary:
    def test_counts_and_rates(self):
        outcomes = [
            {"verdict": PASS, "category": "taste", "status": "ok",
             "repaired": False, "critic_flagged": False, "confidence": 1.0},
            {"verdict": FAIL, "category": "taste", "status": "ok",
             "repaired": True, "critic_flagged": True, "confidence": 0.5},
            {"verdict": PASS, "category": "guardrail_injection", "status": "blocked",
             "repaired": False, "critic_flagged": False, "confidence": 0.0},
        ]
        stats = summarise(outcomes)

        assert stats["total"] == 3
        assert stats["passed"] == 2
        assert stats["failed"] == 1
        assert stats["by_category"]["taste"] == {"passed": 1, "total": 2}
        assert stats["guardrail_block_rate"] == 1.0
        assert stats["repaired"] == 1
        assert stats["critic_flagged"] == 1
        assert stats["mean_confidence"] == pytest.approx(0.75)

    def test_empty_outcomes_do_not_divide_by_zero(self):
        stats = summarise([])
        assert stats["pass_rate"] == 0.0
        assert stats["guardrail_block_rate"] == 0.0
        assert stats["mean_confidence"] == 0.0


class TestGoldenFile:
    def test_golden_file_is_valid_and_populated(self):
        cases = load_golden()
        assert len(cases) >= 15

    def test_every_case_is_well_formed(self):
        for case in load_golden():
            assert set(case) >= {"id", "category", "request", "expect"}, case
            assert case["expect"], f"{case['id']} asserts nothing"

    def test_case_ids_are_unique(self):
        ids = [c["id"] for c in load_golden()]
        assert len(ids) == len(set(ids))

    def test_every_category_is_represented(self):
        categories = {c["category"] for c in load_golden()}
        for expected in ("taste", "critic_repair", "low_confidence",
                         "guardrail_offtopic", "guardrail_injection"):
            assert expected in categories


class TestEndToEnd:
    def test_full_run_passes_and_exits_zero(self, capsys):
        assert main(["--quiet"]) == 0
        assert "ALL CASES PASSED" in capsys.readouterr().out

    def test_a_broken_expectation_exits_nonzero(self, capsys, tmp_path, monkeypatch):
        """The CI-gate promise: a regression must fail the build."""
        import eval.run_eval as harness

        broken = tmp_path / "golden.json"
        broken.write_text(json.dumps({"cases": [{
            "id": "impossible", "category": "selftest",
            "request": "chill lofi", "expect": {"top_genre": "polka"},
        }]}), encoding="utf-8")
        monkeypatch.setattr(harness, "GOLDEN_PATH", broken)

        assert main(["--quiet"]) == 1
        assert "1 CASE(S) FAILED" in capsys.readouterr().out

    def test_category_filter(self, capsys):
        assert main(["--category", "guardrail_injection", "--quiet"]) == 0
        assert "guardrail_injection" in capsys.readouterr().out

    def test_unknown_category_exits_two(self, capsys):
        assert main(["--category", "does-not-exist"]) == 2

    def test_json_output_is_parseable(self, capsys):
        main(["--json"])
        payload = json.loads(capsys.readouterr().out)
        assert "cases" in payload and "summary" in payload
        assert payload["summary"]["failed"] == 0

    def test_harness_does_not_write_traces(self, catalog, tmp_path, monkeypatch):
        """Evaluation runs must not pollute the committed trace log."""
        from src import config
        trace_file = tmp_path / "traces.jsonl"
        monkeypatch.setattr(config, "TRACE_FILE", trace_file)

        main(["--quiet"])

        assert not trace_file.exists()
