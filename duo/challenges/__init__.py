"""
Challenges package for duo-cli.
"""

from .types import (
    AUDIO_CHALLENGE_TYPES,
    BUILD_SENTENCE_TYPES,
    CHALLENGE_TYPES,
    CLOZE_TYPES,
    FREE_TEXT_FAMILY,
    LANGUAGE_FLAGS,
    TEXT_CHALLENGE_TYPES,
    TYPE_COMPLETE_TYPES,
    VISUAL_CHALLENGE_TYPES,
    get_flag,
)
from .normalizer import normalize_answer
from .parser import ChallengeParser, extract_challenge_solution

__all__ = [
    "AUDIO_CHALLENGE_TYPES",
    "BUILD_SENTENCE_TYPES",
    "CHALLENGE_TYPES",
    "CLOZE_TYPES",
    "FREE_TEXT_FAMILY",
    "LANGUAGE_FLAGS",
    "TEXT_CHALLENGE_TYPES",
    "TYPE_COMPLETE_TYPES",
    "VISUAL_CHALLENGE_TYPES",
    "get_flag",
    "normalize_answer",
    "ChallengeParser",
    "extract_challenge_solution",
]
