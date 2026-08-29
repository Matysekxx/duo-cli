"""
Clean, minimal TUI for duo-cli — borderless tables and lightweight card components.
"""

from .common import (
    DIVIDER_LINE,
    SECTION_SEP,
    _DynamicStdout,
    _combo_badge,
    _hearts_bar,
    _make_table,
    _print_section_title,
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from .banner import DUO_BANNER, UI_VERSION, _build_banner, _get_version, print_banner, render_help

__version__ = UI_VERSION
from .dashboard import render_calendar, render_config, render_hearts, render_status
from .cards import (
    render_answer_result,
    render_build_card,
    render_freeform_card,
    render_match_panel,
    render_question_card,
)
from .tables import (
    render_courses_table,
    render_friends_table,
    render_leaderboard,
    render_profile,
    render_shop,
)
from .auto_display import (
    render_auto_challenge,
    render_auto_header,
    render_auto_session_result,
    render_auto_summary,
)

__all__ = [
    "DIVIDER_LINE",
    "SECTION_SEP",
    "_DynamicStdout",
    "_combo_badge",
    "_hearts_bar",
    "_make_table",
    "_print_section_title",
    "console",
    "print_error",
    "print_info",
    "print_success",
    "print_warning",
    "DUO_BANNER",
    "UI_VERSION",
    "_build_banner",
    "_get_version",
    "print_banner",
    "render_help",
    "render_calendar",
    "render_config",
    "render_hearts",
    "render_status",
    "render_answer_result",
    "render_build_card",
    "render_freeform_card",
    "render_match_panel",
    "render_question_card",
    "render_courses_table",
    "render_friends_table",
    "render_leaderboard",
    "render_profile",
    "render_shop",
    "render_auto_challenge",
    "render_auto_header",
    "render_auto_session_result",
    "render_auto_summary",
]
