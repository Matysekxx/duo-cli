"""
Main CLI entrypoint and interactive shell loop for duo-cli in English.
"""

import os
import sys
from typing import Optional

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import click
from rich.prompt import Prompt

from .api import DuoAPIError, DuoClient
from .config import (
    clear_config,
    get_jwt,
    get_preset_language,
    get_username,
    is_authenticated,
    set_credentials,
    set_preset_language,
)
from .practice import AutoPractice, PracticeSession
from .ui import (
    DIVIDER_LINE,
    console,
    print_banner,
    print_error,
    print_info,
    print_success,
    print_warning,
    render_calendar,
    render_courses_table,
    render_friends_table,
    render_help,
    render_profile,
    render_quests,
    render_shop,
    render_status,
    render_vocabulary_table,
)


class DuoGroup(click.Group):
    """Custom Click Group with beautiful Rich-formatted help output."""
    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        print_banner()
        render_help()


@click.group(cls=DuoGroup, invoke_without_command=True)
@click.option("-v", "--version", is_flag=True, help="Show application version.")
@click.pass_context
def cli(ctx: click.Context, version: bool) -> None:
    """🦉 Duo-CLI: Modern Duolingo Terminal Client & Automated Learning Engine."""
    if version:
        console.print("[bold bright_green]duo-cli[/] version [bold bright_yellow]1.0.0[/]")
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
    if not jwt:
        console.print(
            "\n[bold bright_yellow]ℹ How to get your JWT token in Chrome / Edge / Firefox:[/]\n"
            "  1. Open [underline cyan]https://www.duolingo.com[/] in your browser (logged in)\n"
            "  2. Press [bold]F12[/] -> [bold]Console[/]\n"
            "  3. Paste: [green]copy(document.cookie.split('; ').find(r => r.startsWith('jwt_token='))?.split('=')[1])[/]\n"
            "  4. Press [bold]Enter[/] (token is automatically copied to your clipboard)\n"
        )
        jwt = Prompt.ask("[bold bright_cyan]Paste JWT token (Ctrl+V)[/]").strip()

    if not username or not jwt:
        print_error("Both username and JWT token are required.")
        return

    try:
        set_credentials(username, jwt)
        client = DuoClient()
        user_info = client.verify_auth()
        print_success(f"Successfully logged in as [bold bright_white]@{user_info.get('username')}[/]! 🔥 Streak: {user_info.get('streak', 0)} Days.")
    except Exception as e:
        print_error(f"Authentication failed: {e}")


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
def status_cmd() -> None:
    """Show detailed streak, daily goals, and active language status."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
    try:
        client = DuoClient()
        user_data = client.verify_auth()
        streak_info = client.get_streak_info()
        render_status(streak_info, user_data)
    except Exception as e:
        print_error(f"Failed to load status: {e}")


@cli.command("courses")
def courses_cmd() -> None:
    """List all enrolled languages and courses."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
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
def calendar_cmd(days: int) -> None:
    """Show calendar activity and streak history."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
    try:
        client = DuoClient()
        cal = client.get_streak_calendar(days)
        render_calendar(cal)
    except Exception as e:
        print_error(f"Failed to load calendar: {e}")


@cli.command("quests")
def quests_cmd() -> None:
    """Display daily quests and achievement progress."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
    try:
        client = DuoClient()
        quests = client.get_quests()
        render_quests(quests)
    except Exception as e:
        print_error(f"Failed to load quests: {e}")


@cli.command("shop")
def shop_cmd() -> None:
    """Browse Duolingo shop items and gem pricing."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
    try:
        client = DuoClient()
        items = client.get_shop_items()
        info = client.get_streak_info()
        render_shop(items, info.get("gems", 0))
    except Exception as e:
        print_error(f"Failed to load shop: {e}")


@cli.command("freeze")
def freeze_cmd() -> None:
    """Purchase and equip Streak Freeze item."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
    try:
        client = DuoClient()
        client.buy_streak_freeze()
        print_success("Streak Freeze purchased and equipped! 🛡️")
    except Exception as e:
        print_error(f"Purchase failed: {e}")


@cli.command("vocab")
@click.option("--lang", "-l", help="Language code filter (e.g. es, de, fr)")
@click.option("--limit", "-n", default=30, help="Maximum number of words to show")
def vocab_cmd(lang: str, limit: int) -> None:
    """Browse learned vocabulary and strength."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
    try:
        client = DuoClient()
        vocab = client.get_vocabulary(lang)
        render_vocabulary_table(vocab, limit)
    except Exception as e:
        print_error(f"Failed to load vocabulary: {e}")


@cli.command("profile")
@click.argument("username", required=False)
def profile_cmd(username: Optional[str]) -> None:
    """View user profile stats and achievements."""
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
def friends_cmd() -> None:
    """View list of friends and followers."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
    try:
        client = DuoClient()
        friends = client.get_friends()
        render_friends_table(friends)
    except Exception as e:
        print_error(f"Failed to load friends: {e}")


@cli.command("practice")
@click.option("--lang", "-l", default=None, help="Target language (e.g. es, de, en)")
def practice_cmd(lang: Optional[str]) -> None:
    """Start an interactive practice session to earn XP and maintain streak."""
    client = DuoClient()
    if not client.is_authenticated():
        print_warning("Running in offline mode. Run 'duo login' to sync XP with Duolingo servers.")
    session = PracticeSession(client, lang)
    session.run()


@cli.command("auto")
@click.option("--sessions", "-s", default=1, type=int, help="Number of practice sessions to complete (default: 1)")
@click.option("--target-xp", "-x", default=None, type=int, help="Target XP to earn before stopping")
@click.option("--until-goal", "-g", is_flag=True, help="Run practice sessions until today's daily XP goal is reached")
@click.option("--loop", "-L", is_flag=True, help="Run practice sessions forever (until Ctrl+C)")
@click.option("--lang", "-l", default=None, help="Target language code (e.g. es, de, fr)")
@click.option("--delay-min", default=1.2, type=float, help="Minimum delay between questions in seconds (default: 1.2)")
@click.option("--delay-max", default=2.8, type=float, help="Maximum delay between questions in seconds (default: 2.8)")
@click.option("--fast", is_flag=True, help="Fast mode with reduced delays (~0.3s - 0.7s)")
@click.option("--max-sessions", "-m", default=None, type=int, help="Hard cap on number of sessions (recommended with -L to avoid bans)")
def auto_cmd(
    sessions: int,
    target_xp: Optional[int],
    until_goal: bool,
    loop: bool,
    lang: Optional[str],
    delay_min: float,
    delay_max: float,
    fast: bool,
    max_sessions: Optional[int],
) -> None:
    """Automate Duolingo practice sessions with natural delays to earn XP and keep streak."""
    if not is_authenticated():
        print_error("Not authenticated. Run 'duo login'.")
        return
    if loop:
        print_warning(
            "[bold yellow]⚠ Endless auto (-L) can look like botting to Duolingo and risks a ban. "
            "Use -m/--max-sessions to set a limit.[/]"
        )
    client = DuoClient()
    bot = AutoPractice(
        client=client,
        lang_code=lang,
        delay_min=delay_min,
        delay_max=delay_max,
        fast=fast,
        max_sessions=max_sessions,
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
    client = DuoClient()
    username = client.username or "guest"

    console.print()
    console.print("[bold bright_green]🦉 DUO INTERACTIVE SHELL[/]")
    console.print(f"[dim green]{DIVIDER_LINE}[/]")
    preset = get_preset_language() or "es"
    console.print(f"  Active User : [bold bright_white]@{username}[/]   Course: [bold bright_cyan]{preset.upper()}[/]")
    console.print("  Type 'help' for commands, 'exit' to quit.")
    console.print(f"[dim green]{DIVIDER_LINE}[/]\n")

    cmd_map = {
        "status": status_cmd,
        "courses": courses_cmd,
        "calendar": calendar_cmd,
        "quests": quests_cmd,
        "shop": shop_cmd,
        "freeze": freeze_cmd,
        "switch": switch_cmd,
        "vocab": vocab_cmd,
        "profile": profile_cmd,
        "friends": friends_cmd,
        "practice": practice_cmd,
        "auto": auto_cmd,
        "whoami": whoami_cmd,
        "help": help_cmd,
    }

    while True:
        try:
            prompt_str = f"[bold bright_green]🦉 duo:{username}/{get_preset_language() or 'es'}[/] > "
            raw = Prompt.ask(prompt_str).strip()
            if not raw:
                continue

            parts = raw.split()
            cmd_name = parts[0].lower()
            args = parts[1:]

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
                    if cmd_name == "practice" and args:
                        ctx.invoke(cmd_map[cmd_name], lang=args[0])
                    elif cmd_name == "profile" and args:
                        ctx.invoke(cmd_map[cmd_name], username=args[0])
                    elif cmd_name == "auto":
                        # Support parsing flags inside shell
                        fast = "--fast" in args
                        until_goal = "-g" in args or "--until-goal" in args
                        loop = "-L" in args or "--loop" in args
                        sessions = 1
                        target_xp = None
                        lang = None
                        max_sessions = None

                        for i, a in enumerate(args):
                            if a in ["-s", "--sessions"] and i + 1 < len(args) and args[i + 1].isdigit():
                                sessions = int(args[i + 1])
                            elif a in ["-x", "--target-xp"] and i + 1 < len(args) and args[i + 1].isdigit():
                                target_xp = int(args[i + 1])
                            elif a in ["-l", "--lang"] and i + 1 < len(args):
                                lang = args[i + 1]
                            elif a in ["-m", "--max-sessions"] and i + 1 < len(args) and args[i + 1].isdigit():
                                max_sessions = int(args[i + 1])

                        ctx.invoke(cmd_map[cmd_name], sessions=sessions, target_xp=target_xp, until_goal=until_goal, loop=loop, lang=lang, fast=fast, max_sessions=max_sessions)
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
    try:
        cli()
    except Exception as e:
        print_error(f"Fatal error: {e}")


if __name__ == "__main__":
    main()
