"""
Dashboard, calendar, hearts, and config renderers.
"""

from typing import Any, Dict, List, Optional
from .common import SECTION_SEP, _hearts_bar, _make_table, console


def render_status(data: Dict[str, Any], user_data: Optional[Dict[str, Any]] = None) -> None:
    """Minimal dashboard — typography + spacing, no borders."""
    streak = data.get("site_streak", 0)
    streak_extended = data.get("streak_extended_today", False)
    gems = data.get("gems", 0)
    total_xp = data.get("total_xp", 0)
    username = (user_data or {}).get("username") or data.get("username") or "Learner"

    curr_course = data.get("current_course", {})
    if curr_course:
        code = curr_course.get('learningLanguage', '').upper()
        title = curr_course.get('title', 'Unknown')
        course_display = f"{title} [{code}]" if code else title
    elif user_data and user_data.get("learningLanguage"):
        code = user_data.get("learningLanguage", "").upper()
        course_display = f"Course [{code}]"
    else:
        from ..config import get_preset_language
        preset = get_preset_language()
        if preset:
            course_display = f"Course [{preset.upper()}]"
        else:
            course_display = "No active course [—]"

    streak_badge = "[bold white on dark_green]  ✓ COMPLETED TODAY  [/]" if streak_extended else "[bold white on dark_red]  ⌛ INCOMPLETE  [/]"
    accent = "bright_green" if streak_extended else "bright_red"
    effect_msg = (
        f"[bold bright_green]🔥 Streak secured today — great job, @{username}![/]"
        if streak_extended else
        f"[bold bright_yellow]⚠ Streak expires tonight — run [bright_white]duo auto[/] to keep it![/]"
    )

    console.print()
    console.print(f"[bold bright_cyan]🦉  DUOLINGO DASHBOARD[/]  [dim]@{username}[/dim]")
    console.print(f"[{accent} dim]{SECTION_SEP}[/]")
    console.print(f"  [dim]Course[/dim]         [bold bright_cyan]{course_display}[/]")
    console.print(f"  [dim]Total XP[/dim]       [bold bright_magenta]{total_xp:,} XP[/]")
    console.print(f"  [dim]Gems[/dim]           [bold bright_yellow]{gems:,}[/]")
    if streak == 0:
        streak_color = "dim"
        streak_icon = "💤"
    elif streak < 7:
        streak_color = "bright_yellow"
        streak_icon = "🔥"
    elif streak < 30:
        streak_color = "bright_green"
        streak_icon = "🔥"
    elif streak < 100:
        streak_color = "bold bright_green"
        streak_icon = "🏆"
    else:
        streak_color = "bold yellow"
        streak_icon = "👑"
    console.print(f"  [dim]Streak[/dim]         [{streak_color}]{streak_icon} {streak} days[/]  {streak_badge}")
    console.print(f"[{accent} dim]{SECTION_SEP}[/]")
    console.print(f"  {effect_msg}")
    console.print()


def render_calendar(calendar_data: List[Dict[str, Any]], days: int = 14) -> None:
    """Render the activity heatmap table."""
    table = _make_table(f"ACTIVITY  ·  LAST {days} DAYS")
    table.add_column("Date", style="bold white", no_wrap=True)
    table.add_column("Day", justify="center", style="bright_blue")
    table.add_column("Status", justify="center")
    table.add_column("XP", justify="right", style="bright_magenta")

    for day in calendar_data:
        date_str = day["date"]
        day_name = day["day_name"]
        xp = f"[bold bright_green]+{day['xp']} XP[/]" if day['xp'] > 0 else "[dim]0 XP[/dim]"
        status = "[bold bright_green]● active[/]" if day["is_active"] else "[dim]○ inactive[/dim]"
        if day["is_today"]:
            date_str = f"[bold bright_yellow]› {date_str}  today[/]"
        table.add_row(date_str, day_name, status, xp)

    console.print(table)
    console.print(f"[dim]{SECTION_SEP}[/dim]")


def render_hearts(hearts_data: Dict[str, Any]) -> None:
    """Render hearts indicator bar."""
    hearts = hearts_data.get("hearts")
    is_unlimited = hearts_data.get("is_unlimited", False)
    max_h = hearts_data.get("max_hearts", 5)
    console.print()
    console.print("[bold bright_cyan]❤️  HEARTS[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    if is_unlimited:
        console.print("  [bold bright_green]Unlimited ♥[/]  [dim](Super Duolingo)[/dim]")
    else:
        try:
            h_int = int(hearts) if isinstance(hearts, (int, str)) and str(hearts).isdigit() else (hearts if isinstance(hearts, int) else 0)
        except Exception:
            h_int = 0
        bar = _hearts_bar(h_int)
        console.print(f"  {bar}  [bold white]{h_int}/{max_h}[/]")
        if h_int == 0:
            console.print("  [bold bright_red]Out of hearts! Wait for refill or buy in shop.[/]")
        elif h_int <= 2:
            console.print("  [bold bright_yellow]Low hearts — be careful![/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print()


def render_config(config_data: Dict[str, Any]) -> None:
    """Render configuration and authentication state."""
    console.print()
    console.print("[bold bright_cyan]⚙️  CONFIG[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    for k, v in config_data.items():
        console.print(f"  [dim]{k:<18}[/] [white]{v}[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print()
