"""
Main CLI entrypoint and interactive shell loop for duo-cli in English.
"""

import functools
import os
import re
import shlex
import sys
from typing import Callable, Optional

import click
from rich.prompt import Prompt

from .api import DuoAPIError, DuoClient
from .config import (
    CONFIG_FILE,
    clear_config,
    get_jwt,
    get_jwt_expiry,
    get_preset_language,
    get_username,
    is_authenticated,
    set_credentials,
    set_preset_language,
)
from .practice import AutoPractice, PracticeSession
from .ui import (
    DIVIDER_LINE,
    __version__ as UI_VERSION,
    console,
    print_banner,
    print_error,
    print_info,
    print_success,
    print_warning,
    render_calendar,
    render_config,
    render_courses_table,
    render_friends_table,
    render_hearts,
    render_help,
    render_leaderboard,
    render_profile,
    render_shop,
    render_status,
)


# ---------------------------------------------------------------------------
# Small extensibility helpers — keep command bodies focused on business logic
# ---------------------------------------------------------------------------

_LANG_RE = re.compile(r"^[a-z]{2,3}(-[a-z]{2,4})?$", re.IGNORECASE)
_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{2,50}$")


def _is_valid_lang(lang: str) -> bool:
    return bool(lang and _LANG_RE.match(lang))


def _require_auth(func: Callable) -> Callable:
    """Decorator for commands that need a logged-in user — keeps auth checks DRY."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            print_error("Not authenticated. Run 'duo login'.")
            return None
        return func(*args, **kwargs)

    return wrapper


def _check_jwt_expiry_warning() -> None:
    """Print warning if JWT expires within 7 days."""
    try:
        exp = get_jwt_expiry()
        if exp:
            import datetime

            days_left = (datetime.datetime.fromtimestamp(exp) - datetime.datetime.now()).days
            if days_left < 7:
                print_warning(f"JWT expires in {days_left} days — refresh it via 'duo login' soon!")
            elif days_left < 0:
                print_warning("JWT appears expired — run 'duo login' with a fresh token.")
    except Exception:
        pass


def _parse_shell_auto_args(args: list[str]) -> dict:
    """Parse `auto` flags inside the interactive shell (simple, no click re-parse)."""
    params: dict = {
        "until_goal": "-g" in args or "--until-goal" in args,
        "loop": "-L" in args or "--loop" in args,
        "dry_run": "--dry-run" in args,
        "sessions": 1,
        "target_xp": None,
        "lang": None,
        "max_sessions": None,
    }
    for i, a in enumerate(args):
        if a in ("-s", "--sessions") and i + 1 < len(args) and args[i + 1].isdigit():
            params["sessions"] = int(args[i + 1])
        elif a in ("-x", "--target-xp") and i + 1 < len(args) and args[i + 1].isdigit():
            params["target_xp"] = int(args[i + 1])
        elif a in ("-l", "--lang") and i + 1 < len(args):
            params["lang"] = args[i + 1]
        elif a in ("-m", "--max-sessions") and i + 1 < len(args) and args[i + 1].isdigit():
            params["max_sessions"] = int(args[i + 1])
    return params


class DuoGroup(click.Group):
    """Custom Click Group with beautiful Rich-formatted help output and graceful error handling."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        print_banner()
        render_help()

    def resolve_command(self, ctx: click.Context, args):
        """Intercept unknown commands / bad usage and show friendly TUI error instead of raw traceback."""
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as e:
            print_banner()
            print_error(str(e))
            if args:
                attempted = args[0].lstrip("-")
                if "No such command" in str(e) and attempted:
                    import difflib

                    all_cmds = list(self.commands.keys())
                    matches = difflib.get_close_matches(attempted, all_cmds, n=3, cutoff=0.6)
                    if matches:
                        console.print(
                            f"[dim]Did you mean:[/] [bold bright_green]{', '.join(matches)}[/][dim] ?[/dim]"
                        )
            console.print("[dim]Run [bold]duo help[/] or [bold]duo --help[/] to see all commands.[/dim]\n")
            ctx.exit(2)


@click.group(cls=DuoGroup, invoke_without_command=True)
@click.option("-v", "--version", is_flag=True, help="Show application version.")
@click.option("--verbose", is_flag=True, help="Enable verbose debug logging.")
@click.pass_context
def cli(ctx: click.Context, version: bool, verbose: bool) -> None:
    """🦉 Duo-CLI: Modern Duolingo Terminal Client & Automated Learning Engine."""
    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
        os.environ["DUO_DEBUG"] = "1"
    if version:
        console.print(f"[bold bright_green]duo-cli[/] version [bold bright_yellow]{UI_VERSION}[/]")
        ctx.exit()

    if ctx.invoked_subcommand is None:
        print_banner()
        if not is_authenticated():
            print_warning("No active login found. Run 'duo login' to connect your Duolingo account.")
            return

        try:
            client = DuoClient()
            user_data = client.verify_auth()
            streak_info = client.get_streak_info()
            render_status(streak_info, user_data)
            _check_jwt_expiry_warning()
        except DuoAPIError as e:
            print_error(str(e))
        except Exception as e:
            print_error(f"Unexpected error: {e}")


@cli.command("login")
@click.option("--username", "-u", help="Duolingo username")
@click.option("--jwt", "-j", help="Duolingo JWT session token")
def login_cmd(username: str, jwt: str) -> None:
    """Log in with your Duolingo credentials and JWT token."""
    print_banner()
    if not username:
        username = Prompt.ask("[bold bright_cyan]Enter Duolingo username[/]").strip()
        # Limit length to prevent abuse
        username = username[:100]
    if not jwt:
        console.print(
            "\n[bold bright_yellow]ℹ How to get your JWT token in Chrome / Edge / Firefox:[/]\n"
            "  1. Open [underline cyan]https://www.duolingo.com[/] in your browser (logged in)\n"
            "  2. Press [bold]F12[/] -> [bold]Console[/]\n"
            "  3. Paste: [green]copy(document.cookie.split('; ').find(r => r.startsWith('jwt_token='))?.split('=')[1])[/]\n"
            "  4. Press [bold]Enter[/] (token is automatically copied to your clipboard)\n"
        )
        jwt = Prompt.ask("[bold bright_cyan]Paste JWT token (Ctrl+V)[/]").strip()
        jwt = jwt[:5000]

    if not username or not jwt:
        print_error("Both username and JWT token are required.")
        return

    # Early format checks before touching disk — give user clear feedback
    if not _USERNAME_RE.match(username):
        print_error("Invalid username — use 2-50 chars: letters, digits, . _ -")
        return
    # Don't echo the token itself in errors
    if "\r" in jwt or "\n" in jwt:
        print_error("Invalid JWT token — contains line breaks")
        return

    try:
        set_credentials(username, jwt)
        client = DuoClient()
        user_info = client.verify_auth(force_refresh=True)
        print_success(f"Successfully logged in as [bold bright_white]@{user_info.get('username')}[/]! 🔥 Streak: {user_info.get('streak', 0)} Days.")

        # Detect enrolled courses and learning language
        active_lang = (user_info.get("learningLanguage") or "").lower()
        courses = []
        try:
            courses = client.get_courses(force_refresh=True)
        except Exception:
            pass

        if courses:
            console.print("\n[bold bright_cyan]📚 Enrolled Courses:[/]")
            for i, c in enumerate(courses, 1):
                cur_marker = " [bold bright_green](Active)[/]" if c.get("is_current") else ""
                console.print(f"  [bold bright_yellow]{i}.[/] {c.get('title', 'Unknown')} [{c.get('language', '').upper()}]{cur_marker}")

            if active_lang:
                set_preset_language(active_lang)
                print_info(f"Default practice course set to: [bold bright_cyan]{active_lang.upper()}[/] (use 'duo switch <lang>' to change)")
            else:
                choice = Prompt.ask("\n[bold bright_cyan]Select default course number (or press Enter for course 1)[/]", default="1").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(courses):
                    chosen = courses[int(choice) - 1]["language"].lower()
                    set_preset_language(chosen)
                    print_success(f"Default course set to: [bold bright_cyan]{chosen.upper()}[/]")
        elif active_lang:
            set_preset_language(active_lang)
            print_info(f"Default practice course set to: [bold bright_cyan]{active_lang.upper()}[/]")
        else:
            print_warning("No active enrolled courses detected on this account.")
            manual = Prompt.ask("[bold bright_cyan]Enter target language code to learn (e.g. en, es, de, fr, or press Enter to skip)[/]", default="").strip().lower()
            if manual and _is_valid_lang(manual):
                set_preset_language(manual)
                print_success(f"Default course set to: [bold bright_cyan]{manual.upper()}[/]")
    except Exception as e:
        # Never leak the raw token in error output
        msg = str(e)
        if jwt and jwt[:20] in msg:
            msg = msg.replace(jwt, "[REDACTED]")
            msg = msg.replace(jwt[:30], "[REDACTED]")
        print_error(f"Authentication failed: {msg}")


@cli.command("logout")
def logout_cmd() -> None:
    """Log out and remove stored credentials from disk."""
    clear_config()
    print_success("You have been logged out and local credentials were removed.")


@cli.command("whoami")
def whoami_cmd() -> None:
    """Display currently authenticated user."""
    if not is_authenticated():
        print_warning("Not authenticated. Run 'duo login'.")
        return
    u = get_username()
    try:
        client = DuoClient()
        user_data = client.verify_auth()
        print_info(f"Logged in as: [bold bright_green]@{user_data.get('username', u)}[/] (ID: {user_data.get('id')})")
    except Exception as e:
        print_error(f"Failed to verify session: {e}")


@cli.command("status")
@_require_auth
def status_cmd() -> None:
    """Show detailed streak, daily goals, and active language status."""
    try:
        client = DuoClient()
        user_data = client.verify_auth()
        streak_info = client.get_streak_info()
        render_status(streak_info, user_data)
        _check_jwt_expiry_warning()
    except Exception as e:
        print_error(f"Failed to load status: {e}")


@cli.command("courses")
@_require_auth
def courses_cmd() -> None:
    """List all enrolled languages and courses."""
    try:
        client = DuoClient()
        courses = client.get_courses()
        render_courses_table(courses)
    except Exception as e:
        print_error(f"Failed to load courses: {e}")


@cli.command("switch")
@click.argument("language_code")
def switch_cmd(language_code: str) -> None:
    """Switch active learning course (e.g. duo switch es)."""
    if not language_code:
        print_error("Usage: duo switch <language_code>  (e.g. duo switch es)")
        return
    if not _is_valid_lang(language_code):
        print_error(f"Invalid language code: {language_code!r} — expected like 'es', 'de', 'fr'")
        return
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return

    lang = language_code.lower()
    old = get_preset_language()
    try:
        client = DuoClient()
        # Always persist the choice locally so practice/auto remember it.
        set_preset_language(lang)
        success = client.switch_language(lang)
        if success:
            print_success(
                f"Switched active course to: [bold bright_cyan]{lang.upper()}[/]"
                + (f"  (was {old.upper()})" if old and old != lang else "")
                + "  [dim]— saved as local preset[/dim]"
            )
        else:
            print_warning(
                f"Server didn't confirm the switch, but [bold bright_cyan]{lang.upper()}[/] "
                f"is saved as your local preset for practice/auto."
            )
    except Exception as e:
        print_error(f"Error switching course: {e}")


@cli.command("calendar")
@click.option("--days", "-d", default=14, help="Number of past days to display (default: 14)")
@_require_auth
def calendar_cmd(days: int) -> None:
    """Show calendar activity and streak history."""
    # Clamp days to sane range to avoid huge loops / abuse
    try:
        days = int(days)
    except Exception:
        print_error("Invalid --days value — must be an integer")
        return
    if not 1 <= days <= 365:
        print_error("Invalid --days value — must be between 1 and 365")
        return
    try:
        client = DuoClient()
        cal = client.get_streak_calendar(days)
        render_calendar(cal, days=days)
    except Exception as e:
        print_error(f"Failed to load calendar: {e}")


@cli.command("shop")
@_require_auth
def shop_cmd() -> None:
    """Browse Duolingo shop items and gem pricing."""
    try:
        client = DuoClient()
        items = client.get_shop_items()
        info = client.get_streak_info()
        render_shop(items, info.get("gems", 0))
    except Exception as e:
        print_error(f"Failed to load shop: {e}")


@cli.command("freeze")
@_require_auth
def freeze_cmd() -> None:
    """Purchase and equip Streak Freeze item."""
    try:
        client = DuoClient()
        client.buy_streak_freeze()
        print_success("Streak Freeze purchased and equipped! 🛡️")
    except Exception as e:
        print_error(f"Purchase failed: {e}")


@cli.command("profile")
@click.argument("username", required=False)
def profile_cmd(username: Optional[str]) -> None:
    """View user profile stats and achievements."""
    if username and (len(username) > 50 or not _USERNAME_RE.match(username)):
        print_error("Invalid username format")
        return
    try:
        client = DuoClient()
        if username:
            data = client.get_public_user(username)
        else:
            if not is_authenticated():
                print_error("Provide a username or run 'duo login'.")
                return
            data = client.get_full_user_data()
        render_profile(data)
    except Exception as e:
        print_error(f"Failed to load profile: {e}")


@cli.command("friends")
@_require_auth
def friends_cmd() -> None:
    """View list of friends and followers."""
    try:
        client = DuoClient()
        friends = client.get_friends()
        render_friends_table(friends)
    except Exception as e:
        print_error(f"Failed to load friends: {e}")


@cli.command("leaderboard")
@_require_auth
def leaderboard_cmd() -> None:
    """Show weekly XP leaderboard.
    
    Retrieves the current user's profile and their friends list to build and render
    a unified scoreboard ranked by weekly XP contributions.
    """
    try:
        client = DuoClient()
        entries = client.get_leaderboard()
        render_leaderboard(entries)
    except Exception as e:
        print_error(f"Failed to load leaderboard: {e}")


@cli.command("hearts")
@_require_auth
def hearts_cmd() -> None:
    """Show heart / health status."""
    try:
        client = DuoClient()
        data = client.get_hearts()
        render_hearts(data)
    except Exception as e:
        print_error(f"Failed to load hearts: {e}")


@cli.command("config")
def config_cmd() -> None:
    """Show resolved config and token expiry."""
    import datetime

    jwt = get_jwt()
    username = get_username()
    preset = get_preset_language()
    expiry = get_jwt_expiry()
    expiry_str = "unknown"
    if expiry:
        try:
            dt = datetime.datetime.fromtimestamp(expiry)
            days_left = (dt - datetime.datetime.now()).days
            expiry_str = f"{dt.strftime('%Y-%m-%d %H:%M')} ({days_left} days left)"
            if days_left < 3:
                expiry_str += " ⚠ expires soon!"
        except Exception:
            expiry_str = str(expiry)
    jwt_masked = f"{jwt[:12]}...{jwt[-8:]}" if jwt and len(jwt) > 20 else ("set" if jwt else "not set")
    # detect source
    import os as _os

    src = "config.json"
    if _os.getenv("DUOLINGO_JWT") or _os.getenv("DUOLINGO_JWT_TOKEN"):
        src = "env var"
    elif (__import__("pathlib").Path.cwd() / ".env").exists():
        # check if jwt came from .env (approx)
        src = ".env / config.json"
    data = {
        "username": username or "not set",
        "jwt": jwt_masked,
        "jwt_source": src,
        "jwt_expiry": expiry_str,
        "preset_language": preset or "not set",
        "config_file": str(CONFIG_FILE),
        "authenticated": str(is_authenticated()),
    }
    render_config(data)


@cli.command("export")
@click.option("--format", "-f", "fmt", type=click.Choice(["json", "csv"]), default="json", help="Export format (json/csv)")
@click.option("--output", "-o", default=None, help="Output file (default: duo-export.<fmt>)")
@click.option("--days", "-d", default=30, type=int, help="Days of calendar history to include (1-365)")
@_require_auth
def export_cmd(fmt: str, output: Optional[str], days: int) -> None:
    """Export progress (courses, calendar, profile) to file."""
    import csv as _csv
    import json as _json
    from pathlib import Path as _Path

    if not 1 <= days <= 365:
        print_error("Invalid --days value — must be between 1 and 365")
        return
    try:
        client = DuoClient()
        user_data = client.get_full_user_data()
        courses = client.get_courses()
        calendar = client.get_streak_calendar(days)
        streak_info = client.get_streak_info()
        payload = {
            "username": user_data.get("username"),
            "totalXp": user_data.get("totalXp"),
            "streak": user_data.get("streak"),
            "courses": courses,
            "calendar": calendar,
            "streak_info": streak_info,
            "exported_at": __import__("datetime").datetime.now().isoformat(),
        }
        out_path = _Path(output) if output else _Path(f"duo-export.{fmt}")
        if fmt == "json":
            out_path.write_text(_json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            # CSV: flatten calendar
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = _csv.writer(f)
                w.writerow(["date", "day", "is_active", "xp"])
                for d in calendar:
                    w.writerow([d["date"], d["day_name"], d["is_active"], d["xp"]])
                w.writerow([])
                w.writerow(["course", "language", "xp", "is_current"])
                for c in courses:
                    w.writerow([c.get("title"), c.get("language"), c.get("xp"), c.get("is_current")])
        print_success(f"Exported to [bold bright_white]{out_path.resolve()}[/] ({fmt})")
    except Exception as e:
        print_error(f"Export failed: {e}")


@cli.command("practice")
@click.option("--lang", "-l", default=None, help="Target language (e.g. en, es, de, fr)")
@click.option("--dry-run", is_flag=True, help="Simulate lesson without submitting XP to server")
def practice_cmd(lang: Optional[str], dry_run: bool) -> None:
    """Start an interactive practice session to earn XP and maintain streak."""
    if lang and not _is_valid_lang(lang):
        print_error(f"Invalid language code: {lang!r}")
        return
    client = DuoClient()

    target_lang = lang or get_preset_language()
    if not target_lang and client.is_authenticated():
        target_lang = client.get_learning_language()
        if not target_lang:
            try:
                courses = client.get_courses()
                if courses:
                    console.print("\n[bold bright_cyan]Select course for practice:[/]")
                    for i, c in enumerate(courses, 1):
                        console.print(f"  [bold bright_yellow]{i}.[/] {c.get('title', 'Unknown')} [{c.get('language', '').upper()}]")
                    ans = Prompt.ask("[bold bright_cyan]Choice (or enter language code)[/]", default="1").strip().lower()
                    if ans.isdigit() and 1 <= int(ans) <= len(courses):
                        target_lang = courses[int(ans) - 1]["language"]
                    elif _is_valid_lang(ans):
                        target_lang = ans
            except Exception:
                pass

    if not target_lang:
        target_lang = Prompt.ask("[bold bright_cyan]Enter target language code (e.g. en, es, de, fr)[/]").strip().lower()
        if not _is_valid_lang(target_lang):
            print_error("Invalid language code. Practice aborted.")
            return
        set_preset_language(target_lang)

    if dry_run:
        print_warning("Dry run — XP will NOT be submitted.")
    if not client.is_authenticated():
        print_warning("Running in offline mode. Run 'duo login' to sync XP with Duolingo servers.")
    session = PracticeSession(client, target_lang, dry_run=dry_run)
    session.run()


@cli.command("auto")
@click.option("--sessions", "-s", default=1, type=int, help="Number of practice sessions to complete (default: 1)")
@click.option("--target-xp", "-x", default=None, type=int, help="Target XP to earn before stopping")
@click.option("--until-goal", "-g", is_flag=True, help="Run practice sessions until today's daily XP goal is reached")
@click.option("--loop", "-L", is_flag=True, help="Run practice sessions forever (until Ctrl+C)")
@click.option("--lang", "-l", default=None, help="Target language code (e.g. en, es, de, fr)")
@click.option("--max-sessions", "-m", default=None, type=int, help="Hard cap on number of sessions (recommended with -L to avoid bans)")
@click.option("--dry-run", is_flag=True, help="Simulate sessions without submitting XP")
def auto_cmd(
    sessions: int,
    target_xp: Optional[int],
    until_goal: bool,
    loop: bool,
    lang: Optional[str],
    max_sessions: Optional[int],
    dry_run: bool,
) -> None:
    """Automate Duolingo practice sessions with natural delays to earn XP and keep streak."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
    if lang and not _is_valid_lang(lang):
        print_error(f"Invalid language code: {lang!r}")
        return
    # Clamp numeric inputs to sane ranges to avoid abuse / hangs
    try:
        if sessions is not None and not 1 <= int(sessions) <= 1000:
            print_error("Invalid --sessions value — must be between 1 and 1000")
            return
        if target_xp is not None and not 1 <= int(target_xp) <= 10000:
            print_error("Invalid --target-xp value — must be between 1 and 10000")
            return
        if max_sessions is not None and not 1 <= int(max_sessions) <= 1000:
            print_error("Invalid --max-sessions value — must be between 1 and 1000")
            return
    except Exception as e:
        print_error(f"Invalid numeric option: {e}")
        return
    if loop:
        print_warning(
            "[bold yellow]⚠ Endless auto (-L) can look like botting to Duolingo and risks a ban. "
            "Use -m/--max-sessions to set a limit.[/]"
        )
    if dry_run:
        print_warning("Dry run — XP will NOT be submitted.")
    client = DuoClient()

    target_lang = lang or get_preset_language()
    if not target_lang:
        target_lang = client.get_learning_language()
    if not target_lang:
        try:
            courses = client.get_courses()
            if courses:
                target_lang = courses[0]["language"]
        except Exception:
            pass
    if not target_lang:
        target_lang = Prompt.ask("[bold bright_cyan]Enter target language code for auto practice (e.g. en, es, de, fr)[/]").strip().lower()
        if not _is_valid_lang(target_lang):
            print_error("Invalid language code. Aborted.")
            return
        set_preset_language(target_lang)

    bot = AutoPractice(
        client=client,
        lang_code=target_lang,
        max_sessions=max_sessions,
        dry_run=dry_run,
    )
    bot.run(sessions=sessions, target_xp=target_xp, until_goal=until_goal, loop=loop)


@cli.command("help")
def help_cmd() -> None:
    """Display comprehensive help guide and command list."""
    print_banner()
    render_help()


@cli.command("shell")
def shell_cmd() -> None:
    """Launch interactive Duo REPL shell."""
    print_banner()
    # Initial display data — will be refreshed each loop iteration
    _initial_client = DuoClient()
    _initial_user = _initial_client.username or get_username() or "guest"
    _initial_preset = get_preset_language() or _initial_client.get_learning_language() or "none"

    console.print()
    console.print("[bold bright_green]🦉 DUO INTERACTIVE SHELL[/]")
    console.print(f"[dim green]{DIVIDER_LINE}[/]")
    console.print(f"  Active User : [bold bright_white]@{_initial_user}[/]   Course: [bold bright_cyan]{_initial_preset.upper()}[/]")
    console.print("  Type 'help' for commands, 'exit' to quit.")
    console.print(f"[dim green]{DIVIDER_LINE}[/]\n")

    cmd_map = {
        "status": status_cmd,
        "courses": courses_cmd,
        "calendar": calendar_cmd,
        "shop": shop_cmd,
        "freeze": freeze_cmd,
        "hearts": hearts_cmd,
        "config": config_cmd,
        "export": export_cmd,
        "leaderboard": leaderboard_cmd,
        "switch": switch_cmd,
        "profile": profile_cmd,
        "friends": friends_cmd,
        "practice": practice_cmd,
        "auto": auto_cmd,
        "whoami": whoami_cmd,
        "help": help_cmd,
    }

    while True:
        try:
            # Refresh username/preset each iteration so switch/login reflect immediately
            cur_user = get_username() or "guest"
            cur_preset = get_preset_language() or _initial_client.get_learning_language() or "none"
            prompt_str = f"[bold bright_green]🦉 duo:{cur_user}/{cur_preset}[/] > "
            raw = Prompt.ask(prompt_str).strip()
            if not raw:
                continue
            # Shell safety: hard cap on input length and reject control chars
            if len(raw) > 500:
                print_error("Input too long — max 500 chars")
                continue
            if "\r" in raw or "\n" in raw or "\0" in raw:
                print_error("Invalid input — control characters not allowed")
                continue

            try:
                parts = shlex.split(raw, posix=True)
            except ValueError as e:
                print_error(f"Could not parse input: {e}")
                continue
            if not parts:
                continue
            cmd_name = parts[0].lower()
            # Allow only known commands plus shell builtins — no OS execution
            args = parts[1:]
            # Truncate args to prevent abuse
            if len(args) > 20:
                print_error("Too many arguments — max 20")
                continue

            if cmd_name in ["exit", "quit", "q"]:
                console.print("[bold yellow]Goodbye! Happy learning! 🦉[/]")
                break
            elif cmd_name == "clear":
                console.clear()
            elif cmd_name in ["help", "?"]:
                render_help()
            elif cmd_name in cmd_map:
                try:
                    ctx = click.Context(cmd_map[cmd_name])
                    if cmd_name == "practice":
                        # practice [lang] [--dry-run]
                        p_lang = None
                        p_dry = "--dry-run" in args
                        filtered = [a for a in args if a != "--dry-run"]
                        if filtered:
                            p_lang = filtered[0]
                        ctx.invoke(cmd_map[cmd_name], lang=p_lang, dry_run=p_dry)
                    elif cmd_name == "profile" and args:
                        ctx.invoke(cmd_map[cmd_name], username=args[0])
                    elif cmd_name == "auto":
                        p = _parse_shell_auto_args(args)
                        ctx.invoke(
                            cmd_map[cmd_name],
                            sessions=p["sessions"],
                            target_xp=p["target_xp"],
                            until_goal=p["until_goal"],
                            loop=p["loop"],
                            lang=p["lang"],
                            max_sessions=p["max_sessions"],
                            dry_run=p["dry_run"],
                        )
                    elif cmd_name == "switch" and args:
                        ctx.invoke(cmd_map[cmd_name], language_code=args[0])
                    else:
                        ctx.invoke(cmd_map[cmd_name])
                except Exception as ex:
                    print_error(f"Command failed: {ex}")
            else:
                print_error(f"Unknown command '{cmd_name}'. Type 'help' for command list.")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Exiting shell. Goodbye![/]")
            break


def main() -> None:
    """Entrypoint with crash-proof error handling — never dumps a traceback for user errors."""
    try:
        # standalone_mode=False lets us control rendering; click returns exit_code
        # for Exit exceptions instead of calling sys.exit.
        result = cli(standalone_mode=False)
        # click returns exit_code (int) for ctx.exit() paths; propagate it
        if isinstance(result, int) and result != 0:
            sys.exit(result)
    except click.ClickException as e:
        # Any remaining ClickException not caught by DuoGroup (e.g. BadParameter)
        # — show as friendly TUI error, no traceback.
        print_error(e.format_message())
        console.print("[dim]Run [bold]duo help[/] for usage.[/dim]\n")
        sys.exit(e.exit_code)
    except SystemExit as e:
        # Click uses SystemExit for --help / normal exits (code 0) and for
        # error exits (code 2). Re-raise correctly without extra output.
        raise
    except Exception as e:
        print_error(f"Fatal error: {e}")
        # Only dump traceback when explicitly debugging — never by default
        if os.getenv("DUO_DEBUG"):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
