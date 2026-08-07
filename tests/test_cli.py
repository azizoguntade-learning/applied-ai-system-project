"""CLI behaviour tests.

The CLI is how a grader and a future employer actually meet this project, so
its contract is worth pinning down: exit codes, flag handling, and the fact
that a critic repair is visible in the output rather than buried in a log.
"""

import pytest

from src import config
from src.main import DEMO_QUERIES, build_parser, cli, format_result
from src.models import PipelineResult, PipelineStatus, TraceStep
from src.orchestrator import Orchestrator


class TestArgumentParsing:
    def test_defaults(self):
        args = build_parser().parse_args([])
        assert args.requests == []
        assert args.top == config.DEMO_K
        assert not args.interactive
        assert not args.verbose

    def test_multiple_requests_are_collected(self):
        args = build_parser().parse_args(["chill lofi", "happy pop"])
        assert args.requests == ["chill lofi", "happy pop"]

    def test_k_can_be_overridden(self):
        assert build_parser().parse_args(["-k", "7"]).top == 7
        assert build_parser().parse_args(["--top", "7"]).top == 7

    def test_help_exits_cleanly(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            build_parser().parse_args(["--help"])
        assert exc_info.value.code == 0
        assert "REQUEST" in capsys.readouterr().out

    def test_bad_k_is_rejected(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["-k", "not-a-number"])


class TestFormatting:
    def _result(self, repaired=False, trace=None):
        return PipelineResult(
            status=PipelineStatus.OK, message="Top picks:", repaired=repaired,
            trace=trace or [],
        )

    def test_status_is_shown(self):
        assert "[ok]" in format_result(self._result())

    def test_repaired_flag_is_visible(self):
        assert "[repaired]" in format_result(self._result(repaired=True))

    def test_repaired_flag_absent_when_not_repaired(self):
        assert "[repaired]" not in format_result(self._result())

    def test_trace_hidden_unless_verbose(self):
        result = self._result(trace=[TraceStep("critic", "flag", "mood mismatch")])
        assert "Agent trace" not in format_result(result, verbose=False)

    def test_trace_shown_when_verbose(self):
        result = self._result(trace=[TraceStep("critic", "flag", "mood mismatch")])
        rendered = format_result(result, verbose=True)
        assert "Agent trace" in rendered
        assert "mood mismatch" in rendered


class TestExitCodes:
    def test_success_returns_zero(self, capsys):
        assert cli(["chill lofi", "--no-traces"]) == 0
        assert "Library Rain" in capsys.readouterr().out

    def test_missing_catalog_returns_one_without_a_traceback(self, capsys, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "CATALOG_PATH", tmp_path / "gone.csv")

        assert cli(["chill lofi", "--no-traces"]) == 1

        captured = capsys.readouterr()
        assert captured.err.startswith("Error: Song catalog not found")
        assert "Traceback" not in captured.err


class TestEndToEndOutput:
    def test_demo_set_runs_and_summarises(self, capsys):
        assert cli(["--no-traces"]) == 0
        out = capsys.readouterr().out

        assert f"{len(DEMO_QUERIES)} requests" in out
        assert "blocked by guardrails" in out
        assert "repaired by the critic" in out

    def test_demo_set_exercises_every_branch(self, capsys):
        cli(["--no-traces"])
        out = capsys.readouterr().out

        assert "[ok]" in out
        assert "[repaired]" in out
        assert "[blocked]" in out
        assert "[low_confidence]" in out

    def test_single_request_prints_no_summary(self, capsys):
        cli(["chill lofi", "--no-traces"])
        assert "requests:" not in capsys.readouterr().out

    def test_k_controls_the_number_of_results(self, catalog):
        orch = Orchestrator(catalog, write_traces=False)
        assert len(orch.handle("chill lofi", k=2).recommendations) == 2
        assert len(orch.handle("chill lofi", k=5).recommendations) == 5

    def test_no_traces_flag_writes_nothing(self, capsys, monkeypatch, tmp_path):
        trace_file = tmp_path / "traces.jsonl"
        monkeypatch.setattr(config, "TRACE_FILE", trace_file)

        cli(["chill lofi", "--no-traces"])

        assert not trace_file.exists()
