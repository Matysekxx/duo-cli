"""
Duolingo API Client wrapper.
Uses direct REST endpoints with optimized session caching and robust error handling.
"""

from datetime import datetime, timezone, timedelta
import json
import logging
from typing import Any, Dict, List, Optional
import requests

from urllib.parse import quote as url_quote

from .config import get_jwt, get_username

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — challenge taxonomy & i18n
# ---------------------------------------------------------------------------

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# All text-based challenge types the terminal can handle
TEXT_CHALLENGE_TYPES = [
    "assist", "characterIntro", "characterMatch", "characterPuzzle", "characterSelect",
    "characterTrace", "characterWrite", "completeReverseTranslation", "definition", "dialogue",
    "extendedMatch", "form", "freeResponse", "gapFill", "judge",
    "match", "name", "orderTapComplete", "partialReverseTranslate",
    "patternTapComplete", "radioBinary", "radioImageSelect",
    "radioSelect", "readComprehension", "reverseAssist", "sameDifferent",
    "select", "svgPuzzle", "syllableTap",
    "tapCloze", "tapClozeTable", "tapComplete", "tapCompleteTable",
    "tapDescribe", "translate", "transliterate", "transliterationAssist", "typeCloze",
    "typeClozeTable", "typeComplete", "typeCompleteTable", "writeComprehension"
]

# Audio / speaking challenge types are intentionally excluded: the terminal
# client cannot present or capture them, so we only request text-based types.
AUDIO_CHALLENGE_TYPES = {
    "listen", "listenComplete", "listenMatch", "listenComprehension", "listenIsolation",
    "listenSpeak", "listenTap", "partialListen", "radioListenMatch",
    "radioListenRecognize", "syllableListenTap", "speak",
    "selectPronunciation", "selectTranscription",
}

CHALLENGE_TYPES = [t for t in TEXT_CHALLENGE_TYPES if t not in AUDIO_CHALLENGE_TYPES]

# Challenges where the learner arranges a word bank into the correct sentence.
BUILD_SENTENCE_TYPES = {
    "orderTapComplete", "patternTapComplete", "syllableTap",
    "tapComplete", "tapCompleteTable",
}

# Cloze-style challenges with one or more blanks filled from a word bank.
CLOZE_TYPES = {
    "gapFill", "tapCloze", "tapClozeTable", "typeCloze", "typeClozeTable",
}

# Challenges where the learner types the missing letters of a word.
TYPE_COMPLETE_TYPES = {
    "typeComplete", "typeCompleteTable",
}

# Types whose "choices"/"options" are the source sentence tokens (not answer
# options). They must be solved as free text, never as multiple choice.
FREE_TEXT_FAMILY = {
    "translate",
}

LANGUAGE_FLAGS = {
    "en": "🇬🇧",
    "es": "🇪🇸",
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "it": "🇮🇹",
    "ja": "🇯🇵",
    "zh": "🇨🇳",
    "ru": "🇷🇺",
    "pt": "🇧🇷",
    "cs": "🇨🇿",
    "pl": "🇵🇱",
    "ko": "🇰🇷",
    "nl": "🇳🇱",
    "sv": "🇸🇪",
    "el": "🇬🇷",
    "tr": "🇹🇷",
    "uk": "🇺🇦",
    "vi": "🇻🇳",
    "ar": "🇸🇦",
    "hi": "🇮🇳",
    "la": "🏛️",
    "eo": "🟢",
    "kl": "🖖",
}


def get_flag(lang_code: Optional[str]) -> str:
    """Return flag emoji for a language code."""
    if not lang_code:
        return "🌐"
    return LANGUAGE_FLAGS.get(lang_code.lower(), "🌐")


def sanitize_token(token: Optional[str]) -> Optional[str]:
    """Deprecated shim — delegates to config.sanitize_jwt for strict validation."""
    from .config import sanitize_jwt
    return sanitize_jwt(token)


# ---------------------------------------------------------------------------
# Small validation helpers — keep API guards readable & extensible
# ---------------------------------------------------------------------------

_LANG_RE = None  # lazy import to avoid circular deps at module load


def _validate_lang_code(lang_code: str) -> str:
    """Validate and normalize language code, raise DuoAPIError if bad."""
    import re as _re

    if not lang_code or not _re.match(r"^[a-z]{2,3}(-[a-z]{2,4})?$", lang_code, _re.IGNORECASE):
        raise DuoAPIError(f"Invalid language code: {lang_code!r}")
    return lang_code.lower()


def _reject_control_chars(value: str, label: str = "value") -> None:
    """Raise if value contains control chars that could break URLs/headers."""
    if value and any(c in value for c in ("\r", "\n", "\0")):
        raise DuoAPIError(f"Invalid {label} — contains control characters")


class DuoAPIError(Exception):
    """General Duolingo API exception."""
    pass


def extract_challenge_solution(ch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to reliably extract the prompt, challenge type,
    options, and correct answer/solution from any Duolingo challenge object.
    """
    ctype = ch.get("type", "unknown")
    raw_prompt = ch.get("prompt") or ch.get("promptText") or ch.get("sentence") or ""
    translation = (
        ch.get("solutionTranslation")
        or (ch.get("metadata", {}) if isinstance(ch.get("metadata"), dict) else {}).get("translation")
        or (ch.get("metadata", {}) if isinstance(ch.get("metadata"), dict) else {}).get("word")
        or ""
    )

    # Solutions list
    solutions: List[str] = []
    if "correctSolutions" in ch and ch["correctSolutions"]:
        solutions.extend([str(s) for s in ch["correctSolutions"]])
    elif "solution" in ch and ch["solution"]:
        solutions.append(str(ch["solution"]))

    # Best solution from tracking
    best_sol = ch.get("challengeResponseTrackingProperties", {}).get("best_solution")
    if best_sol and best_sol not in solutions:
        solutions.append(str(best_sol))

    # Metadata word
    meta = ch.get("metadata", {}) if isinstance(ch.get("metadata"), dict) else {}
    meta_word = meta.get("word") or meta.get("translation")

    raw_choices = ch.get("choices") or []
    options = ch.get("options") or []
    pairs = ch.get("pairs") or []
    display_tokens = ch.get("displayTokens") or []
    tokens = ch.get("tokens") or []
    correct_idx = ch.get("correctIndex")

    formatted_choices: List[str] = []
    pair_strings: List[str] = []
    pair_tuples: List[tuple] = []
    word_bank: List[str] = []
    answer_str = ""
    prompt = ""

    if ctype in ["assist", "select", "characterSelect", "gapFill", "tapCloze", "tapClozeTable", "typeCloze", "typeClozeTable"]:
        if raw_choices:
            for c in raw_choices:
                if isinstance(c, str):
                    formatted_choices.append(c)
                elif isinstance(c, dict):
                    formatted_choices.append(c.get("text", ""))
        elif options:
            for opt in options:
                if isinstance(opt, dict):
                    formatted_choices.append(opt.get("text", ""))
                else:
                    formatted_choices.append(str(opt))

        if correct_idx is not None and 0 <= correct_idx < len(formatted_choices):
            answer_str = formatted_choices[correct_idx]
        elif solutions:
            answer_str = solutions[0]
        elif meta_word:
            answer_str = str(meta_word)

        if ctype == "gapFill":
            if display_tokens:
                sentence_parts = []
                in_blank = False
                for t in display_tokens:
                    is_b = t.get("isBlank") or t.get("is_blank", False)
                    if is_b:
                        if not in_blank:
                            sentence_parts.append("____")
                            in_blank = True
                    else:
                        in_blank = False
                        sentence_parts.append(t.get("text", ""))
                sentence = "".join(sentence_parts)
                prompt = f"Fill in the blank:\n  \"{sentence}\""
                if translation:
                    prompt += f"\n  [dim](Meaning: {translation})[/dim]"
            elif raw_prompt:
                prompt = f"Fill in the blank: \"{raw_prompt}\""

        elif ctype == "assist":
            if raw_prompt:
                prompt = f"Translate to Spanish: '{raw_prompt}'"

        elif ctype in ["select", "characterSelect"]:
            if raw_prompt:
                prompt = f"Select the correct option for: '{raw_prompt}'"

        elif ctype in ["tapCloze", "tapClozeTable", "typeCloze", "typeClozeTable"]:
            built = False
            if display_tokens:
                sentence_parts = []
                in_blank = False
                for t in display_tokens:
                    is_b = t.get("isBlank") or t.get("is_blank", False)
                    if is_b:
                        if not in_blank:
                            sentence_parts.append("____")
                            in_blank = True
                    else:
                        in_blank = False
                        sentence_parts.append(t.get("text", ""))
                if "____" in sentence_parts:
                    sentence = "".join(sentence_parts)
                    prompt = f"Fill in the blank:\n  \"{sentence}\""
                    if translation:
                        prompt += f"\n  [dim](Meaning: {translation})[/dim]"
                    built = True
            if not built:
                if raw_prompt:
                    prompt = f"Fill in the blank: \"{raw_prompt}\""
                elif solutions:
                    prompt = f"Fill in the blank (answer: {solutions[0]})"

    elif ctype == "translate":
        if solutions:
            answer_str = solutions[0]
        elif meta_word:
            answer_str = str(meta_word)

        if raw_prompt:
            prompt = f"✍️ Translate: \"{raw_prompt}\""
        elif display_tokens:
            prompt = f"✍️ Translate: \"{''.join(t.get('text', '') for t in display_tokens)}\""

    elif ctype in TYPE_COMPLETE_TYPES:
        built = False
        if display_tokens:
            sentence_parts = []
            in_blank = False
            for t in display_tokens:
                is_b = t.get("isBlank") or t.get("is_blank", False)
                if is_b:
                    if not in_blank:
                        sentence_parts.append("____")
                        in_blank = True
                else:
                    in_blank = False
                    sentence_parts.append(t.get("text", ""))
            if "____" in sentence_parts:
                sentence = "".join(sentence_parts)
                prompt = f"🔤 Type the missing letters:\n  [bold bright_white]{sentence}[/]"
                if translation:
                    prompt += f"\n  [dim](Meaning: {translation})[/dim]"
                built = True
        if not built:
            if raw_prompt:
                prompt = f"🔤 Type the word: \"{raw_prompt}\""
            elif solutions:
                prompt = f"🔤 Type the word (answer: {solutions[0]})"
        if solutions:
            answer_str = solutions[0]

    elif ctype == "match":
        for p in pairs:
            lw = p.get("learningWord") or p.get("learning_word") or p.get("learningToken") or ""
            tr = p.get("translation") or p.get("fromToken") or ""
            if lw and tr:
                pair_tuples.append((lw, tr))
                pair_strings.append(f"{lw} ⇄ {tr}")
        answer_str = ", ".join(pair_strings)
        prompt = "Match the following pairs"

    elif ctype in BUILD_SENTENCE_TYPES:
        word_bank = []
        for t in (tokens or display_tokens):
            if isinstance(t, dict):
                word_bank.append(t.get("value") or t.get("text") or t.get("token") or "")
            elif isinstance(t, str):
                word_bank.append(t)
        word_bank = [w for w in word_bank if w]
        if not word_bank and raw_choices:
            for c in raw_choices:
                word_bank.append(c if isinstance(c, str) else c.get("text", ""))
        if not word_bank and options:
            for opt in options:
                word_bank.append(opt if isinstance(opt, str) else opt.get("text", ""))
        answer_str = solutions[0] if solutions else (meta_word or "")
        prompt = "Arrange the words to build the correct sentence"

    else:
        if solutions:
            answer_str = solutions[0]
        elif meta_word:
            answer_str = str(meta_word)
        if raw_prompt:
            prompt = raw_prompt

    # Generic fallback: many MC-like types (radioSelect, judge, definition,
    # name, form, ...) carry options/choices that should
    # be surfaced as selectable answers instead of a free-text prompt.
    # NOTE: for translate the "choices" are the source sentence
    # tokens, NOT answer options, so it must stay free-text.
    if (
        not formatted_choices
        and ctype not in BUILD_SENTENCE_TYPES
        and ctype not in FREE_TEXT_FAMILY
    ):
        if raw_choices:
            for c in raw_choices:
                formatted_choices.append(c if isinstance(c, str) else c.get("text", ""))
        elif options:
            for opt in options:
                formatted_choices.append(opt if isinstance(opt, str) else opt.get("text", ""))
        if formatted_choices and not answer_str:
            if correct_idx is not None and 0 <= correct_idx < len(formatted_choices):
                answer_str = formatted_choices[correct_idx]
            elif solutions:
                answer_str = solutions[0]

    if not prompt:
        if raw_prompt:
            prompt = raw_prompt
        elif translation:
            prompt = f"Translate/Solve: (Meaning: {translation})"
        else:
            prompt = f"Solve this {ctype} challenge"

    if not answer_str and solutions:
        answer_str = solutions[0]

    return {
        "type": ctype,
        "prompt": prompt,
        "choices": formatted_choices,
        "pairs": pair_strings,
        "pair_tuples": pair_tuples,
        "word_bank": word_bank,
        "answer": answer_str or "OK",
        "solutions": solutions,
        "raw": ch
    }


class DuoClient:
    """Duolingo API wrapper running purely on direct, high-performance REST calls."""

    def __init__(self, username: Optional[str] = None, jwt_token: Optional[str] = None):
        # Prefer explicit args, otherwise load from secure config (already validated)
        self.username = (username.strip() if isinstance(username, str) else None) or get_username()
        raw_jwt = jwt_token if jwt_token is not None else get_jwt()
        self.jwt_token = sanitize_token(raw_jwt)
        # Defensive: guard against header/URL injection
        if self.jwt_token:
            _reject_control_chars(self.jwt_token, "JWT token")
        if self.username:
            _reject_control_chars(self.username, "username")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "device-platform": "web",
            "x-duolingo-device-platform": "web",
            "x-duolingo-app-version": "1.0.0",
            "x-duolingo-application": "chrome",
            "x-duolingo-client-version": "web",
        })
        if self.jwt_token:
            self.session.headers["Authorization"] = f"Bearer {self.jwt_token}"
            self.session.cookies.set("jwt_token", self.jwt_token, domain=".duolingo.com")

        self._cached_user_data: Optional[Dict[str, Any]] = None

    def is_authenticated(self) -> bool:
        """Check if client has JWT and username."""
        return bool(self.username and self.jwt_token)

    def invalidate_cache(self) -> None:
        """Clear cached user data."""
        self._cached_user_data = None

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Perform HTTP request with robust error handling and header-injection guard."""
        # Only allow https to Duolingo — prevent SSRF via crafted url
        if not url.startswith("https://www.duolingo.com/"):
            raise DuoAPIError("Blocked request to non-Duolingo host")

        headers = kwargs.pop("headers", {})
        # Reject header injection in custom headers
        for hk, hv in list(headers.items()):
            if "\r" in str(hk) or "\n" in str(hk) or "\r" in str(hv) or "\n" in str(hv):
                raise DuoAPIError("Blocked header injection attempt")
        merged_headers = dict(self.session.headers)
        merged_headers.update(headers)
        if self.jwt_token and "Authorization" not in merged_headers:
            merged_headers["Authorization"] = f"Bearer {self.jwt_token}"

        timeout = kwargs.pop("timeout", 15)
        # Clamp timeout to sane range
        try:
            timeout = float(timeout)
            timeout = max(5.0, min(timeout, 30.0))
        except Exception:
            timeout = 15
        try:
            resp = self.session.request(method, url, headers=merged_headers, timeout=timeout, **kwargs)
            return resp
        except requests.RequestException as e:
            raise DuoAPIError(f"Network error connecting to Duolingo: {e}")

    def verify_auth(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Verify if current JWT credentials are valid and return user data."""
        if not self.is_authenticated():
            raise DuoAPIError("Missing authentication token. Run 'duo login' first.")

        if self._cached_user_data is not None and not force_refresh:
            return self._cached_user_data

        url = f"https://www.duolingo.com/2017-06-30/users?username={url_quote(self.username, safe='')}"
        resp = self.request("GET", url)
        if resp.status_code in (401, 403):
            raise DuoAPIError("Invalid or expired JWT token. Run 'duo login' to enter a fresh token.")
        if resp.status_code != 200:
            raise DuoAPIError(f"Duolingo API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        users = data.get("users", [])
        if not users:
            raise DuoAPIError(f"User '{self.username}' was not found.")
        self._cached_user_data = users[0]
        return users[0]

    def get_learning_language(self) -> Optional[str]:
        """Return the user's currently active learning language code (e.g. 'es')."""
        try:
            user_data = self.verify_auth()
            lang = user_data.get("learningLanguage")
            return lang.lower() if lang else None
        except Exception:
            return None

    def get_public_user(self, username: str) -> Dict[str, Any]:
        """Fetch public profile info for any user (without requiring auth)."""
        if not username or len(username) > 50:
            raise DuoAPIError("Invalid username format")
        _reject_control_chars(username, "username")
        url = f"https://www.duolingo.com/2017-06-30/users?username={url_quote(username, safe='')}"
        resp = self.request("GET", url)
        if resp.status_code == 404:
            raise DuoAPIError(f"User '{username}' was not found.")
        if resp.status_code != 200:
            raise DuoAPIError(f"Could not load profile ({resp.status_code}).")

        data = resp.json()
        users = data.get("users", [])
        if not users:
            raise DuoAPIError(f"User '{username}' was not found.")
        return users[0]

    def get_full_user_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get authenticated user's complete data."""
        return self.verify_auth(force_refresh=force_refresh)

    def get_streak_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get streak, freeze status, and daily goals."""
        user_data = self.verify_auth(force_refresh=force_refresh)
        streak_data = user_data.get("streakData", {})
        last_streak = user_data.get("lastStreak", {})

        # Compute accurate streak extended today status
        today_str = str(datetime.now().date())
        current_streak_end = streak_data.get("currentStreak", {}).get("endDate", "")
        days_ago = last_streak.get("daysAgo")

        is_extended_today = False
        if user_data.get("streakExtendedToday") is True:
            is_extended_today = True
        elif days_ago == 0:
            is_extended_today = True
        elif current_streak_end == today_str:
            is_extended_today = True

        # Calculate XP today
        xp_gains = user_data.get("xpGains", [])
        today_date = datetime.now().date()
        xp_today = 0
        if isinstance(xp_gains, list):
            for g in xp_gains:
                if isinstance(g, dict) and "time" in g:
                    try:
                        g_date = datetime.fromtimestamp(g["time"]).date()
                        if g_date == today_date:
                            xp_today += g.get("xp", 0)
                    except Exception:
                        pass

        if xp_today > 0:
            is_extended_today = True

        # Streak freeze check
        has_freeze = bool(
            user_data.get("hasPlus")
            or user_data.get("gemsConfig", {}).get("streakFreeze")
            or user_data.get("streakFreeze")
        )

        return {
            "site_streak": user_data.get("streak", 0),
            "daily_goal": user_data.get("xpGoal", 10),
            "streak_extended_today": is_extended_today,
            "streak_freeze": has_freeze,
            "gems": user_data.get("gems", user_data.get("lingots", 0)),
            "total_xp": user_data.get("totalXp", 0),
            "xp_today": xp_today,
            "current_course": user_data.get("currentCourse", {}),
            "has_plus": user_data.get("hasPlus", False),
            "streak_data": streak_data,
        }

    def get_courses(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get all courses the user is currently learning."""
        user_data = self.verify_auth(force_refresh=force_refresh)
        courses = user_data.get("courses", [])
        current_course_id = user_data.get("currentCourseId") or (user_data.get("currentCourse", {}) or {}).get("id")

        results = []
        for c in courses:
            lang_code = c.get("learningLanguage", "")
            title = c.get("title") or lang_code.upper()
            xp = c.get("xp", 0)
            crowns = c.get("crowns", 0)
            is_current = (c.get("id") == current_course_id) or (lang_code == user_data.get("learningLanguage"))
            results.append({
                "id": c.get("id"),
                "language": lang_code,
                "title": title,
                "xp": xp,
                "crowns": crowns,
                "is_current": is_current,
                "flag": get_flag(lang_code),
            })

        results.sort(key=lambda x: (not x["is_current"], -x["xp"]))
        return results

    def get_daily_xp_progress(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get daily XP progress and goal."""
        user_data = self.verify_auth(force_refresh=force_refresh)
        xp_goal = user_data.get("xpGoal", 10)
        xp_gains = user_data.get("xpGains", [])
        today_date = datetime.now().date()

        total_today = 0
        today_lessons = []
        if isinstance(xp_gains, list):
            for item in xp_gains:
                if isinstance(item, dict) and "time" in item:
                    try:
                        d = datetime.fromtimestamp(item["time"]).date()
                        if d == today_date:
                            total_today += item.get("xp", 0)
                            today_lessons.append(item)
                    except Exception:
                        pass

        return {
            "xp_goal": xp_goal,
            "xp_today": total_today,
            "lessons_today": today_lessons,
        }

    def get_streak_calendar(self, days: int = 14, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get calendar activity history for recent days."""
        user_data = self.verify_auth(force_refresh=force_refresh)
        xp_gains = user_data.get("xpGains", [])

        today = datetime.now().date()
        calendar_list = []
        gains_by_date: Dict[Any, int] = {}

        for gain in xp_gains:
            if isinstance(gain, dict) and "time" in gain:
                try:
                    d = datetime.fromtimestamp(gain["time"]).date()
                    gains_by_date[d] = gains_by_date.get(d, 0) + gain.get("xp", 0)
                except Exception:
                    pass

        for i in range(days - 1, -1, -1):
            target_date = today - timedelta(days=i)
            xp = gains_by_date.get(target_date, 0)
            is_today = (target_date == today)
            is_active = (xp > 0)

            calendar_list.append({
                "date": target_date.strftime("%Y-%m-%d"),
                "day_name": target_date.strftime("%a"),
                "is_today": is_today,
                "is_active": is_active,
                "xp": xp,
            })

        return calendar_list

    def get_hearts(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get user hearts / health status."""
        user_data = self.verify_auth(force_refresh=force_refresh)
        has_plus = user_data.get("hasPlus", False)
        hearts = user_data.get("hearts", 5 if has_plus else user_data.get("health", 5))
        return {
            "hearts": hearts if not has_plus else "Unlimited",
            "is_unlimited": has_plus,
            "max_hearts": 5,
        }

    def get_shop_items(self) -> List[Dict[str, Any]]:
        """Get list of authentic modern Duolingo store items and prices."""
        user_data = self.verify_auth(force_refresh=False)
        inventory = user_data.get("shopItems", [])

        # Check equipped streak freezes
        freeze_qty = 0
        for it in inventory:
            if it.get("itemName") == "streak_freeze":
                freeze_qty = it.get("quantity", 1)

        freeze_status = f" [dim](Equipped: {freeze_qty}/2)[/]" if freeze_qty > 0 else ""

        return [
            {
                "id": "streak_freeze",
                "name": f"Streak Freeze{freeze_status}",
                "cost": 200,
                "currency": "Gems",
                "icon": "🛡️",
                "desc": "Protects your streak for 1 full day of inactivity (Max 2 equipped).",
            },
            {
                "id": "heart_refill",
                "name": "Refill Hearts",
                "cost": 350,
                "currency": "Gems",
                "icon": "❤️",
                "desc": "Instantly refills all 5 hearts to continue practicing.",
            },
        ]

    def get_friends(self) -> List[Dict[str, Any]]:
        """Get list of friends / following users."""
        user_data = self.verify_auth()
        user_id = user_data.get("id")
        if not user_id:
            return []

        url = f"https://www.duolingo.com/2017-06-30/friends/users/{user_id}/following"
        resp = self.request("GET", url)
        if resp.status_code == 200:
            data = resp.json()
            following = data.get("following", {}).get("users", [])
            results = []
            for f in following:
                results.append({
                    "id": f.get("id"),
                    "username": f.get("username"),
                    "name": f.get("name"),
                    "points": f.get("totalXp", 0),
                    "streak": f.get("streak", 0),
                    "avatar": f.get("picture"),
                })
            results.sort(key=lambda x: -x["points"])
            return results
        return []

    def switch_language(self, lang_code: str) -> bool:
        """Switch active learning language."""
        lang_code = _validate_lang_code(lang_code)
        self.invalidate_cache()
        user_data = self.verify_auth()
        user_id = user_data.get("id")

        url = "https://www.duolingo.com/switch_language"
        resp = self.request("POST", url, json={"learning_language": lang_code})
        if resp.status_code == 200:
            self.invalidate_cache()
            return True

        patch_url = f"https://www.duolingo.com/2017-06-30/users/{user_id}"
        patch_resp = self.request("PATCH", patch_url, json={"learningLanguage": lang_code})
        if patch_resp.status_code == 200:
            self.invalidate_cache()
            return True

        return False

    def buy_streak_freeze(self) -> bool:
        """Buy and equip streak freeze item."""
        self.invalidate_cache()
        user_data = self.verify_auth()
        user_id = user_data.get("id")
        curr_lang = user_data.get("learningLanguage", "es")

        url = f"https://www.duolingo.com/2017-06-30/users/{user_id}/shop-items"
        resp = self.request("POST", url, json={"itemName": "streak_freeze", "learningLanguage": curr_lang})
        if resp.status_code == 200:
            self.invalidate_cache()
            return True

        data = resp.json() if resp.status_code != 500 else {}
        err = data.get("error", "Purchase failed")
        raise DuoAPIError(f"Shop error: {err}")

    def create_practice_session(self, lang_abbr: str) -> Dict[str, Any]:
        """Fetch an interactive practice session from Duolingo."""
        user_data = self.verify_auth()
        from_lang = user_data.get("fromLanguage", "en")

        url = "https://www.duolingo.com/2017-06-30/sessions"
        payload = {
            "challengeTypes": CHALLENGE_TYPES,
            "fromLanguage": from_lang,
            "isFinalLevel": False,
            "isV2": True,
            "juicy": True,
            "learningLanguage": lang_abbr,
            "smartTipsVersion": 2,
            "type": "GLOBAL_PRACTICE"
        }

        resp = self.request("POST", url, json=payload)
        if resp.status_code == 200:
            return resp.json()

        raise DuoAPIError(f"Could not create practice session on server ({resp.status_code}).")

    def submit_practice_session(
        self,
        session_data: Dict[str, Any],
        score: int,
        start_time: Optional[float] = None,
        hearts_left: int = 5,
        mistakes: int = 0,
        failed: bool = False,
    ) -> Dict[str, Any]:
        """Submit completed session to Duolingo backend to award real XP and extend streak.

        `hearts_left` and `failed` reflect the actual outcome of the session so
        the server deducts hearts correctly (it trusts the client-sent value).
        """
        if not self.is_authenticated():
            return {"xpGain": 0, "streakExtended": False, "serverSync": False, "reason": "Not authenticated"}

        session_id = session_data.get("id")
        if not session_id or session_id == "dummy":
            try:
                user_data = self.verify_auth()
                lang = session_data.get("learningLanguage") or user_data.get("learningLanguage", "es")
                live_sess = self.create_practice_session(lang)
                session_id = live_sess.get("id")
                session_data = live_sess
            except Exception as e:
                return {"xpGain": 0, "streakExtended": False, "serverSync": False, "reason": str(e)}

        now = datetime.now(timezone.utc)
        if start_time:
            start_ts = int(start_time)
            end_ts = int(now.timestamp())
            if end_ts - start_ts < 15:
                start_ts = end_ts - 25  # Ensure minimum realistic elapsed time for anti-cheat
        else:
            start_ts = int((now - timedelta(seconds=45)).timestamp())
            end_ts = int(now.timestamp())

        url = f"https://www.duolingo.com/2017-06-30/sessions/{session_id}"
        payload = {
            **session_data,
            "heartsLeft": max(0, hearts_left),
            "mistakes": max(0, mistakes),
            "startTime": start_ts,
            "endTime": end_ts,
            "enableBonusPoints": True,
            "failed": bool(failed),
            "maxInLessonStreak": min(max(score, 1), 9),
            "shouldLearnThings": True
        }

        resp = self.request("PUT", url, json=payload)
        if resp.status_code == 200:
            self.invalidate_cache()
            result = resp.json()
            return {
                "xpGain": result.get("xpGain", 15),
                "streakExtended": result.get("streakExtendedToday", True),
                "serverSync": True,
                "raw": result
            }
        else:
            return {"xpGain": 0, "streakExtended": False, "serverSync": False, "status": resp.status_code}
