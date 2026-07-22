"""Pipeline orchestrator.

Wires the agents into a single entry point: ``handle(text)`` takes a raw
free-text request and returns a structured :class:`PipelineResult`.

Phase A wires the three agents. Phase B inserts the guardrail check as the
first step, before any request reaches the routing agent.
"""

from typing import List

from .agents import ReasoningAgent, RetrievalAgent, RoutingAgent
from .guardrails import validate_input
from .models import PipelineResult, PipelineStatus, Song


class Orchestrator:
    def __init__(self, songs: List[Song]):
        self.songs = songs
        self.router = RoutingAgent(songs)
        self.retriever = RetrievalAgent(songs)
        self.reasoner = ReasoningAgent()
        # Catalog-derived vocabulary so bare genres/moods count as on-topic.
        self._known_terms = list(self.router.known_genres | self.router.known_moods)

    def handle(self, text: str, k: int = 5) -> PipelineResult:
        # 1. Guardrails: reject unsafe / off-topic input before anything else.
        guard = validate_input(text, known_terms=self._known_terms)
        if not guard.allowed:
            return PipelineResult(
                status=PipelineStatus.BLOCKED,
                message=guard.reason,
            )

        # 2. Routing agent: read the request into a structured intent.
        intent = self.router.route(text)
        if not intent.is_music_request:
            return PipelineResult(
                status=PipelineStatus.LOW_CONFIDENCE,
                message=(
                    "I couldn't find any music preferences in that request. "
                    "Try naming a genre, mood, or energy level."
                ),
                intent=intent,
            )

        recommendations = self.retriever.retrieve(intent, k=k)
        message = self.reasoner.explain(intent, recommendations)
        return PipelineResult(
            status=PipelineStatus.OK,
            message=message,
            intent=intent,
            recommendations=recommendations,
        )
