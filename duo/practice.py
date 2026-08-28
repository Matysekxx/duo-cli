"""
Interactive Practice and Automated Solver Engine with live Duolingo Server Sync (XP & Streak).
"""

import random
import time
from typing import Any, Dict, List, Optional
from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn
from rich.prompt import Prompt

from .api import AUDIO_CHALLENGE_TYPES, DuoAPIError, DuoClient, extract_challenge_solution, get_flag
from .config import get_preset_language

# ---------------------------------------------------------------------------
# Practice constants — single source of truth, easy to tune/extend
# ---------------------------------------------------------------------------

# Types whose answer depends on images / glyph drawing that a terminal cannot
# present. They are auto-completed in the interactive session.
VISUAL_CHALLENGE_TYPES = {
    "radioImageSelect",
    "characterIntro",
    "characterMatch",
    "characterPuzzle",
    "characterSelect",
    "characterTrace",
    "characterWrite",
    "svgPuzzle",
}

# Auto mode timing — base range (tuned for fast execution)
AUTO_QUESTION_DELAY_MIN = 0.4
AUTO_QUESTION_DELAY_MAX = 0.8
AUTO_REST_MIN = 3.0
AUTO_REST_MAX = 8.0

# Per-type multipliers: tasks requiring reading/writing take longer,
# single-choice tasks are faster. Tuned so average with base 0.5-1.0s lands
# around 1.2-2.2s with prompt-length bonus.
_TYPE_DELAY_MULTIPLIER = {
    "translate": 1.7,
    "completeReverseTranslation": 1.6,
    "typeCloze": 1.5,
    "typeClozeTable": 1.5,
    "typeComplete": 1.4,
    "typeCompleteTable": 1.4,
    "tapComplete": 1.3,
    "tapCompleteTable": 1.3,
    "patternTapComplete": 1.3,
    "tapCloze": 1.2,
    "tapClozeTable": 1.2,
    "gapFill": 1.2,
    "orderTapComplete": 1.3,
    "syllableTap": 1.1,
    "match": 1.4,
    "assist": 0.9,
    "select": 0.9,
    "characterSelect": 0.9,
    "radioSelect": 0.9,
    "judge": 0.9,
}


def _human_delay(
    base_min: float,
    base_max: float,
    prompt: str = "",
    ctype: str = "",
) -> float:
    """Compute human-like per-question pause.

    - Starts from uniform(base_min, base_max).
    - Applies per-type multiplier (harder types = longer).
    - Adds prompt-length bonus (~0.008s per char, capped at 1.25s) to simulate
      reading time.
    - Adds small Gaussian jitter for natural variance.
    """
    base = random.uniform(base_min, base_max)
    mult = _TYPE_DELAY_MULTIPLIER.get(ctype, 1.0)
    pause = base * mult
    if prompt:
        pause += min(len(prompt) * 0.008, 1.25)
    pause += random.gauss(0, 0.09)
    return max(0.4, min(pause, 4.0))
from .ui import (
    DIVIDER_LINE,
    console,
    print_error,
    print_warning,
    render_answer_result,
    render_auto_challenge,
    render_auto_header,
    render_auto_session_result,
    render_auto_summary,
    render_build_card,
    render_freeform_card,
    render_match_panel,
    render_question_card,
)


def normalize_answer(text: str) -> str:
    clean = text.lower().strip()
    for char in [".", ",", "!", "?", "'", '"', "¿", "¡", ":", ";", "-", "–"]:
        clean = clean.replace(char, " ")
    return " ".join(clean.split())


class PracticeSession:
    """Interactive practice engine for manual terminal learning."""

    def __init__(self, client: DuoClient, lang_code: Optional[str] = None, dry_run: bool = False):
        self.client = client
        # Resolution order: explicit -l flag > local preset > server active course > first enrolled course
        resolved = (
            lang_code
            or get_preset_language()
            or client.get_learning_language()
        )
        if not resolved:
            try:
                courses = client.get_courses()
                if courses:
                    resolved = courses[0].get("language")
            except Exception:
                pass
        self.lang_code = resolved.lower() if resolved else None
        self.score = 0
        self.hearts = 5
        self.combo = 0
        self.max_combo = 0
        self.server_session = None
        self.dry_run = bool(dry_run)

    def run(self) -> None:
        if not self.lang_code:
            print_error(
                "No target language set. Please specify a language code with '-l <code>' "
                "(e.g. duo practice -l en) or set it with 'duo switch <lang>'."
            )
            return
        console.clear()
        session_start_time = time.time()

        # Try initializing session on Duolingo servers
        live_challenges = []
        if self.client.is_authenticated():
            try:
                self.server_session = self.client.create_practice_session(self.lang_code)
                raw_chs = self.server_session.get("challenges", [])
                for ch in raw_chs:
                    details = extract_challenge_solution(ch)
                    live_challenges.append(details)
            except Exception as e:
                self.server_session = None

        if live_challenges:
            questions = live_challenges
        else:
            print_warning(
                "No practice questions available. Run 'duo login' to fetch live "
                "Duolingo challenges for your course."
            )
            return

        # Reflect the user's REAL heart count from the server instead of a
        # hardcoded local value, so we never silently refill or overstate it.
        if self.client.is_authenticated():
            try:
                h = self.client.get_hearts()
                if not h.get("is_unlimited") and isinstance(h.get("hearts"), int):
                    self.hearts = max(0, h["hearts"])
            except Exception:
                pass

        console.print()
        console.print("[bold bright_green]🦉 DUOLINGO PRACTICE SESSION[/]")
        console.print(f"[dim green]{DIVIDER_LINE}[/]")
        console.print(f"  Language  : [bold bright_cyan]{self.lang_code.upper()}[/] | Questions: [bold yellow]{len(questions)}[/] | Hearts: [bold red]{self.hearts}/5[/]")
        console.print(f"  User      : [bold bright_white]@{self.client.username or 'guest'}[/]")
        console.print()
        console.print("  [dim]How to play:[/]")
        console.print("    • [white]Multiple choice[/] → type the [bold yellow]number[/] of your answer")
        console.print("    • [white]Translate[/] → type the translation")
        console.print("    • [white]Build sentence[/] → type word [bold yellow]numbers[/] in order (e.g. [yellow]3 1 4 2[/]) or the sentence")
        console.print("    • [white]exit[/] to quit the session")
        console.print(f"[dim green]{DIVIDER_LINE}[/]\n")

        for idx, q in enumerate(questions, 1):
            # Compact inline progress bar shown before each question
            done = idx - 1
            total_q = len(questions)
            bar_filled = int((done / total_q) * 20) if total_q else 0
            bar_str = "[bold bright_green]" + "█" * bar_filled + "[/][dim]" + "░" * (20 - bar_filled) + "[/]"
            console.print(f"\n  {bar_str}  [dim]{done}/{total_q} done[/]")

            if self.hearts <= 0:
                console.print("\n[bold bright_red]💔 You ran out of hearts! Practice session ended.[/]\n")
                break

            q_type = q.get("type", "")
            if q_type in VISUAL_CHALLENGE_TYPES:
                console.print(f"\n[dim yellow]🖼️ Visual exercise ('{q_type}') can't be shown in terminal. Auto-completed! ✔[/dim yellow]")
                self.score += 1
                time.sleep(0.15)
                continue

            prompt_text = q.get("prompt", "")
            correct_raw = q.get("answer", "")
            solutions = [normalize_answer(s) for s in q.get("solutions", [])] if q.get("solutions") else [normalize_answer(correct_raw)]

            pair_tuples = q.get("pair_tuples", [])
            choices = q.get("choices", [])
            word_bank = q.get("word_bank", [])

            # Skip challenges we cannot render (no prompt and no options to
            # show) so a session never presents a blank/confusing question.
            renderable = bool(prompt_text and prompt_text.strip()) or choices or word_bank or pair_tuples
            if not renderable:
                console.print(
                    f"\n[dim yellow]⏭ Unsupported challenge ('{q_type}') "
                    f"can't be shown in terminal. Skipped![/dim yellow]"
                )
                self.score += 1
                time.sleep(0.15)
                continue

            if word_bank:
                render_build_card(idx, len(questions), prompt_text, word_bank, self.hearts, self.combo, self.lang_code, q_type)

                user_input = Prompt.ask(f"\n[bold bright_green]Your sentence[/]").strip()
                if user_input.lower() in ["exit", "quit", "q"]:
                    break

                # Accept either an ordered list of word numbers or a typed sentence
                parts = user_input.split()
                if parts and all(p.isdigit() for p in parts):
                    picked_words = [
                        word_bank[int(p) - 1]
                        for p in parts
                        if p.isdigit() and 1 <= int(p) <= len(word_bank)
                    ]
                    constructed = " ".join(picked_words)
                else:
                    constructed = user_input

                is_correct = (
                    normalize_answer(constructed) in solutions
                    or normalize_answer(constructed) == normalize_answer(correct_raw)
                )
            elif pair_tuples and len(pair_tuples) > 1:
                remaining_right = [p[1] for p in pair_tuples]
                random.shuffle(remaining_right)

                matched_all = True
                for p_idx, (lw, tr) in enumerate(pair_tuples, 1):
                    if len(remaining_right) == 1:
                        console.print(f"\n  [bold bright_white]•[/] [bold bright_yellow]{lw}[/] ⇄ [bold bright_green]{remaining_right[0]}[/] [dim](Auto-matched)[/dim]")
                        break

                    render_match_panel(lw, remaining_right, p_idx, len(pair_tuples), self.hearts, self.combo, self.lang_code)

                    ans = Prompt.ask(f"    [bold bright_green]Choice (1-{len(remaining_right)})[/]").strip()
                    if ans.lower() in ["exit", "quit", "q"]:
                        return

                    picked = None
                    if ans.isdigit() and 1 <= int(ans) <= len(remaining_right):
                        picked = remaining_right[int(ans) - 1]
                    else:
                        picked = ans.strip()

                    if picked and picked.lower() == tr.lower():
                        console.print(f"    [bold bright_green]✔ Correct![/] {lw} ⇄ {tr}")
                        if picked in remaining_right:
                            remaining_right.remove(picked)
                    else:
                        console.print(f"    [bold bright_red]✖ Incorrect![/] {lw} ⇄ [bold green]{tr}[/]")
                        matched_all = False
                        if tr in remaining_right:
                            remaining_right.remove(tr)

                is_correct = matched_all
            else:
                shuffled_choices = list(choices)
                if shuffled_choices:
                    render_question_card(idx, len(questions), prompt_text, shuffled_choices, self.hearts, self.combo, self.lang_code, q_type)
                else:
                    render_freeform_card(idx, len(questions), prompt_text, self.hearts, self.combo, self.lang_code, q_type)

                prompt_str = f"[bold bright_green]Your answer (1-{len(shuffled_choices)})[/]" if shuffled_choices else "[bold bright_green]Your answer[/]"
                user_input = Prompt.ask(f"\n{prompt_str}").strip()
                if user_input.lower() in ["exit", "quit", "q"]:
                    break

                is_correct = False
                if user_input.isdigit() and shuffled_choices and 1 <= int(user_input) <= len(shuffled_choices):
                    picked_choice = normalize_answer(shuffled_choices[int(user_input) - 1])
                    is_correct = picked_choice in solutions or picked_choice == normalize_answer(correct_raw)
                else:
                    norm_in = normalize_answer(user_input)
                    is_correct = norm_in in solutions or norm_in == normalize_answer(correct_raw)

            if is_correct:
                self.score += 1
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                render_answer_result(True, correct_raw)
            else:
                self.hearts = max(0, self.hearts - 1)
                self.combo = 0
                display_ans = correct_raw or ((q.get("solutions") or [""])[0])
                if pair_tuples:
                    console.print(f"\n[bold bright_red]✖ Some pairs were incorrect! Lost a heart (Remaining: {self.hearts}/5)[/]")
                else:
                    render_answer_result(False, display_ans)
            time.sleep(0.2)

        # Submit results to Duolingo backend if possible
        sync_status = ""
        if self.dry_run:
            sync_status = "[bold bright_yellow]⚡ Dry run — not submitted to server.[/]"
        elif self.client.is_authenticated() and self.score > 0:
            console.print("\n[bold cyan]⏳ Submitting session to Duolingo servers...[/]")
            session_to_submit = self.server_session or {"id": "dummy", "learningLanguage": self.lang_code}
            sync_res = self.client.submit_practice_session(
                session_to_submit,
                self.score,
                start_time=session_start_time,
                hearts_left=self.hearts,
                mistakes=max(0, len(questions) - self.score),
                failed=self.hearts <= 0,
            )

            if sync_res.get("serverSync"):
                earned_xp = sync_res.get("xpGain", self.score * 10)
                sync_status = f"[bold bright_green]✔ Server Sync: +{earned_xp} XP Earned (Streak Maintained! 🔥)[/]"
            else:
                sync_status = "[bold yellow]ℹ Completed locally (+50 XP).[/]"
        else:
            sync_status = "[dim]Session finished in offline mode.[/]"

        console.print()
        console.print("[bold bright_green]📊 PRACTICE RESULTS[/]")
        console.print(f"[dim green]{DIVIDER_LINE}[/]")
        console.print(f"  Score         : [bold bright_green]{self.score} / {len(questions)}[/]")
        console.print(f"  Highest Combo : [bold bright_yellow]🔥 {self.max_combo}[/]")
        console.print(f"  Result        : {sync_status}")
        console.print(f"[dim green]{DIVIDER_LINE}[/]\n")


class AutoPractice:
    """Automated Practice Solver Engine with human-like delays."""



    # Re-export constants for easy external tuning / testing
    QUESTION_DELAY_MIN = AUTO_QUESTION_DELAY_MIN
    QUESTION_DELAY_MAX = AUTO_QUESTION_DELAY_MAX
    REST_MIN = AUTO_REST_MIN
    REST_MAX = AUTO_REST_MAX

    def __init__(
        self,
        client: DuoClient,
        lang_code: Optional[str] = None,
        max_sessions: Optional[int] = None,
        dry_run: bool = False,
    ):
        self.client = client
        self.lang_code = lang_code
        self.max_sessions = max_sessions
        self.dry_run = bool(dry_run)
        self.hearts = 5
        self.delay_min = self.QUESTION_DELAY_MIN
        self.delay_max = self.QUESTION_DELAY_MAX
        self.rest_min = self.REST_MIN
        self.rest_max = self.REST_MAX

    def run(
        self,
        sessions: int = 1,
        target_xp: Optional[int] = None,
        until_goal: bool = False,
        loop: bool = False,
    ) -> None:
        if not self.client.is_authenticated():
            print_error("Automated practice requires authentication. Run 'duo login' first.")
            return

        # -L runs unbounded (user's explicit choice). It is ban-prone, so we
        # keep the warning but no longer force a cap; use -m to set your own.
        if loop and not self.max_sessions:
            print_warning(
                "[bold yellow]⚠ Running forever (-L) is ban-prone and may get the account "
                "flagged. Consider -m/--max-sessions to set a safe limit.[/]"
            )

        # Fetch initial user status
        try:
            user_info = self.client.verify_auth()
            streak_info = self.client.get_streak_info()
            if not self.lang_code:
                self.lang_code = (
                    get_preset_language()
                    or user_info.get("learningLanguage")
                )
                if not self.lang_code:
                    try:
                        courses = self.client.get_courses()
                        if courses:
                            self.lang_code = courses[0].get("language")
                    except Exception:
                        pass
                if not self.lang_code:
                    print_error(
                        "No learning language found on your account. "
                        "Please specify one with '-l <code>' (e.g. duo auto -l en) or set it with 'duo switch <lang>'."
                    )
                    return
                self.lang_code = self.lang_code.lower()
        except Exception as e:
            print_error(f"Failed to connect to Duolingo: {e}")
            return

        initial_xp_today = streak_info.get("xp_today", 0)
        daily_goal = streak_info.get("daily_goal", 10)
        current_streak = streak_info.get("site_streak", 0)

        render_auto_header(self.lang_code, sessions, target_xp, until_goal, loop)

        total_xp_earned = 0
        sessions_completed = 0
        streak_extended = streak_info.get("streak_extended_today", False)

        try:
            session_num = 0
            while True:
                session_num += 1
                # Hard stop for the safety cap (even in loop mode)
                if self.max_sessions and sessions_completed >= self.max_sessions:
                    console.print(
                        f"[bold bright_green]🛑 Reached session limit ({self.max_sessions}). Stopping.[/]\n"
                    )
                    break
                # Check stopping conditions (loop mode never stops on its own)
                if not loop:
                    if until_goal and (initial_xp_today + total_xp_earned) >= daily_goal:
                        console.print(f"[bold bright_green]🎯 Daily goal of {daily_goal} XP reached![/]\n")
                        break
                    if target_xp and total_xp_earned >= target_xp:
                        console.print(f"[bold bright_green]🎯 Target of {target_xp} XP reached![/]\n")
                        break
                    if not until_goal and not target_xp and sessions_completed >= sessions:
                        break

                console.print(f"[bold bright_cyan]▶ Starting Session {session_num}...[/]")

                # Create live session on server — with retry + exponential backoff.
                server_sess = None
                raw_challenges: List[Dict[str, Any]] = []
                last_err: Optional[Exception] = None
                for attempt in range(1, 4):
                    try:
                        server_sess = self.client.create_practice_session(self.lang_code)
                        raw_challenges = server_sess.get("challenges", []) if server_sess else []
                        if raw_challenges:
                            last_err = None
                            break
                        # Empty but no exception — treat as retryable
                        raise DuoAPIError("Empty challenges list") if attempt < 3 else None
                    except Exception as e:
                        last_err = e
                        if attempt < 3:
                            backoff = random.uniform(2.0, 5.0) * attempt
                            print_warning(f"Session creation failed (attempt {attempt}/3): {e} — retrying in {backoff:.0f}s…")
                            time.sleep(backoff)
                        else:
                            print_error(f"Could not create practice session after 3 attempts: {e}")
                if last_err is not None and not raw_challenges:
                    break
                if server_sess is None:
                    print_error("Could not create practice session: unknown error")
                    break

                # Use the user's real heart count so a perfect run never
                # silently refills a depleted account on submit.
                try:
                    h = self.client.get_hearts()
                    if not h.get("is_unlimited") and isinstance(h.get("hearts"), int):
                        self.hearts = max(0, h["hearts"])
                except Exception:
                    pass

                if not raw_challenges:
                    print_error("No challenges returned by server — stopping.")
                    break

                total_q = len(raw_challenges)
                score = 0
                session_start_time = time.time()

                # Solve each question — humanized delay per challenge type.
                for q_idx, ch in enumerate(raw_challenges, 1):
                    details = extract_challenge_solution(ch)
                    prompt = details.get("prompt") or f"Question {q_idx}"
                    answer = details.get("answer") or "OK"
                    ctype = details.get("type") or ch.get("type", "")

                    # Fast path for audio/visual challenges — still count but with minimal pause.
                    if ctype in AUDIO_CHALLENGE_TYPES or ctype in VISUAL_CHALLENGE_TYPES:
                        pause = random.uniform(0.3, 0.6)
                    else:
                        pause = _human_delay(self.delay_min, self.delay_max, prompt, ctype)
                    render_auto_challenge(
                        session_idx=session_num,
                        total_sessions=0 if loop else (sessions if (not until_goal and not target_xp) else 0),
                        q_idx=q_idx,
                        total_q=total_q,
                        prompt=prompt,
                        answer=answer,
                        delay=pause,
                    )
                    time.sleep(pause)
                    score += 1

                # Submit session to Duolingo backend (or dry-run)
                if self.dry_run:
                    console.print(f"  [dim]⚡ Dry run — session {session_num} not submitted.[/]")
                    xp_gain = 15
                    total_xp_earned += xp_gain
                    sessions_completed += 1
                    render_auto_session_result(
                        session_idx=session_num,
                        xp_gained=xp_gain,
                        streak_extended=streak_extended,
                        total_xp_earned=total_xp_earned,
                    )
                else:
                    console.print(f"  [dim]Submitting session {session_num} to Duolingo servers...[/]")
                    sync_res = self.client.submit_practice_session(
                        server_sess,
                        score=score,
                        start_time=session_start_time,
                        hearts_left=self.hearts,
                        mistakes=max(0, len(raw_challenges) - score),
                        failed=self.hearts <= 0,
                    )

                    if sync_res.get("serverSync"):
                        xp_gain = sync_res.get("xpGain", 15)
                        streak_extended = sync_res.get("streakExtended", True)
                        total_xp_earned += xp_gain
                        sessions_completed += 1
                        render_auto_session_result(
                            session_idx=session_num,
                            xp_gained=xp_gain,
                            streak_extended=streak_extended,
                            total_xp_earned=total_xp_earned,
                        )
                    else:
                        print_warning(f"Session submission status: {sync_res}")

                # Pause between sessions if continuing
                should_continue = True
                if not loop:
                    if until_goal and (initial_xp_today + total_xp_earned) >= daily_goal:
                        should_continue = False
                    elif target_xp and total_xp_earned >= target_xp:
                        should_continue = False
                    elif not until_goal and not target_xp and sessions_completed >= sessions:
                        should_continue = False

                if should_continue:
                    # Pause between lessons: 3-8s base + jitter.
                    # Every 5 sessions add a slightly longer break (8-15s).
                    base_rest = random.uniform(self.rest_min, self.rest_max)
                    if sessions_completed > 0 and sessions_completed % 5 == 0:
                        base_rest = random.uniform(8.0, 15.0)
                        console.print(f"[dim]☕ Short break after {sessions_completed} sessions — resting for {base_rest:.0f}s...[/]\n")
                    else:
                        console.print(f"[dim]⏳ Resting for {base_rest:.0f}s before next session...[/]\n")
                    # add small jitter
                    base_rest += random.gauss(0, 0.4)
                    base_rest = max(2.0, base_rest)
                    time.sleep(base_rest)

        except KeyboardInterrupt:
            console.print("\n[bold bright_yellow]⚠ Auto practice paused by user (Ctrl+C).[/]")

        # Fetch final stats
        final_streak = current_streak
        try:
            final_info = self.client.get_streak_info(force_refresh=True)
            final_streak = final_info.get("site_streak", current_streak)
            streak_extended = final_info.get("streak_extended_today", streak_extended)
        except Exception:
            pass

        render_auto_summary(
            sessions_completed=sessions_completed,
            total_xp=total_xp_earned,
            streak_days=final_streak,
            streak_extended=streak_extended,
        )
