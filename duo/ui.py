"""
Clean, minimal TUI for duo-cli — no box borders, no heavy chrome.

Design goals:
- No `rich.box` borders at all — tables use `box=None`, cards use spacing +
  typography + subtle dim separators only. This avoids any glyph/encoding
  issues and keeps the output scannable.
- Consistent accent colors, clear section titles, and generous padding so
  the eye can parse content without relying on grid lines.
"""

import sys
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from .api import get_flag


class _DynamicStdout:
    """File-like proxy that always writes to the current sys.stdout (capturable by CliRunner)."""

    def write(self, text: str) -> int:
        return sys.stdout.write(text)

    def flush(self) -> None:
        try:
            sys.stdout.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        try:
            return sys.stdout.isatty()  # type: ignore[attr-defined]
        except Exception:
            return False


console = Console(file=_DynamicStdout(), highlight=False, force_terminal=True)

DIVIDER_LINE = "─" * 56
SECTION_SEP = "─" * 56


def _get_version() -> str:
    """Single source of truth for version — duo.__version__ first (dev), then installed metadata."""
    try:
        from . import __version__ as _v

        return str(_v)
    except Exception:
        pass
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("duo-cli")
    except Exception:
        pass
    try:
        from pathlib import Path
        import re

        # Fallback: parse pyproject.toml without importlib
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        if pyproject.exists():
            m = re.search(r'version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
    except Exception:
        pass
    return "0.0.0"


__version__ = _get_version()

# --- LOGO BANNER ---
# Built dynamically so banner always matches the installed package version.
_BANNER_ART = r"""[bold bright_green]
  ██████╗  ██╗   ██╗  ██████╗         ██████╗ ██╗     ██╗
  ██╔══██╗ ██║   ██║ ██╔═══██╗       ██╔════╝ ██║     ██║
  ██║  ██║ ██║   ██║ ██║   ██║ █████╗██║      ██║     ██║
  ██║  ██║ ██║   ██║ ██║   ██║ ╚════╝██║      ██║     ██║
  ██████╔╝ ╚██████╔╝ ╚██████╔╝       ╚██████╗ ███████╗██║
  ╚═════╝   ╚═════╝   ╚═════╝         ╚═════╝ ╚══════╝╚═╝[/]"""
_BANNER_TAGLINE = "  [dim cyan]─── Duolingo Terminal Interface & Automated Learning Engine ───[/]"


def _build_banner() -> str:
    return f"{_BANNER_ART} [bold bright_yellow]v{__version__}[/]\n{_BANNER_TAGLINE}"


DUO_BANNER = _build_banner()


def print_banner() -> None:
    # Rebuild each time in case version was mocked in tests
    console.print(_build_banner())


def print_success(message: str) -> None:
    console.print(f"[bold bright_green]✔ {message}[/]")


def print_error(message: str) -> None:
    console.print(f"[bold bright_red]✘ {message}[/]")


def print_warning(message: str) -> None:
    console.print(f"[bold bright_yellow]⚠ {message}[/]")


def print_info(message: str) -> None:
    console.print(f"[bold cyan]ℹ {message}[/]")


# ---- helpers for borderless tables ----

def _make_table(title: str) -> Table:
    """Create a borderless table — no box, just clean columns and padding."""
    t = Table(
        title=f"[bold bright_cyan]{title}[/]",
        title_style="bold bright_cyan",
        title_justify="left",
        box=None,
        show_header=True,
        header_style="bold bright_cyan",
        pad_edge=False,
        padding=(0, 2),
        collapse_padding=True,
        show_lines=False,
    )
    return t


def _print_section_title(title: str, subtitle: str = "") -> None:
    console.print()
    console.print(f"[bold bright_cyan]{title}[/]" + (f"  [dim]{subtitle}[/dim]" if subtitle else ""))
    console.print(f"[dim]{SECTION_SEP}[/dim]")


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
        from .config import get_preset_language
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
    # Streak gradient: short=yellow, 7d+=green, 30d+=bright_green+trophy, 100d+=gold
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


def render_shop(items: List[Dict[str, Any]], user_gems: int) -> None:
    # header line outside table for balance — more scannable without borders
    console.print()
    console.print(f"[bold bright_cyan]SHOP[/]  [dim]balance[/dim] [bold bright_yellow]{user_gems:,} gems[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")

    table = _make_table("")
    table.title = None
    table.add_column("Item", style="bold white")
    table.add_column("Price", justify="right", style="bold bright_yellow")
    table.add_column("Description", style="dim white")

    for it in items:
        name = str(it["name"])
        cost = f"{it['cost']} gems"
        table.add_row(name, cost, it["desc"])

    console.print(table)
    console.print(f"[dim]{SECTION_SEP}[/dim]")


def render_courses_table(courses: List[Dict[str, Any]]) -> None:
    if not courses:
        print_info("No enrolled courses found.")
        return

    table = _make_table("ENROLLED COURSES")
    table.add_column("", justify="center", no_wrap=True)
    table.add_column("Course", style="bold white")
    table.add_column("Code", justify="center", style="bright_cyan")
    table.add_column("Total XP", justify="right", style="bright_magenta")

    seen = set()
    unique_courses = []
    for c in courses:
        key = (c.get("language"), c.get("title"))
        if key not in seen:
            seen.add(key)
            unique_courses.append(c)

    for c in unique_courses:
        is_curr = c.get("is_current", False)
        status = "[bold bright_green]● active[/]" if is_curr else "[dim]○ enrolled[/dim]"
        title = c.get('title', 'Unknown')
        code = c.get('language', '').upper()
        xp = f"{c.get('xp', 0):,} XP"
        table.add_row(status, title, code, xp)

    console.print(table)
    console.print(f"[dim]{SECTION_SEP}[/dim]")


def render_profile(profile: Dict[str, Any]) -> None:
    username = profile.get("username", "Unknown")
    name = profile.get("name") or profile.get("fullname") or username
    bio = profile.get("bio") or "[dim italic]No bio set[/]"
    streak = profile.get("streak", 0)
    total_xp = profile.get("totalXp", profile.get("contribution_points", 0))
    learning_lang = profile.get("learningLanguage", "Unknown").upper()
    from_lang = profile.get("fromLanguage", "en").upper()
    creation_date = profile.get("creationDate") or profile.get("created")

    created_str = "Unknown"
    if creation_date:
        try:
            if isinstance(creation_date, (int, float)):
                ts = creation_date if creation_date < 1e11 else creation_date / 1000.0
                from datetime import datetime
                created_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            else:
                created_str = str(creation_date)[:10]
        except Exception:
            created_str = str(creation_date)[:10]

    console.print()
    console.print(f"[bold bright_cyan]👤  @{username}[/]  [dim]{name}[/dim]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print(f"  [dim]Streak[/dim]        [bold bright_yellow]{streak} days[/]")
    console.print(f"  [dim]Total XP[/dim]      [bold bright_magenta]{total_xp:,} XP[/]")
    console.print(f"  [dim]Learning[/dim]      [bold bright_green]{learning_lang}[/]  [dim]from {from_lang}[/dim]")
    console.print(f"  [dim]Member since[/dim]  [white]{created_str}[/]")
    console.print(f"  [dim]Bio[/dim]           {bio}")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print()


def render_friends_table(friends: List[Dict[str, Any]]) -> None:
    if not friends:
        print_info("You are not following any friends yet.")
        return

    table = _make_table("FRIENDS & FOLLOWING")
    table.add_column("User", style="bold white")
    table.add_column("Total XP", justify="right", style="bright_magenta")
    table.add_column("Streak", justify="center", style="bright_yellow")

    for f in friends:
        username = f.get("username", "Unknown")
        name = f.get("name")
        display = f"@{username}" if not name else f"{name} (@{username})"
        xp = f"{f.get('points', 0):,} XP"
        streak = f"{f.get('streak', 0)} days" if "streak" in f else "—"
        table.add_row(display, xp, streak)

    console.print(table)
    console.print(f"[dim]{SECTION_SEP}[/dim]")


def render_hearts(hearts_data: Dict[str, Any]) -> None:
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
    console.print()
    console.print("[bold bright_cyan]⚙️  CONFIG[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    for k, v in config_data.items():
        console.print(f"  [dim]{k:<18}[/] [white]{v}[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print()


# --- HELP MENU RENDERER ---

def render_help() -> None:
    """Categorized help — spacing + color only, no borders."""
    console.print()
    console.print("[bold bright_cyan]🦉  DUOLINGO COMMANDS[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")

    sections = [
        ("AUTOMATION", "auto-solve & interactive practice", [
            ("auto", "Automate practice lessons  [dim](-s, -g, -x, -L, -m)[/dim]  ·  fast pauses between lessons"),
            ("practice", "Interactive lesson in the terminal  [dim](-l)[/dim]"),
        ]),
        ("STATS & PROGRESS", "streak, courses, and dashboard", [
            ("status", "Overview dashboard — streak, course, XP, gems"),
            ("calendar", "Streak heatmap & XP history  [dim](-d)[/dim]"),
            ("courses", "List enrolled languages and total XP"),
        ]),
        ("PROFILE & SOCIAL", "account and network", [
            ("profile", "User profile card and stats"),
            ("friends", "Friends and following leaderboard"),
            ("leaderboard", "XP leaderboard — you + friends ranked  [dim](weekly XP)[/dim]"),
            ("whoami", "Show current authenticated account"),
        ]),
        ("STORE & SESSION", "shop, streak freeze, and settings", [
            ("shop", "Browse shop items and gem balance"),
            ("freeze", "Buy & equip Streak Freeze  [dim](200 gems)[/dim]"),
            ("hearts", "Show heart / health status"),
            ("switch <lang>", "Switch active course  [dim](e.g. duo switch es)[/dim]"),
            ("config", "Show resolved config & token expiry"),
            ("export", "Export progress to JSON/CSV  [dim](-f, -o)[/dim]"),
            ("login / logout", "Connect or disconnect Duolingo account"),
            ("shell", "Launch interactive REPL shell"),
        ]),
    ]

    for sec_title, sec_desc, cmds in sections:
        console.print(f"\n  [bold bright_yellow]{sec_title}[/]  [dim]· {sec_desc}[/dim]")
        for cmd_name, cmd_desc in cmds:
            console.print(f"    [bold bright_green]{cmd_name:<18}[/] [white]{cmd_desc}[/]")

    console.print("\n[bold bright_cyan]💡  QUICK EXAMPLES[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print("  [bright_green]duo[/]                    Show status dashboard")
    console.print("  [bright_green]duo auto -g[/]            Complete daily goal automatically")
    console.print("  [bright_green]duo auto -L -m 20[/]       Run up to 20 sessions then stop")
    console.print("  [bright_green]duo practice -l es[/]     Interactive Spanish lesson")
    console.print("  [bright_green]duo switch de[/]          Switch course to German")
    console.print("  [bright_green]duo shell[/]               Enter interactive shell")
    console.print()


# --- PRACTICE & AUTO TUI COMPONENTS ---

def render_auto_header(lang: str, sessions: int, target_xp: Optional[int], until_goal: bool, loop: bool = False) -> None:
    if loop:
        goal_mode = "∞  Infinite loop"
    else:
        goal_mode = "Until daily goal" if until_goal else (f"Target: {target_xp} XP" if target_xp else f"{sessions} session(s)")
    console.print()
    console.print("[bold bright_green]⚡  AUTO PRACTICE[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print(f"  [dim]Language[/dim]  [bold bright_cyan]{lang.upper()}[/]   [dim]Mode[/dim]  [bold bright_yellow]{goal_mode}[/]")
    console.print("  [dim]Solving with randomized human-like pauses…[/dim]")
    if loop:
        console.print("  [dim]Runs until [bold]Ctrl+C[/] — longer break every 5 sessions.[/dim]")
    else:
        console.print("  [dim]Press [bold]Ctrl+C[/] to stop safely at any time.[/dim]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print()


def render_auto_challenge(session_idx: int, total_sessions: int, q_idx: int, total_q: int, prompt: str, answer: str, delay: float) -> None:
    sess_info = f"S{session_idx}" if total_sessions <= 1 else f"S{session_idx}/{total_sessions}"
    console.print(
        f"  [dim]›[/dim] [bold white][{sess_info}  Q{q_idx:02d}/{total_q:02d}][/] "
        f"[white]{prompt[:44]}[/] [dim]→[/] [bold bright_green]{answer[:36]}[/] "
        f"[dim]{delay:.1f}s[/dim]"
    )


def render_auto_session_result(session_idx: int, xp_gained: int, streak_extended: bool, total_xp_earned: int) -> None:
    streak_msg = "[bold bright_green]🔥 streak kept[/]" if streak_extended else ""
    console.print(
        f"  [bold bright_green]✔ Session {session_idx} done[/]  "
        f"[bold bright_yellow]+{xp_gained} XP[/]  {streak_msg}  "
        f"[dim](total +{total_xp_earned} XP)[/dim]"
    )
    console.print()


def render_auto_summary(sessions_completed: int, total_xp: int, streak_days: int, streak_extended: bool) -> None:
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


def _hearts_bar(hearts: int) -> str:
    max_hearts = 5
    return " ".join(
        "[bold bright_red]♥[/]" if i < hearts else "[dim]♡[/]" for i in range(max_hearts)
    )


def _combo_badge(combo: int) -> str:
    return f"  [bold bright_yellow]🔥 ×{combo}[/]" if combo >= 2 else ""


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
    """Single question — header line + prompt + numbered choices, no borders."""
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


def render_answer_result(is_correct: bool, correct_answer: str, gained_xp: int = 10) -> None:
    if is_correct:
        console.print(f"\n[bold bright_green]✔ Correct[/]  [dim]+{gained_xp} XP[/dim]  🎉")
    else:
        console.print(f"\n[bold bright_red]✘ Incorrect[/]  [dim]answer:[/dim] [bold green]{correct_answer}[/]")


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


def render_leaderboard(entries: List[Dict[str, Any]]) -> None:
    """Display a ranked XP leaderboard for self + friends."""
    if not entries:
        print_info("No leaderboard data available. Make sure you follow some friends.")
        return

    console.print()
    console.print("[bold bright_cyan]🏆  LEADERBOARD[/]  [dim]· you + friends · sorted by weekly XP[/dim]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")

    table = _make_table("")
    table.title = None
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("User", style="bold white")
    table.add_column("Weekly XP", justify="right", style="bold bright_green")
    table.add_column("Total XP", justify="right", style="bright_magenta")
    table.add_column("Streak", justify="center", style="bright_yellow")

    for e in entries:
        rank = e["rank"]
        username = e.get("username", "?")
        name = e.get("name") or username
        display = f"[bold bright_yellow]→ @{username}[/]" if e.get("is_self") else f"@{username}"
        if name and name != username:
            display = (f"[bold bright_yellow]→ {name}[/]" if e.get("is_self") else name) + f" [dim]@{username}[/dim]"

        # Rank medal for top 3
        rank_str = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))

        weekly = e.get("xp_this_week", 0)
        total = e.get("total_xp", 0)
        streak = e.get("streak", 0)

        table.add_row(
            rank_str,
            display,
            f"+{weekly:,} XP" if weekly else "—",
            f"{total:,} XP",
            f"{streak}d" if streak else "—",
        )

    console.print(table)
    console.print(f"[dim]{SECTION_SEP}[/dim]")
    console.print()
