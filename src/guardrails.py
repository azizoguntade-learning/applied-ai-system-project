"""Input guardrails.

A cheap, deterministic first line of defense that runs *before* the agentic
pipeline. It catches two classes of unwanted input:

1. Prompt injection -- attempts to override instructions or exfiltrate the
   system prompt (e.g. "ignore previous instructions").
2. Off-topic requests -- input with no music-taste signal that instead looks
   like a different task (e.g. "give me a recipe").

Rule-based on purpose: fast, free, offline, and easy to unit-test. It is not a
complete defense, but it stops the obvious cases from reaching the router.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)

# Cap input length to avoid pathological / abusive payloads.
MAX_INPUT_LENGTH = 500

# Injection / jailbreak phrases. Matched as substrings on normalized text.
_INJECTION_PATTERNS = [
    r"ignore (all |the |your )?(previous|prior|above|earlier) (instructions|prompts?|rules)",
    r"disregard (all |the |your )?(previous|prior|above) (instructions|prompts?)",
    r"forget (all |everything|your) (previous|prior|above|instructions)",
    r"(reveal|show|print|repeat|leak) (me )?(your |the )?(system )?(prompt|instructions)",
    r"you are now",
    r"act as (a |an )?(?!.*\b(dj|listener)\b)",  # role-override, but allow musical roles
    r"pretend (to be|you are)",
    r"new instructions?:",
    r"</?(system|assistant|user)>",  # fake role tags
    r"jailbreak",
    r"developer mode",
]

# Words that strongly signal a *non-music* task. Used only to classify input
# that already lacks any music signal, so it won't reject valid music requests.
_OFF_TOPIC_TERMS = {
    "recipe", "cook", "cooking", "bake", "weather", "forecast", "stock",
    "invest", "translate", "essay", "homework", "code", "python", "javascript",
    "sql", "email", "resume", "medical", "diagnose", "lawyer", "legal",
    "directions", "flight", "hotel", "news", "sports score", "capital of",
}

# Generic music vocabulary that signals the request is at least on-topic even
# when it names no specific genre/mood (those are checked by the RoutingAgent).
_MUSIC_TERMS = {
    "song", "songs", "music", "track", "tracks", "playlist", "tune", "tunes",
    "artist", "album", "listen", "recommend", "recommendation", "vibe", "beat",
    "genre", "mood", "energy", "acoustic", "dance", "sing",
}


class GuardrailCategory(str, Enum):
    CLEAN = "clean"
    EMPTY = "empty"
    TOO_LONG = "too_long"
    INJECTION = "injection"
    OFF_TOPIC = "off_topic"


@dataclass
class GuardrailResult:
    allowed: bool
    category: GuardrailCategory
    reason: str
    matched: Optional[str] = None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _contains_any(text: str, terms) -> Optional[str]:
    for term in terms:
        if re.search(rf"\b{re.escape(term)}\b", text):
            return term
    return None


def validate_input(text: str, known_terms: Optional[List[str]] = None) -> GuardrailResult:
    """Validate raw user input before it reaches the pipeline.

    ``known_terms`` are catalog-derived taste words (genres/moods). Passing them
    lets a bare genre like "reggae" count as on-topic even though it isn't in
    the generic music vocabulary.
    """
    if text is None or not text.strip():
        logger.info("Guardrail BLOCK [empty]")
        return GuardrailResult(
            allowed=False,
            category=GuardrailCategory.EMPTY,
            reason="Empty request. Tell me a genre, mood, or energy level.",
        )

    if len(text) > MAX_INPUT_LENGTH:
        logger.info("Guardrail BLOCK [too_long] %d chars (limit %d)", len(text), MAX_INPUT_LENGTH)
        return GuardrailResult(
            allowed=False,
            category=GuardrailCategory.TOO_LONG,
            reason=f"Request too long (>{MAX_INPUT_LENGTH} chars).",
        )

    normalized = _normalize(text)

    # 1. Prompt injection -- checked first; it's the most severe.
    for pattern in _INJECTION_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            logger.info("Guardrail BLOCK [injection] matched %r", match.group(0))
            return GuardrailResult(
                allowed=False,
                category=GuardrailCategory.INJECTION,
                reason="This looks like a prompt-injection attempt. "
                       "I only help with music recommendations.",
                matched=match.group(0),
            )

    # 2. Off-topic -- only reject when there is a non-music task signal AND no
    #    music signal at all, so genuine music requests are never blocked.
    taste_vocab = set(_MUSIC_TERMS)
    if known_terms:
        taste_vocab.update(t.lower() for t in known_terms)

    off_topic_hit = _contains_any(normalized, _OFF_TOPIC_TERMS)
    music_hit = _contains_any(normalized, taste_vocab)
    if off_topic_hit and not music_hit:
        logger.info("Guardrail BLOCK [off_topic] matched %r", off_topic_hit)
        return GuardrailResult(
            allowed=False,
            category=GuardrailCategory.OFF_TOPIC,
            reason="That looks off-topic. I only recommend music — "
                   "try naming a genre, mood, or energy level.",
            matched=off_topic_hit,
        )

    logger.debug("Guardrail PASS [clean]")
    return GuardrailResult(
        allowed=True,
        category=GuardrailCategory.CLEAN,
        reason="ok",
    )
