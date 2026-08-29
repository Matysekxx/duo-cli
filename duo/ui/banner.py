"""
Banner and command help renderers.
"""

from .common import SECTION_SEP, console


def _get_version() -> str:
    """Single source of truth for version — duo.__version__ first (dev), then installed metadata."""
    try:
        from .. import __version__ as _v
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
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if pyproject.exists():
            m = re.search(r'version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
    except Exception:
        pass
    return "0.0.0"


UI_VERSION = _get_version()

_BANNER_ART = r"""[bold bright_green]
  ██████╗  ██╗   ██╗  ██████╗         ██████╗ ██╗     ██╗
  ██╔══██╗ ██║   ██║ ██╔═══██╗       ██╔════╝ ██║     ██║
  ██║  ██║ ██║   ██║ ██║   ██║ █████╗██║      ██║     ██║
  ██║  ██║ ██║   ██║ ██║   ██║ ╚════╝██║      ██║     ██║
  ██████╔╝ ╚██████╔╝ ╚██████╔╝       ╚██████╗ ███████╗██║
  ╚═════╝   ╚═════╝   ╚═════╝         ╚═════╝ ╚══════╝╚═╝[/]"""
_BANNER_TAGLINE = "  [dim cyan]─── Duolingo Terminal Interface & Automated Learning Engine ───[/]"


def _build_banner() -> str:
    version = _get_version()
    return f"{_BANNER_ART} [bold bright_yellow]v{version}[/]\n{_BANNER_TAGLINE}"


DUO_BANNER = _build_banner()


def print_banner() -> None:
    """Print the dynamic ASCII art banner."""
    console.print(_build_banner())


def render_help() -> None:
    """Categorized help — spacing + color only, no borders."""
    console.print()
    console.print("[bold bright_cyan]🦉  DUOLINGO COMMANDS[/]")
    console.print(f"[dim]{SECTION_SEP}[/dim]")

    sections = [
        ("AUTOMATION", "auto-solve & interactive practice", [
            ("auto", "Automate practice lessons  [dim](-s, -g, -x, -L, -m)[/dim]  ·  ~1s / q, 25-35s between"),
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
