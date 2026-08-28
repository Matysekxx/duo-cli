"""
duo-cli: Duolingo Command Line Interface & TUI
"""

import sys

# Ensure UTF-8 output on Windows consoles — centralized (Dedup: cli.py/ui.py/main.py)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

__version__ = "1.2.0"
