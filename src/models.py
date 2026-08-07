"""Core data structures shared across the recommender pipeline.

Keeping these in one place lets every agent (routing, retrieval, reasoning)
and the guardrails speak the same vocabulary without importing each other.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


@dataclass
class Song:
    """A single track in the catalog and its audio features."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """A user's explicit taste preferences.

    This is the structured form the retrieval/scoring layer consumes. The
    RoutingAgent produces an :class:`Intent` from free text and converts it
    into one of these.
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool = False


@dataclass
class Intent:
    """The RoutingAgent's structured reading of a free-text request.

    ``confidence`` is a rough 0..1 signal of how much music-taste information
    we could actually extract. A request like "play something" parses to a
    low-confidence intent; "high energy happy pop" is high-confidence.
    """
    is_music_request: bool
    genre: Optional[str] = None
    mood: Optional[str] = None
    target_energy: float = 0.5
    likes_acoustic: bool = False
    confidence: float = 0.0
    matched_terms: List[str] = field(default_factory=list)

    def to_user_profile(self) -> UserProfile:
        """Project the parsed intent onto the structured UserProfile."""
        return UserProfile(
            favorite_genre=self.genre or "",
            favorite_mood=self.mood or "",
            target_energy=self.target_energy,
            likes_acoustic=self.likes_acoustic,
        )


@dataclass
class Recommendation:
    """A scored song plus the human-readable reasons it was chosen."""
    song: Song
    score: float
    reasons: List[str]


@dataclass
class CriticVerdict:
    """The CriticAgent's judgement of a set of recommendations.

    ``issues`` is empty exactly when ``ok`` is True. ``relaxation`` names the
    single constraint the critic thinks is worth dropping on a retry, or None
    when it sees no repair worth attempting.
    """
    ok: bool
    issues: List[str] = field(default_factory=list)
    relaxation: Optional[str] = None


@dataclass
class TraceStep:
    """One recorded step of a request's journey through the pipeline.

    Collected into ``PipelineResult.trace`` and written to logs/traces.jsonl,
    so the agent's plan -> act -> check reasoning can be inspected after the
    fact rather than taken on trust.
    """
    agent: str
    action: str
    detail: str

    def to_dict(self) -> dict:
        return {"agent": self.agent, "action": self.action, "detail": self.detail}


class PipelineStatus(str, Enum):
    """Terminal state of a single trip through the orchestrator."""
    OK = "ok"
    BLOCKED = "blocked"          # guardrails rejected the input
    LOW_CONFIDENCE = "low_confidence"  # routed, but no usable taste signal


@dataclass
class PipelineResult:
    """Everything one request produces, ready to render or assert against.

    ``repaired`` is a flag rather than a new :class:`PipelineStatus` member on
    purpose: a repaired result is still a successful one, and existing callers
    asserting ``status == PipelineStatus.OK`` keep working unchanged.
    """
    status: PipelineStatus
    message: str
    intent: Optional[Intent] = None
    recommendations: List[Recommendation] = field(default_factory=list)
    trace: List[TraceStep] = field(default_factory=list)
    repaired: bool = False

    #: The critic's verdict on the recommendations actually returned. After a
    #: successful repair this is the verdict on the *repaired* set, so it is
    #: usually clean -- use ``critic_flagged`` to ask whether the check step
    #: ever objected.
    critic: Optional[CriticVerdict] = None

    #: True when the critic's *first* look found at least one issue, whether or
    #: not a repair followed. This is the honest measure of how often the check
    #: step earns its place; ``critic`` alone would report zero flags on every
    #: successfully repaired request.
    critic_flagged: bool = False
