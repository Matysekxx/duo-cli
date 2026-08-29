"""
Common styling, terminal console instance, and message printers for duo-cli TUI.
"""

import sys
from rich.console import Console
from rich.table import Table

DIVIDER_LINE = "─" * 56
SECTION_SEP = "─" * 56


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


def print_success(message: str) -> None:
    console.print(f"[bold bright_green]✔ {message}[/]")


def print_error(message: str) -> None:
    console.print(f"[bold bright_red]✘ {message}[/]")


def print_warning(message: str) -> None:
    console.print(f"[bold bright_yellow]⚠ {message}[/]")


def print_info(message: str) -> None:
    console.print(f"[bold cyan]ℹ {message}[/]")


def _make_table(title: str) -> Table:
    """Create a borderless table — no box, just clean columns and padding."""
    return Table(
        title=f"[bold bright_cyan]{title}[/]" if title else None,
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


def _print_section_title(title: str, subtitle: str = "") -> None:
    console.print()
    console.print(f"[bold bright_cyan]{title}[/]" + (f"  [dim]{subtitle}[/dim]" if subtitle else ""))
    console.print(f"[dim]{SECTION_SEP}[/dim]")


def _hearts_bar(hearts: int) -> str:
    max_hearts = 5
    return " ".join(
        "[bold bright_red]♥[/]" if i < hearts else "[dim]♡[/]" for i in range(max_hearts)
    )


def _combo_badge(combo: int) -> str:
    return f"  [bold bright_yellow]🔥 ×{combo}[/]" if combo >= 2 else ""
