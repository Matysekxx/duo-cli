"""
Core data models for duo-cli using typed dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Challenge:
    """Represents a normalized Duolingo challenge."""
    type: str
    prompt: str
    answer: str
    solutions: List[str] = field(default_factory=list)
    choices: List[str] = field(default_factory=list)
    word_bank: List[str] = field(default_factory=list)
    pair_tuples: List[Tuple[str, str]] = field(default_factory=list)
    pairs: List[str] = field(default_factory=list)
    correct_index: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_visual(self) -> bool:
        from .challenges.types import VISUAL_CHALLENGE_TYPES
        return self.type in VISUAL_CHALLENGE_TYPES

    @property
    def is_audio(self) -> bool:
        from .challenges.types import AUDIO_CHALLENGE_TYPES
        return self.type in AUDIO_CHALLENGE_TYPES

    @property
    def is_renderable(self) -> bool:
        """Return True if this challenge can be rendered meaningfully in the terminal."""
        return bool(
            (self.prompt and self.prompt.strip())
            or self.choices
            or self.word_bank
            or self.pair_tuples
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to legacy dictionary format for backward compatibility."""
        return {
            "type": self.type,
            "prompt": self.prompt,
            "choices": self.choices,
            "pairs": self.pairs,
            "pair_tuples": self.pair_tuples,
            "word_bank": self.word_bank,
            "answer": self.answer,
            "solutions": self.solutions,
            "raw": self.raw,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Challenge:
        """Create a Challenge instance from a dictionary."""
        return cls(
            type=data.get("type", "unknown"),
            prompt=data.get("prompt", ""),
            answer=data.get("answer", "OK"),
            solutions=data.get("solutions", []),
            choices=data.get("choices", []),
            word_bank=data.get("word_bank", []),
            pair_tuples=data.get("pair_tuples", []),
            pairs=data.get("pairs", []),
            correct_index=data.get("correct_index"),
            raw=data.get("raw", {}),
        )


@dataclass
class SessionResult:
    """Result of an executed practice session."""
    score: int
    total: int
    max_combo: int = 0
    xp_gained: int = 0
    streak_extended: bool = False
    synced: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimingConfig:
    """Configuration for question delays and inter-session pauses in auto practice."""
    question_delay_min: float = 0.8
    question_delay_max: float = 1.6
    rest_min: float = 25.0
    rest_max: float = 35.0


@dataclass
class Course:
    """Represents a Duolingo language course."""
    title: str
    language: str
    from_language: str
    xp: int
    is_active: bool = False
    crowns: int = 0


@dataclass
class UserProfile:
    """Duolingo user profile details."""
    username: str
    name: Optional[str] = None
    streak: int = 0
    total_xp: int = 0
    learning_language: Optional[str] = None
    from_language: Optional[str] = None
    created_at: Optional[str] = None
    bio: Optional[str] = None
    gems: int = 0
    has_plus: bool = False
