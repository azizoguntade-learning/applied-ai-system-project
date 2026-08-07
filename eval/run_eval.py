#!/usr/bin/env python3
"""Evaluation harness for the Music Recommender.

Runs every case in ``golden.json`` through the real pipeline and prints a
pass/fail report plus aggregate reliability metrics. Exits non-zero if any
case fails, so it can be used as a CI gate as well as a report.

    python eval/run_eval.py              # full report
    python eval/run_eval.py --quiet      # summary only
    python eval/run_eval.py --category guardrail_injection
    python eval/run_eval.py --json       # machine-readable

The harness deliberately drives the system through ``Orchestrator.handle``,
the same entry point the CLI uses. It asserts on *behaviour* (which song came
back, whether the guardrail fired, whether the critic repaired the result),
never on exact wording, so prose changes cannot produce a false failure.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow `python eval/run_eval.py` from anywhere, not just the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import config                     # noqa: E402
from src.data_loader import load_songs     # noqa: E402
from src.models import PipelineResult      # noqa: E402
from src.orchestrator import Orchestrator  # noqa: E402

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.json"

PASS, FAIL = "PASS", "FAIL"


# --------------------------------------------------------------------------- #
# Expectation checking
# --------------------------------------------------------------------------- #
def check_case(expect: Dict[str, Any], result: PipelineResult) -> List[str]:
    """Compare one result against its expectations.

    Returns a list of failure descriptions -- empty means the case passed.
    Every supported expectation key is handled here, and an unrecognised key
    is itself a failure rather than being silently ignored: a typo in the
    golden file must never read as a pass.
    """
    failures: List[str] = []
    top = result.recommendations[0].song if result.recommendations else None

    for key, want in expect.items():
        if key == "status":
            if result.status.value != want:
                failures.append(f"status: expected {want}, got {result.status.value}")

        elif key == "repaired":
            if result.repaired != want:
                failures.append(f"repaired: expected {want}, got {result.repaired}")

        elif key == "critic_flagged":
            flagged = result.critic_flagged
            if flagged != want:
                failures.append(f"critic_flagged: expected {want}, got {flagged}")

        elif key in {"top_genre", "top_mood", "top_title"}:
            if top is None:
                failures.append(f"{key}: expected {want!r}, but no recommendations")
                continue
            attr = {"top_genre": "genre", "top_mood": "mood", "top_title": "title"}[key]
            got = getattr(top, attr)
            if got != want:
                failures.append(f"{key}: expected {want!r}, got {got!r}")

        elif key == "min_top_acousticness":
            if top is None:
                failures.append(f"{key}: no recommendations")
            elif top.acousticness < want:
                failures.append(
                    f"{key}: expected >= {want}, got {top.acousticness} ({top.title})"
                )

        elif key == "max_top_energy_gap":
            if top is None or result.intent is None:
                failures.append(f"{key}: no recommendations or no intent")
            else:
                gap = abs(result.intent.target_energy - top.energy)
                if gap > want:
                    failures.append(f"{key}: expected <= {want}, got {gap:.2f}")

        elif key == "contains_title":
            titles = [rec.song.title for rec in result.recommendations]
            if want not in titles:
                failures.append(f"contains_title: {want!r} not in {titles}")

        elif key == "min_confidence":
            got = result.intent.confidence if result.intent else 0.0
            if got < want:
                failures.append(f"min_confidence: expected >= {want}, got {got:.2f}")

        else:
            failures.append(f"unknown expectation key {key!r} in golden.json")

    return failures


# --------------------------------------------------------------------------- #
# Running
# --------------------------------------------------------------------------- #
def run_cases(cases: List[dict], orchestrator: Orchestrator, k: int) -> List[dict]:
    outcomes = []
    for case in cases:
        result = orchestrator.handle(case["request"], k=k)
        failures = check_case(case.get("expect", {}), result)
        outcomes.append({
            "id": case["id"],
            "category": case["category"],
            "request": case["request"],
            "verdict": PASS if not failures else FAIL,
            "failures": failures,
            "repaired": result.repaired,
            "status": result.status.value,
            "confidence": result.intent.confidence if result.intent else 0.0,
            "critic_flagged": result.critic_flagged,
        })
    return outcomes


def summarise(outcomes: List[dict]) -> dict:
    total = len(outcomes)
    passed = sum(1 for o in outcomes if o["verdict"] == PASS)

    by_category: Dict[str, Dict[str, int]] = {}
    for o in outcomes:
        bucket = by_category.setdefault(o["category"], {"passed": 0, "total": 0})
        bucket["total"] += 1
        bucket["passed"] += o["verdict"] == PASS

    guardrail_cases = [o for o in outcomes if o["category"].startswith("guardrail")]
    guardrail_blocked = sum(1 for o in guardrail_cases if o["status"] == "blocked")
    scored = [o for o in outcomes if o["status"] == "ok"]

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total else 0.0,
        "by_category": by_category,
        "guardrail_total": len(guardrail_cases),
        "guardrail_blocked": guardrail_blocked,
        "guardrail_block_rate": guardrail_blocked / len(guardrail_cases) if guardrail_cases else 0.0,
        "critic_flagged": sum(1 for o in outcomes if o["critic_flagged"]),
        "repaired": sum(1 for o in outcomes if o["repaired"]),
        "mean_confidence": (
            sum(o["confidence"] for o in scored) / len(scored) if scored else 0.0
        ),
    }


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def print_report(outcomes: List[dict], stats: dict, quiet: bool = False) -> None:
    line = "=" * 72

    if not quiet:
        print(line)
        print("MUSIC RECOMMENDER — EVALUATION REPORT")
        print(line)
        print(f"{'RESULT':<6} {'ID':<22} {'CATEGORY':<22} REQUEST")
        print("-" * 72)
        for o in outcomes:
            print(f"{o['verdict']:<6} {o['id']:<22} {o['category']:<22} {o['request'][:40]!r}")
            for failure in o["failures"]:
                print(f"       └─ {failure}")
        print()

    print(line)
    print("SUMMARY")
    print(line)
    print(f"  Cases passed          {stats['passed']}/{stats['total']}"
          f"  ({stats['pass_rate']:.0%})")
    print()
    print("  By category:")
    for category, bucket in sorted(stats["by_category"].items()):
        rate = bucket["passed"] / bucket["total"]
        print(f"    {category:<24} {bucket['passed']}/{bucket['total']}  ({rate:.0%})")
    print()
    print("  Reliability metrics:")
    print(f"    Guardrail block rate    {stats['guardrail_blocked']}/{stats['guardrail_total']}"
          f"  ({stats['guardrail_block_rate']:.0%})")
    print(f"    Critic flagged          {stats['critic_flagged']} case(s)")
    print(f"    Critic repaired         {stats['repaired']} case(s)")
    print(f"    Mean routing confidence {stats['mean_confidence']:.2f}")
    print()
    verdict = "ALL CASES PASSED" if stats["failed"] == 0 else f"{stats['failed']} CASE(S) FAILED"
    print(f"  {verdict}")
    print(line)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def load_golden(path: Path = GOLDEN_PATH) -> List[dict]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)["cases"]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the golden-set evaluation.")
    parser.add_argument("--category", help="only run cases in this category")
    parser.add_argument("--quiet", action="store_true", help="summary only")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    parser.add_argument("-k", "--top", type=int, default=config.DEFAULT_K)
    args = parser.parse_args(argv)

    cases = load_golden()
    if args.category:
        cases = [c for c in cases if c["category"] == args.category]
        if not cases:
            print(f"No cases in category {args.category!r}", file=sys.stderr)
            return 2

    songs = load_songs(config.CATALOG_PATH)
    orchestrator = Orchestrator(songs, write_traces=False)

    outcomes = run_cases(cases, orchestrator, args.top)
    stats = summarise(outcomes)

    if args.json:
        print(json.dumps({"cases": outcomes, "summary": stats}, indent=2))
    else:
        print_report(outcomes, stats, quiet=args.quiet)

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
