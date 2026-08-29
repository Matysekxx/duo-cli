"""
Table renderers for courses, friends, shop, profile, and leaderboard.
"""

from typing import Any, Dict, List
from .common import SECTION_SEP, _make_table, console, print_info


def render_courses_table(courses: List[Dict[str, Any]]) -> None:
    """Render enrolled language courses."""
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


def render_shop(items: List[Dict[str, Any]], user_gems: int) -> None:
    """Render shop inventory and balance."""
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


def render_profile(profile: Dict[str, Any]) -> None:
    """Render user profile card."""
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
    """Render friends and following leaderboard."""
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
