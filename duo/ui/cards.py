"""
Question and challenge renderers for interactive practice.
"""

from typing import List, Optional
from ..challenges.types import get_flag
from .common import SECTION_SEP, _combo_badge, _hearts_bar, console


def render_question_card(
    q_idx: int,
    total_q: int,
    prompt: str,
    choices: List[str],
    hearts: int,
    combo: int,
    lang_code: Optional[str],
    q_type: str = "",
) -> None:
    """Multiple choice challenge card."""
    flag = get_flag(lang_code)
    type_label = ""
    if q_type:
        pretty = {
            "translate": "Translate",
            "assist": "Translate",
            "select": "Multiple choice",
            "gapFill": "Fill the blank",
            "match": "Match",
        }.get(q_type, q_type)
        type_label = f"  [dim]· {pretty}[/dim]"

    console.print()
    console.print(
        f"{flag}  [bold white]Q{q_idx}/{total_q}[/]{type_label}"
        f"    {_hearts_bar(hearts)}{_combo_badge(combo)}"
    )
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print(f"  [bold white]{prompt}[/]")
    console.print()
    if choices:
        for i, c in enumerate(choices, 1):
            console.print(f"  [bold bright_yellow]{i}.[/]  [white]{c}[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")


def render_freeform_card(
    q_idx: int,
    total_q: int,
    prompt: str,
    hearts: int,
    combo: int,
    lang_code: Optional[str],
    q_type: str = "",
) -> None:
    """Freeform translation challenge card."""
    flag = get_flag(lang_code)
    console.print()
    console.print(
        f"{flag}  [bold white]Q{q_idx}/{total_q}[/]"
        f"    {_hearts_bar(hearts)}{_combo_badge(combo)}"
    )
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print(f"  [bold white]{prompt}[/]")
    console.print()
    console.print("  [dim]✎  Type your answer below[/dim]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")


def render_match_panel(
    left_word: str,
    options: List[str],
    p_idx: int,
    total_pairs: int,
    hearts: int,
    combo: int,
    lang_code: Optional[str],
) -> None:
    """Pair matching sub-step panel."""
    flag = get_flag(lang_code)
    console.print()
    console.print(
        f"{flag}  [bold bright_cyan]Match {p_idx}/{total_pairs}[/]"
        f"    {_hearts_bar(hearts)}{_combo_badge(combo)}"
    )
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print(f"  [bold bright_yellow]{left_word}[/]  [dim]⇄  pick its translation[/dim]")
    console.print()
    for i, o in enumerate(options, 1):
        console.print(f"  [bold bright_yellow]{i}.[/]  [white]{o}[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")


def render_build_card(
    q_idx: int,
    total_q: int,
    prompt: str,
    word_bank: List[str],
    hearts: int,
    combo: int,
    lang_code: Optional[str],
    q_type: str = "",
) -> None:
    """Sentence construction word-bank card."""
    flag = get_flag(lang_code)
    console.print()
    console.print(
        f"{flag}  [bold white]Q{q_idx}/{total_q}[/]  [dim]· Build sentence[/dim]"
        f"    {_hearts_bar(hearts)}{_combo_badge(combo)}"
    )
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print(f"  [bold white]{prompt}[/]")
    console.print()
    for i, w in enumerate(word_bank, 1):
        console.print(f"  [bold bright_yellow]{i}.[/]  [white]{w}[/]")
    console.print()
    console.print("  [dim]Type numbers in order [yellow]3 1 4 2[/] or type the full sentence.[/dim]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")


def render_answer_result(is_correct: bool, correct_answer: str, gained_xp: int = 10) -> None:
    """Result feedback banner after an answer."""
    if is_correct:
        console.print(f"\n[bold bright_green]✔ Correct[/]  [dim]+{gained_xp} XP[/dim]  🎉")
    else:
        console.print(f"\n[bold bright_red]✘ Incorrect[/]  [dim]answer:[/dim] [bold green]{correct_answer}[/]")
