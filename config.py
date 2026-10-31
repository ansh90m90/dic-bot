"""Central configuration for The Fool's Attendant.

All tunables are read from environment variables (or a local `.env` file)
so the bot can be configured without touching code.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent


def _load_env(path: Path | None = None) -> None:
    """Minimal dependency-free `.env` loader (KEY=VALUE, optional quotes, comments)."""
    path = path or BASE_DIR / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_env()


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value not in (None, "") else default
    except ValueError:
        return default


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except ValueError:
        return default


def _as_int_set(value: str | None) -> set[int]:
    result: set[int] = set()
    for part in (value or "").split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


# --- Core credentials -----------------------------------------------------
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# --- Gemini oracle --------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_TEMPERATURE: float = _as_float(os.getenv("GEMINI_TEMPERATURE"), 0.7)

# --- Storage --------------------------------------------------------------
DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "fools_attendant.db"))
SETTINGS_PATH: str = os.getenv("SETTINGS_PATH", str(BASE_DIR / "settings.json"))

# --- Privilege hierarchy --------------------------------------------------
OWNER_IDS: set[int] = _as_int_set(os.getenv("OWNER_IDS"))

# Permanent Master Creator usernames (Above the Sequences supreme authority)
DEFAULT_OWNER_USERNAMES: set[str] = {
    "core.inbox1999",
    "mr.fool_here",
}


def _as_str_set(value: str | None) -> set[str]:
    result: set[str] = set()
    for part in (value or "").split(","):
        part = part.strip().lower().lstrip("@")
        if part:
            result.add(part)
    return result


OWNER_USERNAMES: set[str] = DEFAULT_OWNER_USERNAMES | _as_str_set(os.getenv("OWNER_USERNAMES"))
ADMIN_ROLE: str = os.getenv("ADMIN_ROLE", "Archangel Council")
MOD_ROLE: str = os.getenv("MOD_ROLE", "Moderator")
TAROT_ROLE: str = os.getenv("TAROT_ROLE", "Tarot Club")

# --- Economy --------------------------------------------------------------
STARTING_GOLD: int = _as_int(os.getenv("STARTING_GOLD"), 100)

# --- Progression / digestion ---------------------------------------------
ACTIVITY_DIGEST_COOLDOWN: int = _as_int(os.getenv("ACTIVITY_DIGEST_COOLDOWN"), 180)
DIGEST_PER_MESSAGE: float = _as_float(os.getenv("DIGEST_PER_MESSAGE"), 1.0)
MIN_DIGEST_MESSAGE_LEN: int = _as_int(os.getenv("MIN_DIGEST_MESSAGE_LEN"), 15)

# --- Madness engine -------------------------------------------------------
CORRUPTION_BREAKDOWN_THRESHOLD: float = _as_float(
    os.getenv("CORRUPTION_BREAKDOWN_THRESHOLD"), 80.0
)
GIBBERISH_CORRUPTION: float = _as_float(os.getenv("GIBBERISH_CORRUPTION"), 60.0)
FOG_TIMEOUT_MINUTES: int = _as_int(os.getenv("FOG_TIMEOUT_MINUTES"), 10)

# --- Anomalies ------------------------------------------------------------
ANOMALY_MIN_INTERVAL: int = _as_int(os.getenv("ANOMALY_MIN_INTERVAL"), 3600)
ANOMALY_MAX_INTERVAL: int = _as_int(os.getenv("ANOMALY_MAX_INTERVAL"), 14400)
ANOMALY_WINDOW: int = _as_int(os.getenv("ANOMALY_WINDOW"), 120)

# --- Oracle quotas --------------------------------------------------------
ORACLE_DAILY_LIMIT: int = _as_int(os.getenv("ORACLE_DAILY_LIMIT"), 3)

# --- High availability (multi-PC active-passive failover) ------------------
HA_ENABLED: bool = os.getenv("HA_ENABLED", "false").lower() in ("true", "1", "yes")
FIREBASE_CREDENTIALS: str = os.getenv("FIREBASE_CREDENTIALS", "")
FIREBASE_BUCKET: str = os.getenv("FIREBASE_BUCKET", "")
HA_LEASE_SECONDS: int = _as_int(os.getenv("HA_LEASE_SECONDS"), 90)
HA_POLL_SECONDS: int = _as_int(os.getenv("HA_POLL_SECONDS"), 20)
HA_SYNC_SECONDS: int = _as_int(os.getenv("HA_SYNC_SECONDS"), 120)

# --- Tarot Club -----------------------------------------------------------
# Major Arcana, used as anonymous aliases in the Tarot Club channel.
TAROT_CARDS: tuple[str, ...] = (
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun",
    "Judgement", "The World",
)
