"""
Configuration and credentials manager for duo-cli.

Credentials are resolved with priority:
  1. OS environment variables
  2. Local .env in current working directory (resolved dynamically)
  3. Global ~/.duo-cli/config.json

Design goals:
- small, readable helpers — easy to extend with new keys
- strict validation, atomic writes, restrictive file permissions
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Callable, Dict, Optional

# ---------------------------------------------------------------------------
# Paths & validation
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".duo-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _local_env_file() -> Path:
    """Resolve .env in the *current* working directory at call time."""
    return Path.cwd() / ".env"


# Backwards-compat alias — some external code may import LOCAL_ENV_FILE
LOCAL_ENV_FILE = _local_env_file()

# Validation patterns — intentionally conservative and easy to extend
_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{2,50}$")
_LANG_RE = re.compile(r"^[a-z]{2,3}(-[a-z]{2,4})?$", re.IGNORECASE)
_JWT_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def parse_env_file(filepath: Path) -> Dict[str, str]:
    """Parse a simple KEY=VALUE .env file without external dependencies."""
    data: Dict[str, str] = {}
    if not filepath.exists() or not filepath.is_file():
        return data
    # Prevent reading huge / symlink-chasing files
    try:
        if filepath.stat().st_size > 64 * 1024:
            return data
        if filepath.is_symlink():
            try:
                target = filepath.resolve()
                cwd = Path.cwd().resolve()
                # Block symlinks pointing outside cwd (potential secret exfiltration)
                if cwd not in target.parents and target != cwd:
                    return data
                # Also block if resolved size is unexpectedly large
                if target.stat().st_size > 64 * 1024:
                    return data
            except Exception:
                return data
    except Exception:
        pass
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


def _read_config() -> Dict:
    """Read global config.json safely — returns {} on any error."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def ensure_config_dir() -> Path:
    """Ensure ~/.duo-cli exists with 0o700 (no group/other access)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except Exception:
        pass
    return CONFIG_DIR


def _restrict_file_permissions(path: Path) -> None:
    """Set file to 0o600 where supported (owner read/write only)."""
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _atomic_write_json(path: Path, data: Dict) -> None:
    """Write JSON atomically and restrict permissions to 0o600."""
    ensure_config_dir()
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".config_tmp_")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        _restrict_file_permissions(Path(tmp_path))
        Path(tmp_path).replace(path)
        _restrict_file_permissions(path)
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _is_valid_jwt_format(token: str) -> bool:
    """Strict JWT shape check: 3 base64url parts, no control chars, no injection."""
    if not token or "\r" in token or "\n" in token or "\0" in token:
        return False
    if " " in token or "\t" in token:
        return False
    parts = token.split(".")
    if len(parts) != 3:
        return False
    for p in parts:
        if not p or len(p) < 8 or len(p) > 2048:
            return False
        if not _JWT_B64URL_RE.match(p):
            return False
    return True


def sanitize_jwt(token: Optional[str]) -> Optional[str]:
    """Clean and validate a JWT — returns None if malformed or injectable."""
    if not token:
        return None
    raw = token.strip()
    if "jwt_token=" in raw:
        for part in raw.split(";"):
            part = part.strip()
            if part.startswith("jwt_token="):
                raw = part.split("jwt_token=")[1].strip()
                break
    raw = raw.strip()
    if "\r" in raw or "\n" in raw or "\0" in raw:
        return None
    parts = raw.split(".")
    if len(parts) >= 3:
        raw = ".".join(parts[:3])
    raw = raw.strip()
    if not _is_valid_jwt_format(raw):
        return None
    return raw


def _resolve_from_chain(
    env_keys: list[str],
    file_keys: list[str],
    validator: Callable[[str], Optional[str]],
) -> Optional[str]:
    """
    Generic resolver: env vars → .env → config.json.
    `validator` should return cleaned value or None if invalid.
    """
    # 1. Environment
    for ek in env_keys:
        raw = os.environ.get(ek)
        if raw and raw.strip():
            cleaned = validator(raw)
            if cleaned:
                return cleaned
    # 2. Local .env (dynamically resolved)
    local_env = parse_env_file(_local_env_file())
    for fk in file_keys:
        raw = local_env.get(fk)
        if raw:
            cleaned = validator(raw)
            if cleaned:
                return cleaned
    # 3. Global config.json
    data = _read_config()
    for ck in file_keys:
        # config uses lower_snake keys; try both raw and lower
        for key in (ck.lower(), ck):
            raw = data.get(key) or data.get(key.lower())
            if raw and isinstance(raw, str):
                cleaned = validator(raw)
                if cleaned:
                    return cleaned
            elif raw:
                cleaned = validator(str(raw))
                if cleaned:
                    return cleaned
    return None


# ---------------------------------------------------------------------------
# Public API — easy to extend with new credential types
# ---------------------------------------------------------------------------


def get_jwt() -> Optional[str]:
    """Return JWT with priority: env → .env → config.json."""
    return _resolve_from_chain(
        env_keys=["DUOLINGO_JWT", "DUOLINGO_JWT_TOKEN"],
        file_keys=["DUOLINGO_JWT", "DUOLINGO_JWT_TOKEN", "jwt_token", "jwt"],
        validator=lambda v: sanitize_jwt(v),
    )


def get_username() -> Optional[str]:
    """Return username with priority: env → .env → config.json."""

    def _valid_user(v: str) -> Optional[str]:
        u = v.strip()
        return u if _USERNAME_RE.match(u) else None

    # Custom chain because config key is "username" (not env key)
    # 1. Env
    for ek in ["DUOLINGO_USERNAME", "DUOLINGO_USER"]:
        raw = os.environ.get(ek)
        if raw and raw.strip() and _USERNAME_RE.match(raw.strip()):
            return raw.strip()
    # 2. .env
    local_env = parse_env_file(_local_env_file())
    for fk in ["DUOLINGO_USERNAME", "DUOLINGO_USER"]:
        raw = local_env.get(fk)
        if raw and _USERNAME_RE.match(str(raw).strip()):
            return str(raw).strip()
    # 3. Config
    data = _read_config()
    raw = data.get("username")
    if raw and isinstance(raw, str) and _USERNAME_RE.match(raw.strip()):
        return raw.strip()
    return None


def set_credentials(username: str, jwt_token: str) -> None:
    """Store username and JWT in ~/.duo-cli/config.json with 0o600."""
    clean_user = (username or "").strip()
    if not _USERNAME_RE.match(clean_user):
        raise ValueError("Invalid username format — use 2-50 chars: letters, digits, . _ -")
    clean_jwt = sanitize_jwt(jwt_token)
    if not clean_jwt:
        raise ValueError("Invalid JWT token format — expected 3 base64url parts (header.payload.signature)")

    data = _read_config()
    data["username"] = clean_user
    data["jwt_token"] = clean_jwt
    _atomic_write_json(CONFIG_FILE, data)

    # Remove legacy .env in ~/.duo-cli if present
    legacy_env = CONFIG_DIR / ".env"
    if legacy_env.exists():
        try:
            legacy_env.unlink()
        except Exception:
            pass


def clear_config() -> None:
    """Wipe stored config.json from disk."""
    for p in (CONFIG_FILE, CONFIG_DIR / ".env"):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


def get_jwt_expiry() -> Optional[int]:
    """Return JWT exp timestamp if decodable, else None."""
    import base64

    jwt = get_jwt()
    if not jwt:
        return None
    try:
        parts = jwt.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
        exp = data.get("exp")
        if isinstance(exp, int) and exp > 0:
            return exp
    except Exception:
        return None
    return None


def is_authenticated() -> bool:
    """Check if valid JWT and username are configured."""
    return bool(get_jwt() and get_username())


def get_preset_language() -> Optional[str]:
    """Return locally saved default practice language (preset), if any."""
    data = _read_config()
    raw = data.get("preset_language")
    if raw and isinstance(raw, str) and _LANG_RE.match(raw.strip()):
        return raw.strip().lower()
    return None


def set_preset_language(lang_code: str) -> None:
    """Persist default practice language (preset) to config.json."""
    clean = (lang_code or "").strip().lower()
    if not clean or not _LANG_RE.match(clean):
        raise ValueError(f"Invalid language code: {lang_code!r} — expected 2-3 letter code like 'es', 'de'")
    data = _read_config()
    data["preset_language"] = clean
    _atomic_write_json(CONFIG_FILE, data)
