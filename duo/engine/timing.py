"""
Timing calculations and humanized delays for practice sessions.
"""

import random
import time
from typing import Dict
from rich.progress import BarColumn, Progress, TextColumn
from ..models import TimingConfig
from ..ui.common import console

# Per-type multipliers: tasks requiring reading/writing take longer,
# single-choice tasks are faster.
_TYPE_DELAY_MULTIPLIER: Dict[str, float] = {
    "translate": 1.7,
    "completeReverseTranslation": 1.6,
    "typeCloze": 1.5,
    "typeClozeTable": 1.5,
    "typeComplete": 1.4,
    "typeCompleteTable": 1.4,
    "tapComplete": 1.3,
    "tapCompleteTable": 1.3,
    "patternTapComplete": 1.3,
    "tapCloze": 1.2,
    "tapClozeTable": 1.2,
    "gapFill": 1.2,
    "orderTapComplete": 1.3,
    "syllableTap": 1.1,
    "match": 1.4,
    "assist": 0.9,
    "select": 0.9,
    "characterSelect": 0.9,
    "radioSelect": 0.9,
    "judge": 0.9,
}


class HumanDelayCalculator:
    """Calculates realistic, human-like pauses and manages countdown timers."""

    def __init__(self, config: TimingConfig | None = None):
        self.config = config or TimingConfig()

    def question_delay(self, prompt: str = "", ctype: str = "") -> float:
        """Calculate human-like per-question pause.

        - Starts from uniform(question_delay_min, question_delay_max).
        - Applies per-type multiplier (harder types = longer).
        - Adds prompt-length bonus (~0.012s per char, capped at 1.8s) to simulate reading time.
        - Adds small Gaussian jitter for natural variance.
        """
        base = random.uniform(self.config.question_delay_min, self.config.question_delay_max)
        mult = _TYPE_DELAY_MULTIPLIER.get(ctype, 1.0)
        pause = base * mult
        if prompt:
            pause += min(len(prompt) * 0.012, 1.8)
        pause += random.gauss(0, 0.12)
        return max(0.6, min(pause, 6.0))

    def rest_delay(self) -> float:
        """Calculate base rest pause between lessons."""
        base_rest = random.uniform(self.config.rest_min, self.config.rest_max)
        base_rest += random.gauss(0, 1.0)
        return max(15.0, base_rest)

    def sleep_with_progress(self, seconds: float, description: str = "Resting...") -> None:
        """Perform a rest pause with a sleek, non-intrusive rich.progress countdown bar."""
        if seconds <= 0:
            return
        step = 0.25
        with Progress(
            TextColumn("[dim]⏳ {task.description}"),
            BarColumn(bar_width=24, style="dim white", complete_style="bold bright_cyan"),
            TextColumn("[dim]{task.completed:.0f}s / {task.total:.0f}s[/dim]"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(description, total=seconds)
            elapsed = 0.0
            while elapsed < seconds:
                sleep_dur = min(step, seconds - elapsed)
                time.sleep(sleep_dur)
                elapsed += sleep_dur
                progress.advance(task, sleep_dur)


AUTO_QUESTION_DELAY_MIN = 0.8
AUTO_QUESTION_DELAY_MAX = 1.6
AUTO_REST_MIN = 25.0
AUTO_REST_MAX = 35.0


def _human_delay(base_min: float = 0.8, base_max: float = 1.6, prompt: str = "", ctype: str = "") -> float:
    """Standalone helper function for calculating delay."""
    cfg = TimingConfig(question_delay_min=base_min, question_delay_max=base_max)
    calc = HumanDelayCalculator(cfg)
    return calc.question_delay(prompt, ctype)

