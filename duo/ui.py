"""
Ultra-Clean, Modern Borderless TUI for duo-cli.
Designed with sleek horizontal dividers (box.HORIZONTALS) and clean CLI typography.
Eliminates all vertical side borders (no glyph width mismatch or broken box corners across any terminal).
"""

import sys
from typing import Any, Dict, List, Optional

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .api import get_flag

console = Console(file=sys.stdout, force_terminal=True, highlight=False)

DIVIDER_LINE = "─" * 56

# --- LOGO BANNER ---

DUO_BANNER = r"""[bold bright_green]
  ██████╗  ██╗   ██╗  ██████╗         ██████╗ ██╗     ██╗
  ██╔══██╗ ██║   ██║ ██╔═══██╗       ██╔════╝ ██║     ██║
  ██║  ██║ ██║   ██║ ██║   ██║ █████╗██║      ██║     ██║
  ██║  ██║ ██║   ██║ ██║   ██║ ╚════╝██║      ██║     ██║
  ██████╔╝ ╚██████╔╝ ╚██████╔╝       ╚██████╗ ███████╗██║
  ╚═════╝   ╚═════╝   ╚═════╝         ╚═════╝ ╚══════╝╚═╝[/] [bold bright_yellow]v1.0.0[/]
  [dim cyan]─── Duolingo Terminal Interface & Automated Learning Engine ───[/]
"""


def print_banner() -> None:
    console.print(DUO_BANNER)


def print_success(message: str) -> None:
    console.print(f"[bold bright_green][OK][/] {message}")


def print_error(message: str) -> None:
    console.print(f"[bold bright_red][ERROR][/] {message}")


def print_warning(message: str) -> None:
    console.print(f"[bold bright_yellow][WARN][/] {message}")


def print_info(message: str) -> None:
    console.print(f"[bold cyan][INFO][/] {message}")


def render_status(data: Dict[str, Any], user_data: Optional[Dict[str, Any]] = None) -> None:
    """Render a clean, modern, borderless status dashboard with dynamic streak effects."""
    streak = data.get("site_streak", 0)
    streak_extended = data.get("streak_extended_today", False)
    gems = data.get("gems", 0)
    total_xp = data.get("total_xp", 0)
    username = (user_data or {}).get("username") or data.get("username") or "Learner"

    curr_course = data.get("current_course", {})
    if curr_course:
        code = curr_course.get('learningLanguage', '').upper()
        title = curr_course.get('title', 'Unknown')
        course_display = f"{title} [{code}]"
    elif user_data:
        code = user_data.get("learningLanguage", "es").upper()
        course_display = f"Course [{code}]"
    else:
        course_display = "Spanish [ES]"

    streak_badge = "[bold white on dark_green] ✓ COMPLETED TODAY [/]" if streak_extended else "[bold white on dark_red] ⌛ INCOMPLETE [/]"
    div_color = "bright_green" if streak_extended else "bright_red"

    if streak_extended:
        effect_msg = f"[bold bright_green]🔥 Streak Active & Secured Today! Great job, @{username}![/]"
    else:
        effect_msg = f"[bold bright_red]⚠️  Streak expires tonight! Run 'duo auto' to keep it![/]"

    console.print()
    console.print("[bold bright_cyan]🦉 DUOLINGO DASHBOARD[/]")
    console.print(f"[{div_color}]{DIVIDER_LINE}[/]")
    console.print(f"  [bold bright_white]Course[/]        : [bold bright_cyan]{course_display}[/]")
    console.print(f"  [bold bright_white]Daily Streak[/]  : [bold bright_yellow]{streak} Days[/]   {streak_badge}")
    console.print(f"  [bold bright_white]Total XP[/]      : [bold bright_magenta]{total_xp:,} XP[/]")
    console.print(f"  [bold bright_white]Gems Balance[/]  : [bold bright_yellow]{gems:,} Gems[/]")
    console.print(f"[{div_color}]{DIVIDER_LINE}[/]")
    console.print(f"  {effect_msg}")
    console.print()


def render_calendar(calendar_data: List[Dict[str, Any]]) -> None:
    table = Table(
        title="[bold bright_cyan]ACTIVITY & STREAK (Last 14 Days)[/]",
        box=box.HORIZONTALS,
        header_style="bold bright_cyan",
        show_header=True
    )
    table.add_column("Date", style="bold white")
    table.add_column("Day", justify="center", style="bright_blue")
    table.add_column("Status", justify="center")
    table.add_column("XP Gained", justify="right", style="bright_magenta")

    for day in calendar_data:
        date_str = day["date"]
        day_name = day["day_name"]
        xp = f"+{day['xp']} XP" if day['xp'] > 0 else "[dim]0 XP[/dim]"
        status = "[bold bright_green]ACTIVE[/]" if day["is_active"] else "[dim]INACTIVE[/]"
        if day["is_today"]:
            date_str = f"[bold bright_yellow]👉 {date_str} (TODAY)[/]"

        table.add_row(date_str, day_name, status, xp)

    console.print(table)


def render_quests(quests: List[Dict[str, Any]]) -> None:
    table = Table(
        title="[bold bright_cyan]DAILY QUESTS & GOALS[/]",
        box=box.HORIZONTALS,
        header_style="bold bright_cyan",
        show_header=True
    )
    table.add_column("Quest / Goal", style="bold white")
    table.add_column("Progress", justify="center", style="bright_yellow")
    table.add_column("Status", justify="center")
    table.add_column("Reward", justify="right", style="bright_magenta")

    for q in quests:
        prog = f"{q['progress']}/{q['target']}"
        status = "[bold bright_green]✓ DONE[/]" if q["completed"] else "[dim]⌛ IN PROG[/]"
        reward_clean = str(q["reward"]).replace("🎁 ", "").replace("🔥 ", "").replace("💎 ", "")
        table.add_row(q["title"], prog, status, reward_clean)

    console.print(table)


def render_shop(items: List[Dict[str, Any]], user_gems: int) -> None:
    table = Table(
        title=f"[bold bright_cyan]DUOLINGO SHOP (Balance: {user_gems:,} Gems)[/]",
        box=box.HORIZONTALS,
        header_style="bold bright_cyan",
        show_header=True
    )
    table.add_column("Item", style="bold white")
    table.add_column("Price", justify="right", style="bold yellow")
    table.add_column("Description", style="white")

    for it in items:
        name = str(it["name"])
        cost = f"{it['cost']} Gems"
        table.add_row(name, cost, it["desc"])

    console.print(table)


def render_courses_table(courses: List[Dict[str, Any]]) -> None:
    if not courses:
        print_info("No enrolled courses found.")
        return

    table = Table(
        title="[bold bright_cyan]ENROLLED COURSES[/]",
        box=box.HORIZONTALS,
        header_style="bold bright_cyan",
        show_header=True
    )
    table.add_column("Status", justify="center")
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
        status = "[bold bright_green]ACTIVE[/]" if is_curr else "[dim]Enrolled[/]"
        title = c.get('title', 'Unknown')
        code = f"[{c.get('language', '').upper()}]"
        xp = f"{c.get('xp', 0):,} XP"

        table.add_row(status, title, code, xp)

    console.print(table)


def render_profile(profile: Dict[str, Any]) -> None:
    username = profile.get("username", "Unknown")
    name = profile.get("name") or profile.get("fullname") or username
    bio = profile.get("bio") or "[italic dim]No bio set[/]"
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
    console.print(f"[bold bright_cyan]👤 PROFILE: @{username}[/]")
    console.print(f"[dim cyan]{DIVIDER_LINE}[/]")
    console.print(f"  [bold bright_white]Full Name[/]     : [bold bright_white]{name}[/]")
    console.print(f"  [bold bright_white]Username[/]      : [bold bright_cyan]@{username}[/]")
    console.print(f"  [bold bright_white]Daily Streak[/]  : [bold bright_yellow]{streak} Days[/]")
    console.print(f"  [bold bright_white]Total XP[/]      : [bold bright_magenta]{total_xp:,} XP[/]")
    console.print(f"  [bold bright_white]Learning[/]      : [bold bright_green]{learning_lang}[/] (from {from_lang})")
    console.print(f"  [bold bright_white]Member Since[/]  : {created_str}")
    console.print(f"  [bold bright_white]Bio[/]           : {bio}")
    console.print(f"[dim cyan]{DIVIDER_LINE}[/]")
    console.print()


def render_vocabulary_table(vocab: List[Dict[str, Any]], limit: int = 50) -> None:
    if not vocab:
        print_info("No vocabulary data available for this language.")
        return

    table = Table(
        title=f"[bold bright_cyan]LEARNED VOCABULARY ({len(vocab)} words total)[/]",
        box=box.HORIZONTALS,
        header_style="bold bright_cyan",
        show_header=True
    )
    table.add_column("Word", style="bold bright_white")
    table.add_column("Category", style="bright_yellow")
    table.add_column("Strength", justify="center")
    table.add_column("Last Practiced", style="dim")

    for item in vocab[:limit]:
        word = item.get("word_string") or item.get("normalized_string") or "Unknown"
        pos = item.get("pos") or item.get("skill_title") or "Word"
        strength = float(item.get("strength_bars", item.get("strength", 1.0)))

        bars = int(strength * 4) if strength <= 1.0 else min(int(strength), 4)
        strength_bar = "[bold bright_green]" + "█" * bars + "[/][dim]" + "░" * (4 - bars) + "[/]"
        last_practiced = str(item.get("last_practiced", item.get("last_practiced_ms", "N/A")))[:10]

        table.add_row(word, str(pos), strength_bar, last_practiced)

    console.print(table)


def render_friends_table(friends: List[Dict[str, Any]]) -> None:
    if not friends:
        print_info("You are not following any friends yet.")
        return

    table = Table(
        title="[bold bright_cyan]FRIENDS & FOLLOWING[/]",
        box=box.HORIZONTALS,
        header_style="bold bright_cyan",
        show_header=True
    )
    table.add_column("User", style="bold white")
    table.add_column("Total XP", justify="right", style="bright_magenta")
    table.add_column("Streak", justify="center", style="bright_yellow")

    for f in friends:
        username = f.get("username", "Unknown")
        name = f.get("name")
        display = f"@{username}" if not name else f"{name} (@{username})"
        xp = f"{f.get('points', 0):,} XP"
        streak = f"{f.get('streak', 0)} Days" if "streak" in f else "—"

        table.add_row(display, xp, streak)

    console.print(table)


# --- HELP MENU RENDERER ---

def render_help() -> None:
    """Render a clean, modern, borderless categorized Help listing and Examples."""
    console.print()
    console.print("[bold bright_cyan]🦉 DUOLINGO COMMANDS[/]")
    console.print("[dim cyan]──────────────────────────────────────────────────────────────────[/]")

    sections = [
        ("AUTOMATION", "Auto-solve & interactive practice", [
            ("auto", "Automate practice lessons with natural pauses (Flags: -s, -g, -x, -L, --fast)"),
            ("practice", "Interactive full lesson practice session in terminal (Flags: -l)")
        ]),
        ("STATS & PROGRESS", "Streak, courses, and quests", [
            ("status", "Overview dashboard: streak, course, XP, gems"),
            ("calendar", "14-day streak visualizer & XP history heatmap (Flags: -d)"),
            ("courses", "List enrolled languages and total XP"),
            ("quests", "View daily quests and streak challenge goals"),
            ("vocab", "Browse learned vocabulary & word strength (Flags: -l, -n)")
        ]),
        ("PROFILE & USER", "Account info and friend network", [
            ("profile", "Display user profile card and stats"),
            ("friends", "View friends and following rankings"),
            ("whoami", "Show current authenticated account")
        ]),
        ("STORE & SESSION", "Shop items, streak freeze, and settings", [
            ("shop", "Browse shop items and gem balances"),
            ("freeze", "Purchase & equip Streak Freeze (200 gems)"),
            ("mute", "Snooze listening/speaking exercises (Flags: -m 15)"),
            ("switch <lang>", "Switch active learning course (e.g. duo switch es)"),
            ("login / logout", "Connect or disconnect Duolingo account"),
            ("shell", "Launch interactive Duo REPL shell")
        ])
    ]

    for sec_title, sec_desc, cmds in sections:
        console.print(f"\n  [bold bright_yellow]{sec_title}[/] [dim]• {sec_desc}[/]")
        for cmd_name, cmd_desc in cmds:
            console.print(f"    [bold bright_green]{cmd_name:<18}[/] [white]{cmd_desc}[/]")

    console.print("\n[bold bright_cyan]💡 QUICK EXAMPLES[/]")
    console.print("[dim cyan]──────────────────────────────────────────────────────────────────[/]")
    console.print("  [bright_green]duo[/]                    Show status dashboard")
    console.print("  [bright_green]duo auto -g[/]            Complete daily goal automatically")
    console.print("  [bright_green]duo auto -L[/]            Run practice sessions forever (Ctrl+C to stop)")
    console.print("  [bright_green]duo practice -l es[/]     Interactive Spanish lesson")
    console.print("  [bright_green]duo switch de[/]          Switch course to German")
    console.print("  [bright_green]duo shell[/]               Enter interactive shell")
    console.print()


# --- PRACTICE & AUTO TUI COMPONENTS ---

def render_auto_header(lang: str, sessions: int, target_xp: Optional[int], until_goal: bool, loop: bool = False) -> None:
    if loop:
        goal_mode = "♾ Infinite Loop (runs forever)"
    else:
        goal_mode = "Until Daily Goal is Met" if until_goal else (f"Target: {target_xp} XP" if target_xp else f"{sessions} Sessions")
    console.print()
    console.print("[bold bright_green]⚡ DUOLINGO AUTO PRACTICE BOT[/]")
    console.print(f"[dim green]{DIVIDER_LINE}[/]")
    console.print(f"  Language : [bold bright_cyan]{lang.upper()}[/] | Mode: [bold bright_yellow]{goal_mode}[/]")
    console.print("  [dim]Solving lessons automatically with natural randomized pauses...[/]")
    if loop:
        console.print("  [dim]Runs endlessly until you press [bold]Ctrl+C[/bold]. A longer break is taken every 5 sessions.[/]")
    else:
        console.print("  [dim]Press [bold]Ctrl+C[/bold] at any time to safely stop and save progress.[/]")
    console.print(f"[dim green]{DIVIDER_LINE}[/]")
    console.print()


def render_auto_challenge(session_idx: int, total_sessions: int, q_idx: int, total_q: int, prompt: str, answer: str, delay: float) -> None:
    sess_info = f"Session {session_idx}" if total_sessions <= 1 else f"Session {session_idx}/{total_sessions}"
    console.print(
        f"  [dim cyan]•[/] [bold bright_white][{sess_info} | Q {q_idx:02d}/{total_q:02d}][/] "
        f"[white]{prompt[:40]}[/] [dim]→[/] [bold bright_green]{answer[:35]}[/] "
        f"[dim]({delay:.1f}s)[/]"
    )


def render_auto_session_result(session_idx: int, xp_gained: int, streak_extended: bool, total_xp_earned: int) -> None:
    streak_msg = "🔥 Streak Maintained!" if streak_extended else ""
    console.print(
        f"  [bold bright_green]✔ Session {session_idx} Complete![/] "
        f"[bold bright_yellow]+{xp_gained} XP[/] {streak_msg} "
        f"[dim](Total earned this run: +{total_xp_earned} XP)[/]\n"
    )


def render_auto_summary(sessions_completed: int, total_xp: int, streak_days: int, streak_extended: bool) -> None:
    if streak_extended:
        status_str = f"[bold bright_yellow]🔥 {streak_days} Days[/] [bold bright_green](✓ Streak Active & Protected Today!)[/]"
        congrats = "  [bold bright_green]🎉 Great job! Your streak has been safely extended for today! 🚀[/]\n"
    else:
        status_str = f"[bold bright_yellow]{streak_days} Days[/]"
        congrats = ""

    console.print()
    console.print("[bold bright_green]⚡ AUTO PRACTICE SUMMARY[/]")
    console.print(f"[dim green]{DIVIDER_LINE}[/]")
    console.print("  [bold bright_white]Status[/]            : [bold bright_green]Completed Successfully![/]")
    console.print(f"  [bold bright_white]Sessions Finished[/] : [bold bright_cyan]{sessions_completed}[/]")
    console.print(f"  [bold bright_white]Total XP Gained[/]   : [bold bright_green]+{total_xp} XP[/]")
    console.print(f"  [bold bright_white]Current Streak[/]    : {status_str}")
    if congrats:
        console.print()
        console.print(congrats, end="")
    console.print(f"[dim green]{DIVIDER_LINE}[/]")
    console.print()


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
    """Render a single practice question as a beautiful Duolingo-style card."""
    flag = get_flag(lang_code)
    max_hearts = 5
    hearts_bar = " ".join(
        "[bold bright_red]♥[/]" if i < hearts else "[dim]♡[/]" for i in range(max_hearts)
    )
    combo_badge = f"  [bold bright_yellow]🔥 COMBO x{combo}[/]" if combo >= 2 else ""

    type_label = ""
    if q_type:
        pretty = {
            "translate": "Translation",
            "assist": "Translation",
            "select": "Multiple Choice",
            "gapFill": "Fill the Blank",
            "match": "Matching",
            "listen": "Listening",
            "speak": "Speaking",
        }.get(q_type, q_type)
        type_label = f"  [dim]{pretty}[/]"

    title = f"{flag} [bold bright_white]Question {q_idx}/{total_q}[/]{type_label}   {hearts_bar}{combo_badge}"

    lines = [f"[bold bright_white]{prompt}[/]"]
    if choices:
        lines.append("")
        for i, c in enumerate(choices, 1):
            lines.append(f"  [bold bright_yellow]{i}.[/] [white]{c}[/]")

    content = "\n".join(lines)
    console.print()
    console.print(
        Panel(
            content,
            title=title,
            border_style="bright_green",
            padding=(1, 2),
            expand=False,
        )
    )


def render_freeform_card(
    q_idx: int,
    total_q: int,
    prompt: str,
    hearts: int,
    combo: int,
    lang_code: Optional[str],
    q_type: str = "",
) -> None:
    """Render a free-text (typed) question as a clean card."""
    flag = get_flag(lang_code)
    max_hearts = 5
    hearts_bar = " ".join(
        "[bold bright_red]♥[/]" if i < hearts else "[dim]♡[/]" for i in range(max_hearts)
    )
    combo_badge = f"  [bold bright_yellow]🔥 COMBO x{combo}[/]" if combo >= 2 else ""
    title = f"{flag} [bold bright_white]Question {q_idx}/{total_q}[/]   {hearts_bar}{combo_badge}"
    console.print()
    console.print(
        Panel(
            f"[bold bright_white]{prompt}[/]\n\n[dim]Type your answer below ↓[/]",
            title=title,
            border_style="bright_cyan",
            padding=(1, 2),
            expand=False,
        )
    )


def render_match_panel(
    left_word: str,
    options: List[str],
    p_idx: int,
    total_pairs: int,
    hearts: int,
    combo: int,
    lang_code: Optional[str],
) -> None:
    """Render a single matching sub-round as a card."""
    flag = get_flag(lang_code)
    max_hearts = 5
    hearts_bar = " ".join(
        "[bold bright_red]♥[/]" if i < hearts else "[dim]♡[/]" for i in range(max_hearts)
    )
    combo_badge = f"  [bold bright_yellow]🔥 COMBO x{combo}[/]" if combo >= 2 else ""
    title = f"{flag} [bold bright_cyan]Match {p_idx}/{total_pairs}[/]   {hearts_bar}{combo_badge}"

    lines = [f"[bold bright_yellow]{left_word}[/]  [dim]⇄ choose its translation below[/]"]
    lines.append("")
    for i, o in enumerate(options, 1):
        lines.append(f"  [bold bright_yellow]{i}.[/] [white]{o}[/]")

    console.print()
    console.print(
        Panel(
            "\n".join(lines),
            title=title,
            border_style="bright_cyan",
            padding=(1, 2),
            expand=False,
        )
    )


def render_answer_result(is_correct: bool, correct_answer: str, gained_xp: int = 10) -> None:
    """Render a compact correct/incorrect feedback line after answering."""
    if is_correct:
        console.print(
            f"\n[bold bright_green]✔ Correct![/] [dim]+{gained_xp} XP[/] 🎉"
        )
    else:
        console.print(
            f"\n[bold bright_red]✖ Incorrect![/] [dim]Correct answer:[/] [bold green]{correct_answer}[/]"
        )
