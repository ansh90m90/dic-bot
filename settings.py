"""Schema-driven, runtime-editable server settings (backed by ``settings.json``).

The SCHEMA defines every key: its type, default, description, and (for numeric
keys) min/max bounds. Cogs read settings live on every use, so edits apply
immediately — via the ``/settings`` command or by editing ``settings.json``.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict

import config

SETTINGS_PATH: Path = Path(config.SETTINGS_PATH)

SCHEMA: Dict[str, Dict[str, Any]] = {
    # --- feature toggles -------------------------------------------------
    "features_anomalies": {"type": "bool", "default": True,
                           "desc": "Random Spirit World Anomalies."},
    "features_madness": {"type": "bool", "default": True,
                         "desc": "The corruption / madness engine."},
    "features_tarot": {"type": "bool", "default": True,
                       "desc": "The anonymous Tarot Club."},
    "features_digestion": {"type": "bool", "default": True,
                           "desc": "Digestion gained from activity."},
    "features_shop": {"type": "bool", "default": True, "desc": "The /shop command."},
    "features_daily": {"type": "bool", "default": True, "desc": "The /daily reward."},
    "features_roles": {"type": "bool", "default": True,
                       "desc": "Give members a role for their Pathway + Sequence."},
    "advancement_hazard_enabled": {"type": "bool", "default": True,
                                   "desc": "Enable ritual backlash hazard during advancement."},
    # --- roles -----------------------------------------------------------
    "admin_role": {"type": "str", "default": config.ADMIN_ROLE,
                   "desc": "Role name for the Archangel Council tier."},
    "mod_role": {"type": "str", "default": config.MOD_ROLE,
                 "desc": "Role name for the Moderator tier."},
    "tarot_role": {"type": "str", "default": config.TAROT_ROLE,
                   "desc": "Role name associated with the Tarot Club."},
    # --- oracle ----------------------------------------------------------
    "oracle_daily_limit": {"type": "int", "min": 0, "max": 1000,
                           "default": config.ORACLE_DAILY_LIMIT,
                           "desc": "Daily /ask-oracle limit for Mortals (0 = unlimited)."},
    # --- madness ---------------------------------------------------------
    "corruption_breakdown_threshold": {"type": "float", "min": 1, "max": 100,
                                       "default": config.CORRUPTION_BREAKDOWN_THRESHOLD,
                                       "desc": "Corruption % that triggers a Mental Breakdown."},
    "fog_timeout_minutes": {"type": "int", "min": 1, "max": 1440,
                            "default": config.FOG_TIMEOUT_MINUTES,
                            "desc": "Minutes banished to the Fog of History."},
    # --- anomalies -------------------------------------------------------
    "anomaly_min_interval": {"type": "int", "min": 60, "max": 86400,
                             "default": config.ANOMALY_MIN_INTERVAL,
                             "desc": "Minimum seconds between random anomalies."},
    "anomaly_max_interval": {"type": "int", "min": 60, "max": 86400,
                             "default": config.ANOMALY_MAX_INTERVAL,
                             "desc": "Maximum seconds between random anomalies."},
    "anomaly_window": {"type": "int", "min": 10, "max": 3600,
                       "default": config.ANOMALY_WINDOW,
                       "desc": "Seconds an anomaly window stays open."},
    # --- economy & progression ------------------------------------------
    "starting_gold": {"type": "int", "min": 0, "max": 1000000,
                      "default": config.STARTING_GOLD,
                      "desc": "Gold Pounds a new Beyonder starts with."},
    "digest_per_message": {"type": "float", "min": 0, "max": 100,
                           "default": config.DIGEST_PER_MESSAGE,
                           "desc": "Base digestion % per activity tick (Sequence 9)."},
    "activity_digest_cooldown": {"type": "int", "min": 0, "max": 86400,
                                 "default": config.ACTIVITY_DIGEST_COOLDOWN,
                                 "desc": "Base seconds between chat digestion ticks."},
    "min_digest_message_len": {"type": "int", "min": 1, "max": 200,
                               "default": config.MIN_DIGEST_MESSAGE_LEN,
                               "desc": "Minimum characters in chat message to trigger digestion."},
    # --- daily reward ----------------------------------------------------
    "daily_gold": {"type": "int", "min": 0, "max": 1000000, "default": 50,
                   "desc": "Gold Pounds granted by /daily."},
    "daily_tarot": {"type": "int", "min": 0, "max": 1000, "default": 1,
                    "desc": "Tarot Coins granted by /daily."},
    # --- shop ------------------------------------------------------------
    "shop_common_price": {"type": "int", "min": 0, "max": 1000000, "default": 50,
                          "desc": "Price of a common ingredient."},
    "shop_uncommon_price": {"type": "int", "min": 0, "max": 1000000, "default": 200,
                            "desc": "Price of an uncommon ingredient."},
    "shop_rare_price": {"type": "int", "min": 0, "max": 1000000, "default": 800,
                        "desc": "Price of a rare ingredient."},
    "shop_legendary_price": {"type": "int", "min": 0, "max": 1000000, "default": 3000,
                             "desc": "Price of a legendary ingredient."},
}

DEFAULTS: Dict[str, Any] = {k: v["default"] for k, v in SCHEMA.items()}


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._data = {**DEFAULTS, **data}
        except (json.JSONDecodeError, OSError):
            pass
        self.save()

    def save(self) -> None:
        try:
            with self._lock:
                self.path.write_text(
                    json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
                )
        except OSError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> Any:
        """Validate + coerce ``value`` against SCHEMA, persist, and return it."""
        if key not in SCHEMA:
            raise ValueError(f"Unknown setting: `{key}`.")
        spec = SCHEMA[key]
        coerced = self._coerce(value, spec)
        self._data[key] = coerced
        self.save()
        return coerced

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._data = dict(DEFAULTS)
        else:
            if key not in SCHEMA:
                raise ValueError(f"Unknown setting: `{key}`.")
            self._data[key] = SCHEMA[key]["default"]
        self.save()

    def all(self) -> Dict[str, Any]:
        return dict(self._data)

    @staticmethod
    def _coerce(value: Any, spec: Dict[str, Any]) -> Any:
        kind = spec["type"]
        if kind == "bool":
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in ("true", "1", "yes", "on", "y"):
                return True
            if s in ("false", "0", "no", "off", "n"):
                return False
            raise ValueError(f"Expected true/false for a boolean, got `{value}`.")
        if kind == "int":
            try:
                num = int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Expected an integer, got `{value}`.")
        elif kind == "float":
            try:
                num = float(value)
            except (ValueError, TypeError):
                raise ValueError(f"Expected a number, got `{value}`.")
        else:
            return str(value)

        lo, hi = spec.get("min"), spec.get("max")
        if lo is not None and num < lo:
            raise ValueError(f"`{num}` must be at least {lo}.")
        if hi is not None and num > hi:
            raise ValueError(f"`{num}` must be at most {hi}.")
        return num


settings = SettingsStore(SETTINGS_PATH)
