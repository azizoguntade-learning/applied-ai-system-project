"""Pipeline orchestrator.

Wires the agents into a single entry point: ``handle(text)`` takes a raw
free-text request and returns a structured :class:`PipelineResult`.

The flow is a plan -> act -> check loop:

    guardrails -> route (plan) -> retrieve (act) -> critic (check)
                                      ^                  |
                                      +--- replan <------+

The critic step is what distinguishes this from a straight-through pipeline.
When it finds the top result disagrees with the intent, the orchestrator drops
the constraint the critic names and retrieves once more -- then keeps the new
answer *only if the critic judges it better*. A retry that made things worse
would otherwise be worse than not retrying at all.

Every step appends a :class:`TraceStep`, so the reasoning behind a repaired
answer is inspectable in ``logs/traces.jsonl`` rather than taken on trust.
"""

import json
import logging
from dataclasses import replace
from typing import List, Optional

from . import config
from .agents import RELAX_GENRE, CriticAgent, ReasoningAgent, RetrievalAgent, RoutingAgent
from .guardrails import validate_input
from .models import (
    CriticVerdict,
    Intent,
    PipelineResult,
    PipelineStatus,
    Recommendation,
    Song,
    TraceStep,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, songs: List[Song], write_traces: bool = True):
        self.songs = songs
        self.router = RoutingAgent(songs)
        self.retriever = RetrievalAgent(songs)
        self.critic = CriticAgent()
        self.reasoner = ReasoningAgent()
        self.write_traces = write_traces
        # Catalog-derived vocabulary so bare genres/moods count as on-topic.
        self._known_terms = list(self.router.known_genres | self.router.known_moods)

    # ----------------------------------------------------------------- #
    # Main entry point
    # ----------------------------------------------------------------- #
    def handle(self, text: str, k: int = config.DEFAULT_K) -> PipelineResult:
        trace: List[TraceStep] = []
        logger.info("Request received: %r (k=%d)", text, k)

        # 1. Guardrails: reject unsafe / off-topic input before anything else.
        guard = validate_input(text, known_terms=self._known_terms)
        trace.append(TraceStep(
            "guardrails",
            "block" if not guard.allowed else "pass",
            guard.category.value if not guard.allowed else "clean",
        ))
        if not guard.allowed:
            logger.info("Pipeline result: BLOCKED (%s)", guard.category.value)
            return self._finish(text, PipelineResult(
                status=PipelineStatus.BLOCKED, message=guard.reason, trace=trace,
            ))

        # 2. Routing agent (plan): read the request into a structured intent.
        intent = self.router.route(text)
        trace.append(TraceStep("router", "route", self._describe_intent(intent)))
        logger.debug("Routed intent: %s", self._describe_intent(intent))

        if not intent.is_music_request:
            logger.info("Pipeline result: LOW_CONFIDENCE (no taste signal found)")
            return self._finish(text, PipelineResult(
                status=PipelineStatus.LOW_CONFIDENCE,
                message=(
                    "I couldn't find any music preferences in that request. "
                    "Try naming a genre, mood, or energy level."
                ),
                intent=intent,
                trace=trace,
            ))

        # 3. Retrieval agent (act).
        recommendations = self.retriever.retrieve(intent, k=k)
        trace.append(TraceStep("retriever", "retrieve", self._describe_top(recommendations)))

        # 4. Critic (check), with at most MAX_CRITIC_RETRIES repair attempts.
        recommendations, verdict, repaired, effective = self._check_and_repair(
            intent, recommendations, k, trace
        )

        # 5. Reasoning agent: format the final answer. Explained in terms of the
        #    *effective* intent, so the header never claims a genre the results
        #    no longer honour.
        message = self.reasoner.explain(effective, recommendations)
        if repaired:
            message = self._repair_note(intent, effective) + "\n\n" + message
        trace.append(TraceStep("reasoner", "explain", f"{len(recommendations)} recommendations"))

        top = recommendations[0] if recommendations else None
        logger.info(
            "Pipeline result: OK (%d recommendations, top=%s score=%.2f, repaired=%s)",
            len(recommendations),
            top.song.title if top else "none",
            top.score if top else 0.0,
            repaired,
        )

        return self._finish(text, PipelineResult(
            status=PipelineStatus.OK,
            message=message,
            intent=intent,
            recommendations=recommendations,
            trace=trace,
            repaired=repaired,
            critic=verdict,
        ))

    # ----------------------------------------------------------------- #
    # The check / replan loop
    # ----------------------------------------------------------------- #
    def _check_and_repair(self, intent, recommendations, k, trace):
        """Judge the results and, if warranted, retry once with a relaxed intent.

        Returns ``(recommendations, verdict, repaired, effective_intent)``. The
        retry is kept only when the critic finds strictly fewer problems with
        it, so a repair can never make the answer worse than doing nothing.
        """
        verdict = self.critic.check(intent, recommendations)
        trace.append(TraceStep(
            "critic", "pass" if verdict.ok else "flag",
            "no issues" if verdict.ok else "; ".join(verdict.issues),
        ))

        if verdict.ok:
            return recommendations, verdict, False, intent

        logger.info("Critic flagged %d issue(s): %s", len(verdict.issues), verdict.issues)

        for attempt in range(config.MAX_CRITIC_RETRIES):
            if verdict.relaxation is None:
                trace.append(TraceStep(
                    "critic", "no_repair",
                    "issues found but no constraint worth relaxing",
                ))
                logger.info("Critic proposed no repair; keeping the original result.")
                break

            relaxed = self._relax(intent, verdict.relaxation)
            trace.append(TraceStep(
                "orchestrator", "replan",
                f"attempt {attempt + 1}: {verdict.relaxation}",
            ))

            retry_recs = self.retriever.retrieve(relaxed, k=k)
            retry_verdict = self.critic.check(relaxed, retry_recs)
            trace.append(TraceStep(
                "critic", "recheck",
                "no issues" if retry_verdict.ok else "; ".join(retry_verdict.issues),
            ))

            if len(retry_verdict.issues) < len(verdict.issues):
                trace.append(TraceStep(
                    "orchestrator", "accept_repair",
                    f"{len(verdict.issues)} issue(s) -> {len(retry_verdict.issues)}; "
                    f"top is now {self._describe_top(retry_recs)}",
                ))
                logger.info(
                    "Repair accepted: %d issue(s) -> %d",
                    len(verdict.issues), len(retry_verdict.issues),
                )
                return retry_recs, retry_verdict, True, relaxed

            trace.append(TraceStep(
                "orchestrator", "reject_repair",
                f"retry was no better ({len(retry_verdict.issues)} issue(s)); "
                f"keeping the original",
            ))
            logger.info("Repair rejected: retry was no better; keeping the original.")
            break

        return recommendations, verdict, False, intent

    @staticmethod
    def _repair_note(original: Intent, effective: Intent) -> str:
        """One line telling the user which constraint was widened, and why.

        Without this the header would still advertise a genre that none of the
        results actually match, which reads as a bug rather than a decision.
        """
        if original.genre and effective.genre is None:
            wanted = "that mood and energy level" if original.mood else "that energy level"
            return (
                f"Note: no {original.genre} track in the catalog matched {wanted}, "
                f"so I widened the search beyond {original.genre}."
            )
        return "Note: the first set of results didn't match the request, so I searched again."

    @staticmethod
    def _relax(intent: Intent, relaxation: str) -> Intent:
        """Return a copy of the intent with one constraint dropped."""
        if relaxation == RELAX_GENRE:
            return replace(intent, genre=None)
        raise ValueError(f"Unknown relaxation: {relaxation!r}")

    # ----------------------------------------------------------------- #
    # Trace persistence
    # ----------------------------------------------------------------- #
    def _finish(self, text: str, result: PipelineResult) -> PipelineResult:
        if self.write_traces:
            self._append_trace(text, result)
        return result

    def _append_trace(self, text: str, result: PipelineResult) -> None:
        """Append one JSON line describing this request. Never fatal."""
        record = {
            "request": text,
            "status": result.status.value,
            "repaired": result.repaired,
            "steps": [step.to_dict() for step in result.trace],
        }
        try:
            config.TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(config.TRACE_FILE, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
        except OSError as exc:
            # Losing a trace line must never cost the user their answer.
            logger.warning("Could not write trace to %s (%s)", config.TRACE_FILE, exc)

    # ----------------------------------------------------------------- #
    # Formatting helpers
    # ----------------------------------------------------------------- #
    @staticmethod
    def _describe_intent(intent: Intent) -> str:
        return (
            f"genre={intent.genre} mood={intent.mood} "
            f"energy={intent.target_energy:.2f} acoustic={intent.likes_acoustic} "
            f"confidence={intent.confidence:.2f}"
        )

    @staticmethod
    def _describe_top(recommendations: List[Recommendation]) -> str:
        if not recommendations:
            return "no results"
        top = recommendations[0]
        return f"{top.song.title} ({top.song.genre}, {top.song.mood}) score {top.score:.2f}"
