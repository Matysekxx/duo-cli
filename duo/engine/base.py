"""
Base engine class with shared functionality for interactive and automated learning.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from ..challenges.parser import ChallengeParser
from ..config import get_preset_language
from ..models import Challenge, SessionResult


class BaseEngine(ABC):
    """Abstract base class for practice session runners."""

    def __init__(
        self,
        client: Any,
        lang_code: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.client = client
        self.dry_run = bool(dry_run)
        self.parser = ChallengeParser()
        self.lang_code = self._resolve_language(lang_code)
        self.hearts = 5
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.server_session: Optional[Dict[str, Any]] = None

    def _resolve_language(self, explicit_lang: Optional[str]) -> Optional[str]:
        """Resolve learning language: explicit flag > local preset > server active > enrolled course."""
        resolved = (
            explicit_lang
            or get_preset_language()
            or (self.client.get_learning_language() if hasattr(self.client, "get_learning_language") else None)
        )
        if not resolved and hasattr(self.client, "get_courses"):
            try:
                courses = self.client.get_courses()
                if courses:
                    resolved = courses[0].get("language")
            except Exception:
                pass
        return resolved.lower() if resolved else None

    def _refresh_hearts(self) -> int:
        """Fetch current hearts count from Duolingo server if authenticated."""
        if self.client and hasattr(self.client, "is_authenticated") and self.client.is_authenticated():
            try:
                h = self.client.get_hearts()
                if not h.get("is_unlimited") and isinstance(h.get("hearts"), int):
                    self.hearts = max(0, h["hearts"])
            except Exception:
                pass
        return self.hearts

    def _fetch_challenges(self) -> Tuple[Optional[Dict[str, Any]], List[Challenge]]:
        """Create practice session on server and parse challenges."""
        if not self.lang_code or not self.client or not hasattr(self.client, "create_practice_session"):
            return None, []

        server_session = self.client.create_practice_session(self.lang_code)
        raw_challenges = server_session.get("challenges", [])
        challenges: List[Challenge] = [self.parser.parse(ch) for ch in raw_challenges]
        return server_session, challenges

    def _submit_session(
        self,
        server_session: Dict[str, Any],
        score: int,
        start_time: float,
        total_challenges: int,
    ) -> SessionResult:
        """Submit practice session to Duolingo backend or handle dry-run."""
        if self.dry_run:
            return SessionResult(
                score=score,
                total=total_challenges,
                max_combo=self.max_combo,
                xp_gained=15,
                streak_extended=True,
                synced=False,
                details={"dry_run": True},
            )

        if not self.client or not hasattr(self.client, "submit_practice_session"):
            return SessionResult(score=score, total=total_challenges, max_combo=self.max_combo, xp_gained=0, synced=False)

        sync_res = self.client.submit_practice_session(
            server_session,
            score=score,
            start_time=start_time,
            hearts_left=self.hearts,
            mistakes=max(0, total_challenges - score),
            failed=self.hearts <= 0,
        )

        synced = bool(sync_res.get("serverSync"))
        xp_gain = sync_res.get("xpGain", 15) if synced else 0
        streak_ext = sync_res.get("streakExtended", True) if synced else False

        return SessionResult(
            score=score,
            total=total_challenges,
            max_combo=self.max_combo,
            xp_gained=xp_gain,
            streak_extended=streak_ext,
            synced=synced,
            details=sync_res,
        )

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """Execute the engine."""
        pass
