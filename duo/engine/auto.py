"""
Automated practice solver bot with natural human-like delays and progress feedback.
"""

import random
import time
from typing import Any, Dict, Optional
from ..challenges.types import AUDIO_CHALLENGE_TYPES, VISUAL_CHALLENGE_TYPES
from ..models import TimingConfig
from ..ui import (
    console,
    print_error,
    print_warning,
    render_auto_challenge,
    render_auto_header,
    render_auto_session_result,
    render_auto_summary,
)
from .base import BaseEngine
from .timing import HumanDelayCalculator


class AutoEngine(BaseEngine):
    """Automated Practice Solver Engine with realistic human pacing."""

    # Default timing attributes for backward compatibility
    QUESTION_DELAY_MIN = 0.8
    QUESTION_DELAY_MAX = 1.6
    REST_MIN = 25.0
    REST_MAX = 35.0

    def __init__(
        self,
        client: Any,
        lang_code: Optional[str] = None,
        max_sessions: Optional[int] = None,
        dry_run: bool = False,
        timing_config: Optional[TimingConfig] = None,
    ):
        super().__init__(client=client, lang_code=lang_code, dry_run=dry_run)
        self.max_sessions = max_sessions
        self.timing_config = timing_config or TimingConfig(
            question_delay_min=self.QUESTION_DELAY_MIN,
            question_delay_max=self.QUESTION_DELAY_MAX,
            rest_min=self.REST_MIN,
            rest_max=self.REST_MAX,
        )
        self.delay_calculator = HumanDelayCalculator(self.timing_config)
        self.delay_min = self.timing_config.question_delay_min
        self.delay_max = self.timing_config.question_delay_max
        self.rest_min = self.timing_config.rest_min
        self.rest_max = self.timing_config.rest_max

    def run(
        self,
        sessions: Optional[int] = 1,
        target_xp: Optional[int] = None,
        until_goal: bool = False,
        loop: bool = False,
    ) -> None:
        """Run automated practice sessions.
        
        If sessions is None and no stopping criteria are set, or if loop=True,
        runs continuously until stopped by the user (Ctrl+C) or max_sessions cap.
        """
        if not self.lang_code:
            print_error("No target language specified. Use -l (e.g. duo auto -l en) or run 'duo switch <lang>' first.")
            return

        # Fetch initial streak and daily goal info
        initial_streak = 0
        streak_extended = False
        daily_goal = 20
        initial_xp_today = 0

        if self.client and hasattr(self.client, "is_authenticated") and self.client.is_authenticated():
            try:
                info = self.client.get_streak_info()
                initial_streak = info.get("site_streak", 0)
                streak_extended = info.get("streak_extended_today", False)
                daily_goal = info.get("daily_goal", 20)
                initial_xp_today = info.get("xp_today", 0)
            except Exception:
                pass

        # Determine if continuous mode is active
        is_continuous = loop or (sessions is None and not target_xp and not until_goal)
        effective_sessions = sessions if not is_continuous else None

        render_auto_header(
            lang=self.lang_code,
            sessions=effective_sessions,
            target_xp=target_xp,
            until_goal=until_goal,
            loop=is_continuous,
            max_sessions=self.max_sessions,
        )

        sessions_completed = 0
        total_xp_earned = 0
        session_num = 0

        try:
            while True:
                # Stopping conditions
                if self.max_sessions and sessions_completed >= self.max_sessions:
                    console.print(f"\n[bold yellow]Reached max session cap ({self.max_sessions}). Stopping.[/]")
                    break

                if not is_continuous:
                    if until_goal and (initial_xp_today + total_xp_earned) >= daily_goal:
                        console.print(f"\n[bold bright_green]🎯 Daily goal of {daily_goal} XP reached! (+{total_xp_earned} XP today)[/]")
                        break
                    elif target_xp and total_xp_earned >= target_xp:
                        console.print(f"\n[bold bright_green]🎯 Target of {target_xp} XP reached! (+{total_xp_earned} XP earned)[/]")
                        break
                    elif effective_sessions is not None and sessions_completed >= effective_sessions:
                        break

                session_num += 1

                # Create practice session on server
                server_sess = None
                challenges = []
                backoff = 3.0

                for attempt in range(1, 4):
                    try:
                        if self.dry_run or not self.client or not hasattr(self.client, "is_authenticated") or not self.client.is_authenticated():
                            challenges = [
                                self.parser.parse({"type": "translate", "prompt": "Mock question", "answer": "Mock answer"}),
                                self.parser.parse({"type": "select", "prompt": "Mock question 2", "choices": ["A", "B"], "correctIndex": 0}),
                            ]
                            server_sess = {"id": "mock_session", "learningLanguage": self.lang_code}
                            break
                        else:
                            server_sess, challenges = self._fetch_challenges()
                            if challenges:
                                break
                    except Exception as e:
                        if attempt == 3:
                            print_error(f"Failed to create session after 3 attempts: {e}")
                            return
                        print_warning(f"Session creation failed ({e}) — waiting {backoff:.0f}s before retry...")
                        time.sleep(backoff)
                        backoff *= 2.0

                if not challenges:
                    print_error("No challenges received from server. Aborting.")
                    break

                session_start_time = time.time()
                total_q = len(challenges)
                score = 0

                # Solve questions one by one
                for q_idx, ch in enumerate(challenges, 1):
                    prompt = ch.prompt or f"Question {q_idx}"
                    answer = ch.answer or "OK"
                    ctype = ch.type

                    # Audio/visual fast path
                    if ctype in AUDIO_CHALLENGE_TYPES or ctype in VISUAL_CHALLENGE_TYPES:
                        pause = random.uniform(0.5, 0.9)
                    else:
                        pause = self.delay_calculator.question_delay(prompt, ctype)

                    render_auto_challenge(
                        session_idx=session_num,
                        total_sessions=self.max_sessions if (self.max_sessions and is_continuous) else (0 if is_continuous else (effective_sessions or 0)),
                        q_idx=q_idx,
                        total_q=total_q,
                        prompt=prompt,
                        answer=answer,
                        delay=pause,
                    )
                    time.sleep(pause)
                    score += 1

                # Submit session result
                res = self._submit_session(server_sess or {}, score, session_start_time, total_q)
                if res.synced or self.dry_run:
                    total_xp_earned += res.xp_gained
                    sessions_completed += 1
                    if res.streak_extended:
                        streak_extended = True
                    render_auto_session_result(
                        session_idx=session_num,
                        xp_gained=res.xp_gained,
                        streak_extended=streak_extended,
                        total_xp_earned=total_xp_earned,
                    )
                else:
                    print_warning(f"Session submission status: {res.details}")

                # Check if another session should follow
                should_continue = True
                if self.max_sessions and sessions_completed >= self.max_sessions:
                    should_continue = False
                elif not is_continuous:
                    if until_goal and (initial_xp_today + total_xp_earned) >= daily_goal:
                        should_continue = False
                    elif target_xp and total_xp_earned >= target_xp:
                        should_continue = False
                    elif effective_sessions is not None and sessions_completed >= effective_sessions:
                        should_continue = False

                if should_continue:
                    rest_duration = self.delay_calculator.rest_delay()
                    console.print(f"[dim]⏳ Resting for {rest_duration:.0f}s before next session...[/]\n")
                    self.delay_calculator.sleep_with_progress(rest_duration, description="Next session in")

        except KeyboardInterrupt:
            console.print("\n[bold bright_yellow]⚠ Auto practice paused by user (Ctrl+C).[/]")

        # Fetch final streak status
        final_streak = initial_streak
        try:
            if self.client and hasattr(self.client, "get_streak_info"):
                final_info = self.client.get_streak_info(force_refresh=True)
                final_streak = final_info.get("site_streak", initial_streak)
        except Exception:
            pass

        render_auto_summary(
            sessions_completed=sessions_completed,
            total_xp=total_xp_earned,
            streak_days=final_streak,
            streak_extended=streak_extended,
        )


# Backward compatibility alias
AutoPractice = AutoEngine
