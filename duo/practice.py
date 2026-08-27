"""
Interactive Practice and Automated Solver Engine with live Duolingo Server Sync (XP & Streak).
"""

import random
import time
from typing import Any, Dict, List, Optional
from rich.prompt import Prompt

from .api import DuoClient, extract_challenge_solution, get_flag
from .config import is_audio_snoozed, set_audio_snooze
from .ui import (
    DIVIDER_LINE,
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
    render_answer_result,
    render_auto_challenge,
    render_auto_header,
    render_auto_session_result,
    render_auto_summary,
    render_freeform_card,
    render_match_panel,
    render_question_card,
)

CURATED_CHALLENGES = {
    "es": [
        {"prompt": "Translate to Spanish: 'The cat drinks milk'", "answer": "el gato bebe leche", "wrong": ["el perro come pan", "el niño bebe agua", "el gato come queso"]},
        {"prompt": "What does 'Gracias' mean?", "answer": "thank you", "wrong": ["please", "good morning", "goodbye"]},
        {"prompt": "Translate: 'Buenos días'", "answer": "good morning", "wrong": ["good night", "hello", "see you"]},
        {"prompt": "Translate: 'Water'", "answer": "agua", "wrong": ["leche", "vino", "pan"]},
        {"prompt": "Translate: 'Por favor'", "answer": "please", "wrong": ["thank you", "excuse me", "you're welcome"]},
        {"prompt": "Translate: 'The boy reads a book'", "answer": "el niño lee un libro", "wrong": ["la niña come una manzana", "el hombre bebe vino", "el niño escribe una carta"]},
        {"prompt": "What is 'Bread' in Spanish?", "answer": "pan", "wrong": ["manzana", "agua", "queso"]},
        {"prompt": "Translate: 'Buenas noches'", "answer": "good night", "wrong": ["good morning", "good afternoon", "welcome"]},
    ],
    "de": [
        {"prompt": "Translate: 'Guten Morgen'", "answer": "good morning", "wrong": ["good night", "hello", "goodbye"]},
        {"prompt": "What does 'Danke' mean?", "answer": "thank you", "wrong": ["please", "sorry", "yes"]},
        {"prompt": "Translate: 'Cat'", "answer": "katze", "wrong": ["hund", "vogel", "pferd"]},
        {"prompt": "Translate: 'Water and bread'", "answer": "wasser und brot", "wrong": ["milch und käse", "tee und kaffee", "bier und wein"]},
        {"prompt": "Translate: 'Auf Wiedersehen'", "answer": "goodbye", "wrong": ["see you later", "welcome", "please"]},
        {"prompt": "Translate: 'The woman is drinking'", "answer": "die frau trinkt", "wrong": ["der mann isst", "das kind schläft", "die frau liest"]},
    ],
    "en": [
        {"prompt": "Translate: 'Hello'", "answer": "hello", "wrong": ["good night", "goodbye", "welcome"]},
        {"prompt": "Translate: 'Thank you'", "answer": "thank you", "wrong": ["please", "sorry", "welcome"]},
        {"prompt": "What is 'Apple'?", "answer": "apple", "wrong": ["bread", "water", "milk"]},
        {"prompt": "Translate: 'Good morning'", "answer": "good morning", "wrong": ["good night", "good afternoon", "bye"]},
    ],
    "fr": [
        {"prompt": "Translate: 'Bonjour'", "answer": "hello", "wrong": ["goodbye", "please", "thank you"]},
        {"prompt": "Translate: 'Merci'", "answer": "thank you", "wrong": ["please", "sorry", "yes"]},
        {"prompt": "What is 'The cat' in French?", "answer": "le chat", "wrong": ["le chien", "le cheval", "l'oiseau"]},
        {"prompt": "Translate: 'Un croissant, s'il vous plaît'", "answer": "a croissant please", "wrong": ["a coffee please", "two baguettes", "thank you very much"]},
    ],
    "cs": [
        {"prompt": "Translate: 'Ahoj'", "answer": "hello", "wrong": ["goodbye", "thank you", "please"]},
        {"prompt": "Translate: 'Děkuji'", "answer": "thank you", "wrong": ["please", "good morning", "sorry"]},
        {"prompt": "What is 'Water' in Czech?", "answer": "voda", "wrong": ["chléb", "mléko", "pivo"]},
        {"prompt": "Translate: 'Dobré ráno'", "answer": "good morning", "wrong": ["good night", "good afternoon", "goodbye"]},
    ],
}


def normalize_answer(text: str) -> str:
    clean = text.lower().strip()
    for char in [".", ",", "!", "?", "'", '"', "¿", "¡", ":", ";", "-", "–"]:
        clean = clean.replace(char, " ")
    return " ".join(clean.split())


class PracticeSession:
    """Interactive practice engine for manual terminal learning."""

    def __init__(self, client: DuoClient, lang_code: Optional[str] = None):
        self.client = client
        self.lang_code = (lang_code or "es").lower()
        self.score = 0
        self.hearts = 5
        self.combo = 0
        self.max_combo = 0
        self.server_session = None

    def run(self) -> None:
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
            pool = CURATED_CHALLENGES.get(self.lang_code, CURATED_CHALLENGES.get("es", []))
            questions = []
            for item in pool:
                all_choices = [item["answer"]] + item.get("wrong", [])
                random.shuffle(all_choices)
                questions.append({
                    "type": "multiple_choice",
                    "prompt": item["prompt"],
                    "choices": all_choices,
                    "answer": item["answer"],
                    "solutions": [item["answer"]],
                })

        console.print()
        console.print("[bold bright_green]🦉 DUOLINGO PRACTICE SESSION[/]")
        console.print(f"[dim green]{DIVIDER_LINE}[/]")
        console.print(f"  Language  : [bold bright_cyan]{self.lang_code.upper()}[/] | Questions: [bold yellow]{len(questions)}[/] | Hearts: [bold red]{self.hearts}/5[/]")
        console.print(f"  User      : [bold bright_white]@{self.client.username or 'guest'}[/]")
        console.print("  [dim]Type choice (1..N), enter answer, 'skip' to skip, or 'exit' to quit.[/]")
        console.print(f"[dim green]{DIVIDER_LINE}[/]\n")

        for idx, q in enumerate(questions, 1):
            if self.hearts <= 0:
                console.print("\n[bold bright_red]💔 You ran out of hearts! Practice session ended.[/]\n")
                break

            q_type = q.get("type", "")
            if is_audio_snoozed() and q_type in ["speak", "listenSpeak", "listen", "listenTap", "listenComplete", "listenIsolation", "listenMatch", "partialListen"]:
                console.print(f"\n[dim yellow]🔇 Audio/Speaking exercise snoozed for 15 min. Auto-completed! ✔[/dim yellow]")
                self.score += 1
                time.sleep(0.3)
                continue

            if q_type in ["speak", "listenSpeak"]:
                console.print(f"\n[dim yellow]🎤 Audio/Speaking exercise auto-skipped for terminal. Marked correct! ✔[/dim yellow]")
                self.score += 1
                time.sleep(0.3)
                continue

            prompt_text = q.get("prompt", "")
            correct_raw = q.get("answer", "")
            solutions = [normalize_answer(s) for s in q.get("solutions", [])] if q.get("solutions") else [normalize_answer(correct_raw)]

            pair_tuples = q.get("pair_tuples", [])
            choices = q.get("choices", [])

            if pair_tuples and len(pair_tuples) > 1:
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
                    if ans.lower() in ["skip", "s"]:
                        console.print("[dim yellow]⏭ Matching question skipped.[/dim yellow]")
                        matched_all = True
                        break
                    if ans.lower() in ["cant-listen", "cant-speak", "no-audio", "mute", "cant", "nemuzu", "snooze"]:
                        set_audio_snooze(15)
                        console.print("\n[bold yellow]🔇 'Can't listen/speak right now' enabled for 15 minutes![/]")
                        matched_all = True
                        break

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
                if user_input.lower() in ["skip", "s"]:
                    console.print("[dim yellow]⏭ Question skipped.[/dim yellow]")
                    continue
                if user_input.lower() in ["cant-listen", "cant-speak", "no-audio", "mute", "cant", "nemuzu", "snooze"]:
                    set_audio_snooze(15)
                    console.print("\n[bold yellow]🔇 'Can't listen/speak right now' enabled for 15 minutes![/]")
                    console.print("[dim]Listening and speaking exercises turned off for the next 15 minutes.[/dim]")
                    self.score += 1
                    time.sleep(0.4)
                    continue

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
                self.hearts -= 1
                self.combo = 0
                display_ans = correct_raw or ((q.get("solutions") or [""])[0])
                if pair_tuples:
                    console.print(f"\n[bold bright_red]✖ Some pairs were incorrect! Lost a heart (Remaining: {self.hearts}/5)[/]")
                else:
                    render_answer_result(False, display_ans)
            time.sleep(0.4)

        # Submit results to Duolingo backend if possible
        sync_status = ""
        if self.client.is_authenticated() and self.score > 0:
            console.print("\n[bold cyan]⏳ Submitting session to Duolingo servers...[/]")
            session_to_submit = self.server_session or {"id": "dummy", "learningLanguage": self.lang_code}
            sync_res = self.client.submit_practice_session(session_to_submit, self.score, start_time=session_start_time)

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
    """Automated Practice Solver Engine with natural delays and multi-session capabilities."""

    def __init__(
        self,
        client: DuoClient,
        lang_code: Optional[str] = None,
        delay_min: float = 1.2,
        delay_max: float = 2.8,
        fast: bool = False,
    ):
        self.client = client
        self.lang_code = (lang_code or "es").lower()
        self.fast = fast
        if fast:
            self.delay_min = 0.3
            self.delay_max = 0.7
        else:
            self.delay_min = max(delay_min, 0.5)
            self.delay_max = max(delay_max, self.delay_min)

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

        # Fetch initial user status
        try:
            user_info = self.client.verify_auth()
            streak_info = self.client.get_streak_info()
            if not self.lang_code:
                self.lang_code = user_info.get("learningLanguage", "es")
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

                # Create live session on server
                try:
                    server_sess = self.client.create_practice_session(self.lang_code)
                    raw_challenges = server_sess.get("challenges", [])
                except Exception as e:
                    print_warning(f"Could not load live challenges from server: {e}. Retrying...")
                    time.sleep(2)
                    continue

                if not raw_challenges:
                    print_warning("No challenges returned by server. Retrying in 2 seconds...")
                    time.sleep(2)
                    continue

                total_q = len(raw_challenges)
                score = 0
                session_start_time = time.time()

                # Solve each question with randomized human-like pauses
                for q_idx, ch in enumerate(raw_challenges, 1):
                    details = extract_challenge_solution(ch)
                    prompt = details.get("prompt") or f"Question {q_idx}"
                    answer = details.get("answer") or "OK"

                    # Calculate pause
                    pause = random.uniform(self.delay_min, self.delay_max)
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

                # Submit session to Duolingo backend
                console.print(f"  [dim]Submitting session {session_num} to Duolingo servers...[/]")
                sync_res = self.client.submit_practice_session(server_sess, score=score, start_time=session_start_time)

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
                    # Occasional longer "coffee break" in infinite loop mode to stay safe
                    if loop and sessions_completed > 0 and sessions_completed % 5 == 0:
                        rest_pause = random.uniform(30.0, 60.0)
                        console.print(f"[dim]⏳ Long break for {rest_pause:.0f}s (every 5 sessions in loop mode)...[/]\n")
                    else:
                        rest_pause = random.uniform(2.0, 3.5) if not self.fast else 0.8
                        console.print(f"[dim]⏳ Resting for {rest_pause:.1f}s before next session...[/]\n")
                    time.sleep(rest_pause)

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
