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


class PipelineStatus(str, Enum):
    """Terminal state of a single trip through the orchestrator."""
    OK = "ok"
    BLOCKED = "blocked"          # guardrails rejected the input
    LOW_CONFIDENCE = "low_confidence"  # routed, but no usable taste signal


@dataclass
class PipelineResult:
    """Everything one request produces, ready to render or assert against."""
    status: PipelineStatus
    message: str
    intent: Optional[Intent] = None
    recommendations: List[Recommendation] = field(default_factory=list)
