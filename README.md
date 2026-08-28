<div align="center">

# 🦉 duo-cli

**A blazing-fast, secure, and beautiful Duolingo CLI — terminal client & automated learning engine.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![Code Style: Clean](https://img.shields.io/badge/code%20style-clean-brightgreen.svg)]()

*Keep your streak, hit daily goals, and practice languages — all from the terminal. Live-synced with official Duolingo servers.*

[Installation](#-installation) • [Authentication](#-authentication) • [Command Reference](#-command-reference) • [Learning](#-learning--practice) • [Configuration](#-configuration--security)

</div>

---

## 📑 Table of Contents

1. [What is duo-cli?](#-what-is-duo-cli)
2. [Installation](#-installation)
3. [Authentication](#-authentication)
4. [Command Reference](#-command-reference)
5. [Learning & Practice](#-learning--practice)
   - [`duo practice` — Interactive Lesson](#-duo-practice--interactive-lesson)
   - [`duo auto` — Automation Engine](#-duo-auto--automation-engine)
6. [Stats & Progress](#-stats--progress)
7. [Courses & Languages](#-courses--languages)
8. [Profile & Social](#-profile--social)
9. [Shop & Economy](#-shop--economy)
10. [Interactive Shell](#-interactive-shell-duo-shell)
11. [Configuration & Security](#-configuration--security)
12. [How Server Sync Works](#-how-server-sync-works)
13. [Troubleshooting](#-troubleshooting)
14. [Development](#-development)

---

## 🦉 What is duo-cli?

`duo-cli` is a lightweight terminal client for Duolingo built on direct REST calls. No browser, no bloat — just `requests`, `rich`, and `click`.

**Why use it?**

| Feature | Description |
|---|---|
| **⚡ Live Sync** | XP, streak, and hearts are read from and written back to Duolingo servers. No silent refills. |
| **🤖 Two Learning Modes** | `practice` for legit hands-on learning and `auto` for automatic daily-goal completion. |
| **🛡️ Ban-Safe** | Randomized human-like delays, "coffee breaks", and a hard cap `-m` so automation never looks like a bot. |
| **🌐 Persistent Language** | `duo switch de` remembers your course — `practice`/`auto` reuse it automatically next time. |
| **🎨 Clean TUI** | Minimal, fast terminal UI — clear typography, spacing, and color accents that work in any terminal (PowerShell, Windows Terminal, iTerm2, Alacritty). |
| **🔒 Secure Storage** | Token lives outside the repo in `~/.duo-cli/config.json`. Also supports `.env` and env vars. |

---

## 🚀 Installation

### Requirements
- Python **3.8+**
- `pip`

### Install from Git (recommended)

```bash
# 1. Clone the repository
git clone https://github.com/Matysekxx/duo-cli.git
cd duo-cli

# 2. Install package (registers the global `duo` command)
pip install -e .
```

After installation you have `duo` and `duo-cli` available globally:

```bash
duo --help        # help
duo --version     # version
duo               # dashboard (same as duo status)
```

> **Ways to run `duo`:**
> - `duo <command>` (when installed via pip in PATH)
> - `python -m duo <command>` (universal module execution)
> - `.\duo.bat` or `.\duo.ps1` (Windows command wrapper)
> - `python main.py <command>` (direct script execution)

---

## 🔑 Authentication

### `duo login` — connect your Duolingo account

```bash
duo login
# or with flags:
duo login -u your-name -j your-jwt
```

You will be prompted for:
1. **Duolingo Username** — your login name
2. **JWT Token** — session token from browser cookies

<details>
<summary><b>🔍 How to get your JWT token (Chrome / Edge / Firefox)</b></summary>

1. Open [duolingo.com](https://www.duolingo.com) and log in.
2. Press `F12` → **Console** tab.
3. Paste this snippet and press `Enter`:
   ```javascript
   copy(document.cookie.split('; ').find(r => r.startsWith('jwt_token='))?.split('=')[1])
   ```
4. The token is copied to your clipboard — paste it into `duo login` (`Ctrl+V`).

> Token format is `eyJ...` (3 dot-separated parts). `duo-cli` automatically strips the `jwt_token=` prefix if you copy it with it.

</details>

### `duo logout` / `duo whoami`

```bash
duo whoami    # verifies session and prints @username + ID
duo logout    # deletes ~/.duo-cli/config.json
```

---

## 📖 Command Reference

All commands also work inside the interactive shell (`duo shell`).

| Command | Purpose | Key Options |
|---|---|---|
| **`duo`** / **`duo status`** | Dashboard — streak, XP, course, gems | — |
| **`duo practice`** | Interactive terminal lesson | `-l, --lang <code>` |
| **`duo auto`** | Auto-solve lessons (1-2s / question, 20-50s between) | `-s, -g, -x, -L, -m, -l` |
| **`duo calendar`** | 14-day activity heatmap + XP history | `-d, --days <N>` |
| **`duo courses`** | List all enrolled courses | — |
| **`duo switch <lang>`** | Switch active course & save as preset | `es`, `de`, `fr`, `ja`... |
| **`duo shop`** | Store prices + equipped items | — |
| **`duo freeze`** | Buy Streak Freeze for 200 gems | — |
| **`duo profile [user]`** | Profile & stats (own or other user) | optional `username` |
| **`duo friends`** | Following leaderboard | — |
| **`duo shell`** | Interactive REPL loop | — |
| **`duo login/logout/whoami`** | Auth management | `-u, -j` for login |
| **`duo help`** | Full categorized help | — |

> Run `duo <command> --help` for detailed help on any command.

---

## 🎮 Learning & Practice

### `duo practice` — Interactive Lesson

Starts a **live lesson fetched from Duolingo servers** (`GLOBAL_PRACTICE`). When you finish, XP is submitted back to the server and your streak is extended.

```bash
duo practice              # uses preset language (from `duo switch`) or active server course
duo practice -l es        # Spanish
duo practice -l de        # German
duo practice -l ja        # Japanese
```

**What you see in a lesson:**

```
🦉 DUOLINGO PRACTICE SESSION
────────────────────────────────────────────────────────
  Language  : ES | Questions: 12 | Hearts: 5/5
  User      : @your-name

  How to play:
    • Multiple choice → type the number of your answer
    • Translate → type the translation
    • Build sentence → type word numbers in order (e.g. 3 1 4 2) or the sentence
    • exit to quit the session
────────────────────────────────────────────────────────
```

**Challenge types supported in the terminal:**

| Type | How to Answer | Example |
|---|---|---|
| **Multiple Choice** (`select`, `assist`, `radioSelect`, `judge`...) | Type number `1`–`4` or answer text | `Your answer (1-3): 2` |
| **Translate** (`translate`) | Type the translation as free text | `Translate: "Hello" → Hola` |
| **Gap Fill** (`gapFill`, `tapCloze`, `typeCloze`) | Pick from options or type the missing word | `Fill in the blank: "Yo ____ español"` |
| **Type Complete** (`typeComplete`) | Type the missing letters | `🔤 Type the missing letters: "hel__"` |
| **Build Sentence** (`tapComplete`, `orderTapComplete`...) | Type word numbers in order or the full sentence | `Your sentence: 3 1 4 2` or `Yo soy estudiante` |
| **Match Pairs** (`match`) | Pick translations step-by-step — elimination mini-game | `Choice (1-4): 1` |
| **Visual** (`characterTrace`, `svgPuzzle`...) | Can't be rendered in terminal → **auto-completed as correct** | `🖼️ Auto-completed! ✔` |

**Controls during a lesson:**
- `exit` / `q` / `quit` — end the lesson early (current score is submitted)
- Hearts `♥ ♥ ♥ ♥ ♥` + combo `🔥 COMBO x3` shown on every question
- At `0 ♥` the lesson ends and is submitted as `failed` (server deducts hearts correctly)

---

### 🤖 `duo auto` — Automation Engine

Creates **real lessons on the server** and solves them with randomized human-like delays. Perfect for keeping your streak when you don't have time.

```bash
# Basic — 1 session (1-2s per question, 20-50s between lessons)
duo auto

# 3 sessions
duo auto -s 3

# Run until today's daily goal is met (e.g. 20 XP)
duo auto --until-goal
duo auto -g

# Earn at least 50 XP then stop
duo auto --target-xp 50
duo auto -x 50

# Specific language
duo auto -l de -s 2
duo auto -l fr --until-goal

# Infinite loop (until Ctrl+C) — no cap, just a warning
duo auto -L

# Loop with a safe cap (recommended!)
duo auto -L -m 20          # max 20 sessions
```

#### All `duo auto` Options

| Option | Short | Default | Description |
|---|---|---|---|
| `--sessions` | `-s` | `1` | Number of sessions to complete |
| `--target-xp` | `-x` | — | Stop after earning at least N XP |
| `--until-goal` | `-g` | — | Run until daily XP goal is reached |
| `--loop` | `-L` | — | Infinite loop until `Ctrl+C` |
| `--max-sessions` | `-m` | — | Hard cap on sessions (works with `-L`) |
| `--lang` | `-l` | preset/server | Language code (`es`, `de`, `fr`...) |

#### How It Works

- **Per question:** fixed `1.0–2.0s` random delay — no fast mode, no extra thinking pauses
- **Between lessons:** fixed `20–50s` random pause
- **No retries:** on server error it stops cleanly with an error message instead of retrying
- **`maxInLessonStreak` capped at 9** so it never looks like a bot

> [!WARNING]
> **Ban safety:** Endless `-L` without `-m` can look like botting to Duolingo. Always prefer `duo auto -L -m 20` or similar. The engine already randomizes pacing, but human supervision is safest.

**Example output:**

```
⚡ DUOLINGO AUTO PRACTICE BOT
────────────────────────────────────────────────────────
  Language : ES | Mode: 3 Sessions
  Solving lessons automatically with natural randomized pauses...
────────────────────────────────────────────────────────

▶ Starting Session 1...
  • [Session 1 | Q 01/12] Fill in the blank: "Yo ____" → soy (1.8s)
  • [Session 1 | Q 02/12] Translate: "Good morning" → Buenos días (2.1s)
  ...
  Submitting session 1 to Duolingo servers...
  ✔ Session 1 Complete! +15 XP 🔥 Streak Maintained! (Total earned this run: +15 XP)

⏳ Resting for 18s before next session...
```

---

## 📊 Stats & Progress

### `duo` / `duo status` — Dashboard

Default command with no arguments. Shows an overview:

```bash
duo
duo status
```

```
🦉 DUOLINGO DASHBOARD
────────────────────────────────────────────────────────
  Course        : Spanish [ES]
  Daily Streak  : 127 Days    ✓ COMPLETED TODAY
  Total XP      : 42,350 XP
  Gems Balance  : 1,240 Gems
────────────────────────────────────────────────────────
  🔥 Streak Active & Secured Today! Great job, @your-name!
```

- `✓ COMPLETED TODAY` vs `⌛ INCOMPLETE` based on `xp_today` and `streakData`
- Divider color green/red reflects streak state

### `duo calendar` — Activity Calendar

```bash
duo calendar              # last 14 days
duo calendar -d 30        # last 30 days
duo calendar --days 7     # last 7 days
```

Table `Date | Day | Status (ACTIVE/INACTIVE) | XP Gained`. Today is marked `👉 TODAY`.

---

## 🌐 Courses & Languages

### `duo courses` — List Courses

```bash
duo courses
```

```
ENROLLED COURSES
────────────────────────────────────────────────────────
  Status   Course              Code    Total XP
  ACTIVE   Spanish             [ES]    12,400 XP
  Enrolled German              [DE]     3,200 XP
  Enrolled Japanese            [JA]       800 XP
```

- Sorted: active course first, then by XP descending
- Duplicates filtered

### `duo switch <lang>` — Switch Course

```bash
duo switch es        # Spanish
duo switch de        # German
duo switch fr        # French
duo switch ja        # Japanese
duo switch pt        # Portuguese
```

- Saves `preset_language` to `~/.duo-cli/config.json` — `practice`/`auto` remember it even if the server doesn't confirm the switch
- Tries `POST /switch_language` + fallback `PATCH /users/{id}`
- Prints `Switched active course to: ES (was DE) — saved as local preset`

**Language resolution for `practice`/`auto`:**
```
1. explicit -l flag  →  2. preset from `duo switch`  →  3. server learningLanguage  →  4. "es"
```

Supported codes: `en`, `es`, `fr`, `de`, `it`, `ja`, `zh`, `ru`, `pt`, `cs`, `pl`, `ko`, `nl`, `sv`, `el`, `tr`, `uk`, `vi`, `ar`, `hi` and any other code Duolingo recognizes.

---

## 👤 Profile & Social

### `duo profile [username]` — Profile Card

```bash
duo profile              # your own profile
duo profile your-name      # public profile of another user (no login required)
```

```
👤 PROFILE: @your-name
────────────────────────────────────────────────────────
  Full Name     : Your Name
  Username      : @your-name
  Daily Streak  : 127 Days
  Total XP      : 42,350 XP
  Learning      : ES (from EN)
  Member Since  : 2023-04-12
  Bio           : No bio set
────────────────────────────────────────────────────────
```

### `duo friends` — Friends Leaderboard

```bash
duo friends
```

Table `User | Total XP | Streak` sorted by XP descending. Fetches `GET /friends/users/{id}/following`.

### `duo whoami` — Who Am I?

```bash
duo whoami
# → Logged in as: @your-name (ID: 123456789)
```

Verifies JWT via `GET /users?username=...` and prints the ID.

---

## 🛒 Shop & Economy

### `duo shop` — Store Overview

```bash
duo shop
```

```
DUOLINGO SHOP (Balance: 1,240 Gems)
────────────────────────────────────────────────────────
  Item              Price       Description
  Streak Freeze     200 Gems    Protects your streak for 1 day (Max 2 equipped).
  Refill Hearts     350 Gems    Instantly refills all 5 hearts.
```

- Prices and descriptions match the current Duolingo store
- `Streak Freeze` shows `Equipped: 1/2` if you already own one (from `shopItems`)

### `duo freeze` — Buy Streak Freeze

```bash
duo freeze
# → Streak Freeze purchased and equipped! 🛡️
```

Calls `POST /users/{id}/shop-items` with `streak_freeze`. Requires 200 gems. Automatically invalidates cache.

---

## 💬 Interactive Shell (`duo shell`)

A REPL loop so you can work without leaving the terminal. All commands are available as built-ins.

```bash
duo shell
```

```
🦉 DUO INTERACTIVE SHELL
────────────────────────────────────────────────────────
  Active User : @your-name   Course: ES
  Type 'help' for commands, 'exit' to quit.
────────────────────────────────────────────────────────

🦉 duo:your-name/es > status
🦉 duo:your-name/es > practice es
🦉 duo:your-name/es > auto -s 2
🦉 duo:your-name/es > switch de
🦉 duo:your-name/es > calendar
🦉 duo:your-name/es > help
🦉 duo:your-name/es > exit
Goodbye! Happy learning! 🦉
```

**Supported commands inside the shell:**
`status`, `courses`, `calendar`, `shop`, `freeze`, `switch`, `profile`, `friends`, `practice`, `auto`, `whoami`, `help`, `clear`, `exit`/`quit`/`q`

**Notes:**
- `practice <lang>` — language as positional arg (`practice de`)
- `auto` — parses `-s`, `-x`, `-g`, `-L`, `-l`, `-m` directly in the shell
- `Ctrl+C` / `Ctrl+D` safely exits the shell

---

## 🔒 Configuration & Security

### Where Are Credentials Looked Up?

`duo-cli` searches in this order (first hit wins):

| Priority | Source | Example |
|---|---|---|
| **1.** | OS env vars | `DUOLINGO_USERNAME`, `DUOLINGO_JWT` (or `DUOLINGO_JWT_TOKEN` / `DUOLINGO_USER`) |
| **2.** | Local `.env` file | `.env` in current directory (`KEY=VALUE`) |
| **3.** | Global config | `~/.duo-cli/config.json` (created by `duo login`) |

**Format of `~/.duo-cli/config.json`:**
```json
{
  "username": "your-name",
  "jwt_token": "your-jwt",
  "preset_language": "es"
}
```

**Format of `.env`:**
```ini
DUOLINGO_USERNAME=your-name
DUOLINGO_JWT=your-jwt
```

> [!TIP]
> `.env` is great for CI/Docker. For local use just run `duo login` once — the token stays in `~/.duo-cli/` outside the repo and will never be committed.

### Security Principles

- **Zero-Leak:** Token is never in the repo, only in `~/.duo-cli/` (outside the project)
- **Token sanitization:** `sanitize_token()` automatically strips the `jwt_token=` prefix and keeps only the first 3 JWT parts
- **UTF-8 on Windows:** `sys.stdout.reconfigure(encoding="utf-8")` so emoji and flags work in PowerShell
- **No silent heart refills:** `practice`/`auto` read the real heart count from the API and send it back — the server deducts hearts itself

---

## 🔄 How Server Sync Works

```
┌─────────────┐      POST /sessions       ┌──────────────┐
│  duo-cli    │ ────────────────────────→ │  Duolingo    │
│  (terminal) │  challengeTypes: [...]    │  API         │
│             │  learningLanguage: es     │              │
│             │ ←──────────────────────── │              │
│             │  { id, challenges: [...] }│              │
│             │                           │              │
│  solves     │   PUT /sessions/{id}      │  evaluates   │
│  + delays   │ ────────────────────────→ │  +15 XP      │
│             │  heartsLeft, mistakes,    │  streak 🔥   │
│             │  startTime, endTime       │              │
└─────────────┘                           └──────────────┘
```

1. **Create lesson:** `POST https://www.duolingo.com/2017-06-30/sessions` with `type: GLOBAL_PRACTICE` and filtered `challengeTypes` (audio types like `listen`, `speak` excluded)
2. **Parse challenges:** `extract_challenge_solution()` extracts `prompt`, `choices`, `word_bank`, `pairs`, `solutions`, and `correctIndex` for each type
3. **Submit result:** `PUT /sessions/{id}` with `heartsLeft`, `mistakes`, `failed`, `maxInLessonStreak` (max 9) and timestamps (min. 15s lesson length for anti-cheat)

---

## 🛠 Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `Invalid or expired JWT` | Token expired (Duolingo rotates it) | `duo logout` → `duo login` with a fresh token from cookies |
| `No practice questions available` | Invalid course or API returned no `challenges` | `duo switch es` or try `duo practice -l en` with another language |
| `0 ♥ You ran out of hearts` | Hearts depleted on server | Wait for refill or buy `Refill Hearts` (350 gems, currently web-only) |
| `Shop error` on `duo freeze` | Not enough gems or already 2 freezes | Check balance with `duo shop` |
| `Network error` | Duolingo API outage | Retry shortly, verify `https://www.duolingo.com` in browser |
| Emoji shows as `???` | Wrong terminal encoding | Use Windows Terminal / VS Code terminal instead of legacy `cmd.exe` |

**Debug tips:**
```bash
# Verify token works
duo whoami

# Force cache refresh
# (internally calls verify_auth with force_refresh=True — just run duo status again)

# Check config
cat ~/.duo-cli/config.json        # Linux/macOS
type $HOME\.duo-cli\config.json   # PowerShell
```

---

## 🧩 Development

```bash
# Clone + install
git clone https://github.com/Matysekxx/duo-cli.git
cd duo-cli
pip install -e .

# Run without install
python main.py status
python main.py practice -l es
python main.py auto --help

# Tests (if present)
pytest tests/ -v

# Project structure
duo/
  cli.py        # Click commands + shell loop
  api.py        # DuoClient — REST wrapper + challenge parsing
  practice.py   # PracticeSession (interactive) + AutoPractice (bot)
  config.py     # reads/writes ~/.duo-cli/config.json + .env
  ui.py         # Rich TUI — tables, cards, banners
```

**Dependencies:** `requests>=2.31.0`, `rich>=13.0.0`, `click>=8.0.0` — nothing else.

---

## 📜 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE).

---

<div align="center">

**Built with 🦉 for language lovers who live in the terminal.**

`duo auto -g` and never lose your streak again! 🔥

</div>
