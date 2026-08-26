"""
Configuration and credentials manager for duo-cli.
Securely stores and loads credentials from .env and environment variables.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

CONFIG_DIR = Path.home() / ".duo-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOCAL_ENV_FILE = Path.cwd() / ".env"


def parse_env_file(filepath: Path) -> Dict[str, str]:
    """Parse a simple KEY=VALUE .env file without external dependencies."""
    data = {}
    if not filepath.exists() or not filepath.is_file():
        return data
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k:
                    data[k] = v
    except Exception:
        pass
    return data


def ensure_config_dir() -> Path:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def get_jwt() -> Optional[str]:
    """
    Return stored JWT token with priority:
    1. OS Environment Variables (DUOLINGO_JWT, DUOLINGO_JWT_TOKEN)
    2. Local .env file in current directory
    3. ~/.duo-cli/config.json
    """
    # 1. OS Environment
    env_jwt = os.environ.get("DUOLINGO_JWT") or os.environ.get("DUOLINGO_JWT_TOKEN")
    if env_jwt and env_jwt.strip():
        return env_jwt.strip()

    # 2. Local .env
    local_env = parse_env_file(LOCAL_ENV_FILE)
    if local_env.get("DUOLINGO_JWT"):
        return local_env["DUOLINGO_JWT"].strip()
    if local_env.get("DUOLINGO_JWT_TOKEN"):
        return local_env["DUOLINGO_JWT_TOKEN"].strip()

    # 3. Global config.json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("jwt_token") or data.get("jwt")
        except Exception:
            pass

    return None


def get_username() -> Optional[str]:
    """
    Return stored username with priority:
    1. OS Environment Variables (DUOLINGO_USERNAME, DUOLINGO_USER)
    2. Local .env file
    3. ~/.duo-cli/config.json
    """
    # 1. OS Environment
    env_user = os.environ.get("DUOLINGO_USERNAME") or os.environ.get("DUOLINGO_USER")
    if env_user and env_user.strip():
        return env_user.strip()

    # 2. Local .env
    local_env = parse_env_file(LOCAL_ENV_FILE)
    if local_env.get("DUOLINGO_USERNAME"):
        return local_env["DUOLINGO_USERNAME"].strip()
    if local_env.get("DUOLINGO_USER"):
        return local_env["DUOLINGO_USER"].strip()

    # 3. Global config.json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("username")
        except Exception:
            pass

    return None


def set_credentials(username: str, jwt_token: str) -> None:
    """Store username and JWT token in ~/.duo-cli/config.json."""
    ensure_config_dir()
    clean_user = username.strip()
    clean_jwt = jwt_token.strip()

    data = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    data["username"] = clean_user
    data["jwt_token"] = clean_jwt

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Remove legacy .env in ~/.duo-cli if present
    legacy_env = CONFIG_DIR / ".env"
    if legacy_env.exists():
        try:
            legacy_env.unlink()
        except Exception:
            pass


def clear_config() -> None:
    """Wipe stored config.json from disk."""
    if CONFIG_FILE.exists():
        try:
            CONFIG_FILE.unlink()
        except Exception:
            pass
    legacy_env = CONFIG_DIR / ".env"
    if legacy_env.exists():
        try:
            legacy_env.unlink()
        except Exception:
            pass


def is_authenticated() -> bool:
    """Check if valid JWT token and username are configured."""
    return bool(get_jwt() and get_username())


def get_audio_snooze_until() -> float:
    """Return unix timestamp until which audio is snoozed, or 0.0."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return float(data.get("audio_snooze_until", 0.0))
        except Exception:
            pass
    return 0.0


def set_audio_snooze(minutes: int = 15) -> None:
    """Disable audio/speaking exercises for N minutes (Duolingo app replica)."""
    import time
    ensure_config_dir()
    snooze_until = time.time() + (minutes * 60)
    data = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data["audio_snooze_until"] = snooze_until
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def is_audio_snoozed() -> bool:
    """Check if audio/speaking exercises are currently snoozed."""
    import time
    return time.time() < get_audio_snooze_until()
