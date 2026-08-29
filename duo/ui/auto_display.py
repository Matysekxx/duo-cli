"""
Display renderers for AutoPractice solver sessions.
"""

from typing import Optional
from .common import SECTION_SEP, console


def render_auto_header(
    lang: str,
    sessions: Optional[int],
    target_xp: Optional[int],
    until_goal: bool,
    loop: bool = False,
    max_sessions: Optional[int] = None,
) -> None:
    """Render the header banner for automated practice."""
    if until_goal:
        goal_mode = "Until daily goal"
    elif target_xp:
        goal_mode = f"Target: {target_xp} XP"
    elif sessions is not None:
        goal_mode = f"{sessions} session(s)"
    elif max_sessions is not None:
        goal_mode = f"Continuous (max {max_sessions} sessions)"
    else:
        goal_mode = "∞  Continuous / Infinite"

    console.print()
    console.print("[bold bright_green]⚡  AUTO PRACTICE[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print(f"  [dim]Language[/dim]  [bold bright_cyan]{lang.upper()}[/]   [dim]Mode[/dim]  [bold bright_yellow]{goal_mode}[/]")
    console.print("  [dim]Solving with natural delays and realistic inter-session rests…[/dim]")
    console.print("  [dim]Press [bold]Ctrl+C[/] to stop safely at any time.[/dim]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print()


def render_auto_challenge(
    session_idx: int,
    total_sessions: int,
    q_idx: int,
    total_q: int,
    prompt: str,
    answer: str,
    delay: float,
) -> None:
    """Render a single solved challenge line."""
    sess_info = f"S{session_idx}" if total_sessions <= 1 else f"S{session_idx}/{total_sessions}"
    console.print(
        f"  [dim]›[/dim] [bold white][{sess_info}  Q{q_idx:02d}/{total_q:02d}][/] "
        f"[white]{prompt[:44]}[/] [dim]→[/] [bold bright_green]{answer[:36]}[/] "
        f"[dim]{delay:.1f}s[/dim]"
    )


def render_auto_session_result(
    session_idx: int,
    xp_gained: int,
    streak_extended: bool,
    total_xp_earned: int,
) -> None:
    """Render completion status after a session."""
    streak_msg = "[bold bright_green]🔥 streak kept[/]" if streak_extended else ""
    console.print(
        f"  [bold bright_green]✔ Session {session_idx} done[/]  "
        f"[bold bright_yellow]+{xp_gained} XP[/]  {streak_msg}  "
        f"[dim](total +{total_xp_earned} XP)[/dim]"
    )
    console.print()


def render_auto_summary(
    sessions_completed: int,
    total_xp: int,
    streak_days: int,
    streak_extended: bool,
) -> None:
    """Render final summary upon stopping auto practice."""
    if streak_extended:
        status_str = f"[bold bright_yellow]🔥 {streak_days} days[/]  [bold bright_green]✓ secured today[/]"
        congrats = "[bold bright_green]🎉  Streak extended — great job![/]\n"
    else:
        status_str = f"[bold bright_yellow]{streak_days} days[/]"
        congrats = ""

    console.print()
    console.print("[bold bright_green]⚡  AUTO SUMMARY[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print(f"  [dim]Sessions[/dim]       [bold bright_cyan]{sessions_completed}[/]")
    console.print(f"  [dim]Total XP[/dim]       [bold bright_green]+{total_xp} XP[/]")
    console.print(f"  [dim]Streak[/dim]         {status_str}")
    if congrats:
        console.print(f"  {congrats}", end="")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print()
