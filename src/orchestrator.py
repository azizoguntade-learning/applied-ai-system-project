"""Pipeline orchestrator.

Wires the agents into a single entry point: ``handle(text)`` takes a raw
free-text request and returns a structured :class:`PipelineResult`.

Phase A wires the three agents. Phase B inserts the guardrail check as the
first step, before any request reaches the routing agent.
"""

import logging
from typing import List

from .agents import ReasoningAgent, RetrievalAgent, RoutingAgent
from .guardrails import validate_input
from .models import PipelineResult, PipelineStatus, Song

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, songs: List[Song]):
        self.songs = songs
        self.router = RoutingAgent(songs)
        self.retriever = RetrievalAgent(songs)
        self.reasoner = ReasoningAgent()
        # Catalog-derived vocabulary so bare genres/moods count as on-topic.
        self._known_terms = list(self.router.known_genres | self.router.known_moods)

    def handle(self, text: str, k: int = 5) -> PipelineResult:
        logger.info("Request received: %r (k=%d)", text, k)

        # 1. Guardrails: reject unsafe / off-topic input before anything else.
        guard = validate_input(text, known_terms=self._known_terms)
        if not guard.allowed:
            logger.info("Pipeline result: BLOCKED (%s)", guard.category.value)
            return PipelineResult(
                status=PipelineStatus.BLOCKED,
                message=guard.reason,
            )

        # 2. Routing agent: read the request into a structured intent.
        intent = self.router.route(text)
        logger.debug(
            "Routed intent: genre=%s mood=%s energy=%.2f acoustic=%s confidence=%.2f",
            intent.genre, intent.mood, intent.target_energy,
            intent.likes_acoustic, intent.confidence,
        )
        if not intent.is_music_request:
            logger.info("Pipeline result: LOW_CONFIDENCE (no taste signal found)")
            return PipelineResult(
                status=PipelineStatus.LOW_CONFIDENCE,
                message=(
                    "I couldn't find any music preferences in that request. "
                    "Try naming a genre, mood, or energy level."
                ),
                intent=intent,
            )

        recommendations = self.retriever.retrieve(intent, k=k)
        top = recommendations[0] if recommendations else None
        logger.info(
            "Pipeline result: OK (%d recommendations, top=%s score=%.2f)",
            len(recommendations),
            top.song.title if top else "none",
            top.score if top else 0.0,
        )

        message = self.reasoner.explain(intent, recommendations)
        return PipelineResult(
            status=PipelineStatus.OK,
            message=message,
            intent=intent,
            recommendations=recommendations,
        )
