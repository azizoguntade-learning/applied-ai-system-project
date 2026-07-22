"""The agentic workflow.

Three small, single-responsibility agents make up the pipeline. Each is a plain
Python class (deterministic, no network calls) so the whole system runs offline
and is easy to unit-test:

- :class:`RoutingAgent`  -- reads a free-text request into a structured Intent.
- :class:`RetrievalAgent` -- searches/ranks the catalog for that Intent.
- :class:`ReasoningAgent` -- turns ranked results into a readable explanation.
"""

import re
from typing import Dict, List, Optional

from .models import Intent, Recommendation, Song
from .scoring import rank_songs

# Energy cue words -> a target_energy value on the 0..1 scale.
_HIGH_ENERGY_TERMS = {"high energy", "energetic", "upbeat", "hype", "intense",
                      "workout", "gym", "party", "pumped", "fast"}
_LOW_ENERGY_TERMS = {"low energy", "calm", "chill", "relaxed", "mellow",
                     "sleep", "study", "focus", "slow", "quiet"}

# Words that signal a preference for acoustic/unplugged material.
_ACOUSTIC_TERMS = {"acoustic", "unplugged", "organic", "live"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


class RoutingAgent:
    """Parses free text into an Intent using vocabulary from the catalog.

    Deriving the known genres/moods from the loaded songs (rather than a
    hardcoded list) means the router never drifts from the data it serves.
    """

    def __init__(self, songs: List[Song]):
        self.known_genres = {s.genre.lower() for s in songs}
        self.known_moods = {s.mood.lower() for s in songs}

    def route(self, text: str) -> Intent:
        normalized = _normalize(text)
        matched: List[str] = []

        genre = self._match_vocab(normalized, self.known_genres, matched)
        mood = self._match_vocab(normalized, self.known_moods, matched)
        target_energy, energy_matched = self._detect_energy(normalized)
        matched.extend(energy_matched)
        likes_acoustic = any(term in normalized for term in _ACOUSTIC_TERMS)
        if likes_acoustic:
            matched.append("acoustic")

        # Confidence scales with how many distinct taste signals we found.
        signals = sum(bool(x) for x in (genre, mood, energy_matched, likes_acoustic))
        confidence = min(1.0, signals / 3.0)

        return Intent(
            is_music_request=signals > 0,
            genre=genre,
            mood=mood,
            target_energy=target_energy,
            likes_acoustic=likes_acoustic,
            confidence=confidence,
            matched_terms=matched,
        )

    @staticmethod
    def _match_vocab(text: str, vocab: set, matched: List[str]) -> Optional[str]:
        """Return the first vocab term appearing as a whole word in ``text``.

        Multi-word genres (e.g. "indie pop") are checked before single words so
        the more specific match wins.
        """
        for term in sorted(vocab, key=len, reverse=True):
            if re.search(rf"\b{re.escape(term)}\b", text):
                matched.append(term)
                return term
        return None

    @staticmethod
    def _detect_energy(text: str) -> tuple:
        hits = [t for t in _HIGH_ENERGY_TERMS if t in text]
        lows = [t for t in _LOW_ENERGY_TERMS if t in text]
        if hits and not lows:
            return 0.9, hits
        if lows and not hits:
            return 0.2, lows
        # Mixed or no signal -> neutral midpoint.
        return 0.5, (hits + lows)


class RetrievalAgent:
    """Searches the catalog for songs matching an Intent."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def retrieve(self, intent: Intent, k: int = 5) -> List[Recommendation]:
        return rank_songs(intent.to_user_profile(), self.songs, k=k)


class ReasoningAgent:
    """Formats ranked recommendations into human-readable text."""

    def explain(self, intent: Intent, recommendations: List[Recommendation]) -> str:
        if not recommendations:
            return "No songs in the catalog to recommend."

        header = self._describe_intent(intent)
        lines = [header, ""]
        for i, rec in enumerate(recommendations, 1):
            song = rec.song
            lines.append(f"{i}. {song.title} — {song.artist} "
                         f"({song.genre}, {song.mood}) · score {rec.score:.2f}")
            lines.append(f"   Because: {', '.join(rec.reasons)}")
        return "\n".join(lines)

    @staticmethod
    def _describe_intent(intent: Intent) -> str:
        parts: Dict[str, Optional[str]] = {
            "genre": intent.genre,
            "mood": intent.mood,
        }
        described = [f"{key}={value}" for key, value in parts.items() if value]
        described.append(f"energy≈{intent.target_energy:.2f}")
        if intent.likes_acoustic:
            described.append("acoustic")
        return "Top picks for " + ", ".join(described) + ":"
