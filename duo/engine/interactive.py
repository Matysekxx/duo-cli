"""
Interactive terminal practice engine for manual learning.
"""

import time
from typing import Any, Dict, List, Optional
from rich.prompt import Prompt
from ..challenges.normalizer import normalize_answer
from ..challenges.types import VISUAL_CHALLENGE_TYPES
from ..models import Challenge
from ..ui import (
    DIVIDER_LINE,
    console,
    print_error,
    print_warning,
    render_answer_result,
    render_build_card,
    render_freeform_card,
    render_match_panel,
    render_question_card,
)
from .base import BaseEngine


class InteractiveEngine(BaseEngine):
    """Interactive practice engine for manual terminal learning."""

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
        live_challenges: List[Challenge] = []
        if self.client and hasattr(self.client, "is_authenticated") and self.client.is_authenticated():
            try:
                self.server_session, live_challenges = self._fetch_challenges()
            except Exception:
                self.server_session = None

        if not live_challenges:
            print_warning(
                "No practice questions available. Run 'duo login' to fetch live "
                "Duolingo challenges for your course."
            )
            return

        # Fetch real hearts from server
        self._refresh_hearts()

        console.print()
        console.print("[bold bright_green]🦉 DUOLINGO PRACTICE SESSION[/]")
        console.print(f"[dim green]{DIVIDER_LINE}[/]")
        console.print(f"  Language  : [bold bright_cyan]{self.lang_code.upper()}[/] | Questions: [bold yellow]{len(live_challenges)}[/] | Hearts: [bold red]{self.hearts}/5[/]")
        username = getattr(self.client, "username", None) or "guest"
        console.print(f"  User      : [bold bright_white]@{username}[/]")
        console.print()
        console.print("  [dim]How to play:[/]")
        console.print("    • [white]Multiple choice[/] → type the [bold yellow]number[/] of your answer")
        console.print("    • [white]Translate[/] → type the translation")
        console.print("    • [white]Build sentence[/] → type word [bold yellow]numbers[/] in order (e.g. [yellow]3 1 4 2[/]) or the sentence")
        console.print("    • [white]exit[/] to quit the session")
        console.print(f"[dim green]{DIVIDER_LINE}[/]\n")

        for idx, q in enumerate(live_challenges, 1):
            done = idx - 1
            total_q = len(live_challenges)
            bar_filled = int((done / total_q) * 20) if total_q else 0
            bar_str = "[bold bright_green]" + "█" * bar_filled + "[/][dim]" + "░" * (20 - bar_filled) + "[/]"
            console.print(f"\n  {bar_str}  [dim]{done}/{total_q} done[/]")

            if self.hearts <= 0:
                console.print("\n[bold bright_red]💔 You ran out of hearts! Practice session ended.[/]\n")
                break

            q_type = q.type
            if q_type in VISUAL_CHALLENGE_TYPES:
                console.print(f"\n[dim yellow]🖼️ Visual exercise ('{q_type}') can't be shown in terminal. Auto-completed! ✔[/dim yellow]")
                self.score += 1
                time.sleep(0.15)
                continue

            prompt_text = q.prompt
            correct_raw = q.answer
            solutions = [normalize_answer(s) for s in q.solutions] if q.solutions else [normalize_answer(correct_raw)]
            pair_tuples = q.pair_tuples
            choices = q.choices
            word_bank = q.word_bank

            if not q.is_renderable:
                console.print(
                    f"\n[dim yellow]⏭ Unsupported challenge ('{q_type}') "
                    f"can't be shown in terminal. Skipped![/dim yellow]"
                )
                self.score += 1
                time.sleep(0.15)
                continue

            if word_bank:
                render_build_card(idx, len(live_challenges), prompt_text, word_bank, self.hearts, self.combo, self.lang_code, q_type)
                user_input = Prompt.ask(f"\n[bold bright_green]Your sentence[/]").strip()
                if user_input.lower() in ["exit", "quit", "q"]:
                    break

                tokens_by_num = []
                for token in user_input.split():
                    if token.isdigit():
                        num = int(token)
                        if 1 <= num <= len(word_bank):
                            tokens_by_num.append(word_bank[num - 1])
                if tokens_by_num:
                    constructed_sentence = " ".join(tokens_by_num)
                    user_clean = normalize_answer(constructed_sentence)
                else:
                    user_clean = normalize_answer(user_input)

            elif pair_tuples:
                console.print()
                all_correct = True
                remaining_pairs = list(pair_tuples)
                random_pairs = list(pair_tuples)
                import random
                random.shuffle(random_pairs)

                for p_idx, (lw, correct_tr) in enumerate(random_pairs, 1):
                    avail_options = [tr for (_, tr) in remaining_pairs]
                    random.shuffle(avail_options)
                    render_match_panel(lw, avail_options, p_idx, len(pair_tuples), self.hearts, self.combo, self.lang_code)

                    p_input = Prompt.ask(f"\n[bold bright_cyan]Match number (1-{len(avail_options)})[/]").strip()
                    if p_input.lower() in ["exit", "quit", "q"]:
                        all_correct = False
                        break

                    chosen_tr = ""
                    if p_input.isdigit() and 1 <= int(p_input) <= len(avail_options):
                        chosen_tr = avail_options[int(p_input) - 1]
                    else:
                        chosen_tr = p_input

                    if normalize_answer(chosen_tr) == normalize_answer(correct_tr):
                        console.print(f"[bold bright_green]✔ Correct pair:[/] {lw} ⇄ {chosen_tr}")
                        remaining_pairs = [(w, t) for (w, t) in remaining_pairs if w != lw]
                    else:
                        console.print(f"[bold bright_red]✖ Wrong match![/] {lw} ⇄ [bold green]{correct_tr}[/]")
                        all_correct = False
                        break

                if all_correct:
                    user_clean = "correct"
                    solutions = ["correct"]
                else:
                    user_clean = "wrong"
                    solutions = ["correct"]

            elif choices:
                render_question_card(idx, len(live_challenges), prompt_text, choices, self.hearts, self.combo, self.lang_code, q_type)
                user_input = Prompt.ask(f"\n[bold bright_green]Your answer (1-{len(choices)})[/]").strip()
                if user_input.lower() in ["exit", "quit", "q"]:
                    break

                if user_input.isdigit():
                    opt_idx = int(user_input) - 1
                    if 0 <= opt_idx < len(choices):
                        user_clean = normalize_answer(choices[opt_idx])
                    else:
                        user_clean = normalize_answer(user_input)
                else:
                    user_clean = normalize_answer(user_input)

            else:
                render_freeform_card(idx, len(live_challenges), prompt_text, self.hearts, self.combo, self.lang_code, q_type)
                user_input = Prompt.ask(f"\n[bold bright_green]Your translation[/]").strip()
                if user_input.lower() in ["exit", "quit", "q"]:
                    break
                user_clean = normalize_answer(user_input)

            # Evaluate response
            is_correct = any(user_clean == s or (len(s) > 1 and user_clean == s.strip()) for s in solutions)
            if is_correct:
                self.score += 1
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                render_answer_result(True, correct_raw)
            else:
                self.hearts = max(0, self.hearts - 1)
                self.combo = 0
                display_ans = correct_raw or (q.solutions[0] if q.solutions else "")
                if pair_tuples:
                    console.print(f"\n[bold bright_red]✖ Some pairs were incorrect! Lost a heart (Remaining: {self.hearts}/5)[/]")
                else:
                    render_answer_result(False, display_ans)
            time.sleep(0.2)

        # Submit results
        sync_status = ""
        if self.dry_run:
            sync_status = "[bold bright_yellow]⚡ Dry run — not submitted to server.[/]"
        elif self.client and hasattr(self.client, "is_authenticated") and self.client.is_authenticated() and self.score > 0:
            console.print("\n[bold cyan]⏳ Submitting session to Duolingo servers...[/]")
            session_to_submit = self.server_session or {"id": "dummy", "learningLanguage": self.lang_code}
            res = self._submit_session(session_to_submit, self.score, session_start_time, len(live_challenges))
            if res.synced:
                sync_status = f"[bold bright_green]✔ Synced +{res.xp_gained} XP[/]"
                if res.streak_extended:
                    sync_status += " [bold bright_yellow]🔥 Streak kept![/]"
            else:
                sync_status = "[bold bright_yellow]⚠ Completed (server sync pending)[/]"
        else:
            sync_status = "[dim]Session finished in offline mode.[/]"

        console.print()
        console.print("[bold bright_green]📊 PRACTICE RESULTS[/]")
        console.print(f"[dim green]{DIVIDER_LINE}[/]")
        console.print(f"  Score         : [bold bright_green]{self.score} / {len(live_challenges)}[/]")
        console.print(f"  Highest Combo : [bold bright_yellow]🔥 {self.max_combo}[/]")
        console.print(f"  Result        : {sync_status}")
        console.print(f"[dim green]{DIVIDER_LINE}[/]\n")


# Backward compatibility alias
PracticeSession = InteractiveEngine
