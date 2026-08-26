<div align="center">

# 🦉 duo-cli

**A blazing-fast, secure, and beautiful Duolingo command-line interface & automated learning engine.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Clean](https://img.shields.io/badge/code%20style-clean-brightgreen.svg)]()
[![Platform: Cross-Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Command Reference](#-command-reference) • [Automation](#-automated-practice-duo-auto) • [Interactive Quiz](#-interactive-practice-duo-practice) • [Security](#-configuration--security)

</div>

---

## ✨ Features

- ⚡ **Live Server Synchronization**: Syncs completed lessons and XP directly to official Duolingo servers in real-time, preserving your daily streak.
- 🤖 **Automated Practice Engine (`auto`)**: Autonomous challenge solver using natural human-paced delays, target XP goals, and streak protection.
- 🎮 **Gamified Terminal Quiz (`practice`)**: Legitimate interactive learning with smart sentence reconstruction (`____`), option shuffling, combo streaks, and a word-matching minigame.
- 🔇 **15-Min Audio Snooze (`mute`)**: Replicates the mobile app's *"Can't listen/speak right now"* feature, disabling audio tasks for 15 minutes without penalty.
- 🎨 **Modern Borderless TUI**: Custom horizontal divider system (`box.HORIZONTALS`) that never breaks on any font, encoding, or terminal emulator (PowerShell, Windows Terminal, iTerm2, Alacritty).
- 📅 **14-Day Streak Visualizer**: Activity heatmap and daily XP progress breakdown.
- 📚 **Course & Vocab Inspection**: View all enrolled language courses and inspect learned vocabulary with word strength ratings.
- 🛒 **Duolingo Shop**: Check real store pricing (Streak Freeze, Heart Refill) and inspect your live equipped inventory.
- 🔒 **Zero-Leak Security**: Credentials stored exclusively in `~/.duo-cli/config.json` outside the project repository.
- 🚀 **Zero Dependency Bloat**: Ultra-lightweight native REST client built solely on `requests`, `rich`, and `click`.

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or newer
- `pip` package manager

### Install via Git

```bash
# 1. Clone the repository
git clone https://github.com/Matysekxx/duo-cli.git
cd duo-cli

# 2. Install in editable mode (registers global 'duo' command)
pip install -e .
```

---

## 🔑 Authentication

Connect your Duolingo account with a single command:

```bash
duo login
```

You will be prompted for:
1. **Duolingo Username**
2. **JWT Token** (session token from your browser cookies)

<details>
<summary><b>🔍 How to find your Duolingo JWT Token</b></summary>

1. Open [duolingo.com](https://www.duolingo.com) in Chrome, Firefox, or Edge (make sure you are logged in).
2. Press `F12` to open **Developer Tools** and switch to the **Console** tab.
3. Paste the following snippet and press `Enter`:
   ```javascript
   copy(document.cookie.split('; ').find(r => r.startsWith('jwt_token='))?.split('=')[1])
   ```
4. The token is now copied to your clipboard. Paste it into the `duo login` prompt!
</details>

---

## 📖 Command Reference

| Command | Description | Flags & Options |
|---|---|---|
| `duo` / `duo status` | Display overview dashboard (streak, language, XP, gems) | |
| `duo auto` | Solve practice lessons autonomously with human pauses | `-s, --sessions <N>`<br>`-g, --until-goal`<br>`-x, --target-xp <N>`<br>`--fast`<br>`-l, --lang <CODE>` |
| `duo practice` | Start an interactive full lesson terminal session | `-l, --lang <CODE>` |
| `duo mute` | Temporarily snooze listening & speaking exercises | `-m, --minutes <N>` *(default: 15)* |
| `duo calendar` | View 14-day streak visualizer & XP history | `-d, --days <N>` |
| `duo courses` | List all enrolled languages and total XP | |
| `duo switch <lang>` | Switch your active learning language *(e.g. `duo switch es`)* | |
| `duo quests` | Inspect daily quests, goals, and milestones | |
| `duo shop` | Browse items, prices, and equipped streak freezes | |
| `duo freeze` | Purchase and equip a Streak Freeze (200 gems) | |
| `duo vocab` | Browse learned vocabulary and word strength | `-l, --lang <CODE>`<br>`-n, --limit <N>` |
| `duo profile [user]` | Display user profile card and statistics | |
| `duo friends` | View friends, followers, and rankings | |
| `duo shell` | Launch interactive Duo REPL shell | |
| `duo whoami` | Show current authenticated user | |
| `duo logout` | Wipe stored local credentials | |

---

## ⚡ Automated Practice (`duo auto`)

The `auto` engine creates real practice sessions on Duolingo servers and solves them with randomized human-like delays, safely securing your streak:

```bash
# Complete 1 session with natural delays (~1.2s - 2.8s per challenge)
duo auto

# Automatically practice until today's XP goal is achieved:
duo auto --until-goal

# Earn at least 50 XP:
duo auto --target-xp 50

# Speedrun mode (faster pauses, ~0.5s):
duo auto -s 3 --fast

# Practice a specific language:
duo auto -l de -s 2
```

---

## 🎮 Interactive Practice (`duo practice`)

Experience full Duolingo lessons inside your terminal (all questions returned by the server are completed):

```bash
# Start full practice lesson
duo practice

# Practice Spanish course
duo practice -l es
```

### In-Quiz Controls:
- **Multiple Choice**: Type option number (`1`, `2`, `3`) or answer text.
- **Word Matching**: Interactive step-by-step translation connector with option elimination.
- **Skip Question**: Type `skip` or `s` to bypass a challenge.
- **Mute Audio Exercises**: Type `cant-listen`, `cant-speak`, or `mute` to enable 15-minute audio snooze without losing hearts.
- **Quit**: Type `exit` or `q` anytime to return to terminal.

---

## 🦉 Interactive Shell (`duo shell`)

For an all-in-one terminal session, launch the REPL environment:

```bash
duo shell
```

---

## 🔒 Configuration & Security

`duo-cli` looks for credentials in the following order:

1. **OS Environment Variables**: `DUOLINGO_USERNAME`, `DUOLINGO_JWT`
2. **Local `.env` file**: `.env` in the current working directory *(optional)*
3. **Global Config Store**: `~/.duo-cli/config.json` *(created by `duo login`)*

```json
{
  "username": "your_username",
  "jwt_token": "your_jwt_token",
  "audio_snooze_until": 0
}
```

---

## 📜 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.
