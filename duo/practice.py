"""
Backward-compatibility shim for duo.practice.
Real implementations live in the modular `duo.engine` and `duo.challenges` packages.
"""

from .challenges.normalizer import normalize_answer
from .challenges.types import (
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
from .engine.auto import AutoEngine as AutoPractice
from .engine.base import BaseEngine
from .engine.interactive import InteractiveEngine as PracticeSession
from .engine.timing import (
    AUTO_QUESTION_DELAY_MAX,
    AUTO_QUESTION_DELAY_MIN,
    AUTO_REST_MAX,
    AUTO_REST_MIN,
    HumanDelayCalculator,
    TimingConfig,
    _human_delay,
)

__all__ = [
    "BaseEngine",
    "PracticeSession",
    "AutoPractice",
    "TimingConfig",
    "HumanDelayCalculator",
    "normalize_answer",
    "AUTO_QUESTION_DELAY_MIN",
    "AUTO_QUESTION_DELAY_MAX",
    "AUTO_REST_MIN",
    "AUTO_REST_MAX",
    "_human_delay",
    "AUDIO_CHALLENGE_TYPES",
    "VISUAL_CHALLENGE_TYPES",
    "BUILD_SENTENCE_TYPES",
    "CLOZE_TYPES",
    "TYPE_COMPLETE_TYPES",
    "FREE_TEXT_FAMILY",
    "LANGUAGE_FLAGS",
    "TEXT_CHALLENGE_TYPES",
    "CHALLENGE_TYPES",
    "get_flag",
]
