"""SQLite persistence layer for The Fool's Attendant.

Synchronous sqlite3 behind a threading lock. Operations are tiny (single-row
lookups / increments), so they are safe to call directly from async command
handlers in a single-process bot.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
from settings import settings


class Database:
    def __init__(self, path: str = config.DATABASE_PATH):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        # Performance pragmas: WAL + relaxed fsync reduce I/O; a bounded page cache
        # keeps hot rows in memory instead of re-reading them from disk.
        for pragma in (
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL",
            "PRAGMA cache_size=-8000",
            "PRAGMA temp_store=MEMORY",
        ):
            try:
                self._conn.execute(pragma)
            except sqlite3.DatabaseError:
                pass
        self._create_schema()

    # --- schema -----------------------------------------------------------
    def _create_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    pathway TEXT,
                    sequence INTEGER,
                    digestion REAL NOT NULL DEFAULT 0,
                    sanity REAL NOT NULL DEFAULT 100,
                    corruption REAL NOT NULL DEFAULT 0,
                    gold INTEGER NOT NULL DEFAULT 100,
                    tarot_coins INTEGER NOT NULL DEFAULT 0,
                    joined_at TEXT,
                    last_activity_date TEXT,
                    active_days INTEGER NOT NULL DEFAULT 0,
                    last_digest_ts REAL NOT NULL DEFAULT 0,
                    corrupted_state INTEGER NOT NULL DEFAULT 0,
                    nickname_original TEXT,
                    fog_until REAL NOT NULL DEFAULT 0,
                    last_daily_date TEXT,
                    beyond_role_id TEXT,
                    equipped_artifact TEXT
                );

                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    qty INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (user_id, item_key)
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    owner_id INTEGER NOT NULL,
                    definition_key TEXT,
                    name TEXT,
                    grade INTEGER,
                    effect TEXT,
                    curse TEXT,
                    equipped INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS oracle_queries (
                    user_id INTEGER NOT NULL,
                    queried_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_oracle_user ON oracle_queries(user_id);

                CREATE TABLE IF NOT EXISTS gods (
                    pathway TEXT PRIMARY KEY,
                    holder_id INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trials (
                    user_id INTEGER PRIMARY KEY,
                    target_sequence INTEGER NOT NULL,
                    trial_kind TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tarot_aliases (
                    user_id INTEGER PRIMARY KEY,
                    alias TEXT NOT NULL,
                    card TEXT
                );

                CREATE TABLE IF NOT EXISTS anomalies (
                    channel_id INTEGER PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    ends_at REAL NOT NULL,
                    data TEXT
                );
                """
            )
        for stmt in (
            "CREATE INDEX IF NOT EXISTS idx_users_corruption ON users(corruption)",
            "CREATE INDEX IF NOT EXISTS idx_artifacts_equipped ON artifacts(equipped)",
        ):
            with self._lock, self._conn:
                self._conn.execute(stmt)
        # Migration: add last_daily_date for databases created before this column existed.
        try:
            with self._lock, self._conn:
                self._conn.execute("ALTER TABLE users ADD COLUMN last_daily_date TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            with self._lock, self._conn:
                self._conn.execute("ALTER TABLE users ADD COLUMN beyond_role_id TEXT")
        except sqlite3.OperationalError:
            pass

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def _now() -> float:
        return time.time()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock, self._conn:
            return self._conn.execute(sql, params)

    def _fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        with self._lock, self._conn:
            row = self._conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _fetchall(self, sql: str, params: tuple = ()) -> List[Dict]:
        with self._lock, self._conn:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # --- users ------------------------------------------------------------
    def ensure_user(self, user_id: int) -> Dict:
        user = self.get_user(user_id)
        if user is None:
            self._execute(
                "INSERT INTO users (user_id, gold) VALUES (?, ?)",
                (user_id, int(settings.get("starting_gold", config.STARTING_GOLD))),
            )
            user = self.get_user(user_id)
        return user  # type: ignore[return-value]

    def get_user(self, user_id: int) -> Optional[Dict]:
        return self._fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))

    def register_pathway(self, user_id: int, pathway_key: str) -> None:
        self.ensure_user(user_id)
        self._execute(
            "UPDATE users SET pathway = ?, sequence = 9, digestion = 0, joined_at = ? "
            "WHERE user_id = ?",
            (pathway_key, datetime.now(timezone.utc).isoformat(), user_id),
        )

    def set_sequence(self, user_id: int, pathway_key: str, sequence: int) -> None:
        self._execute(
            "UPDATE users SET pathway = ?, sequence = ?, digestion = 0 WHERE user_id = ?",
            (pathway_key, sequence, user_id),
        )

    def add_digestion(self, user_id: int, amount: float) -> float:
        """Add digestion, cap at 100, return the new value."""
        user = self.ensure_user(user_id)
        new_val = min(100.0, float(user["digestion"]) + amount)
        self._execute("UPDATE users SET digestion = ? WHERE user_id = ?", (new_val, user_id))
        return new_val

    def add_gold(self, user_id: int, amount: int) -> int:
        user = self.ensure_user(user_id)
        new_val = max(0, int(user["gold"]) + amount)
        self._execute("UPDATE users SET gold = ? WHERE user_id = ?", (new_val, user_id))
        return new_val

    def add_tarot(self, user_id: int, amount: int) -> int:
        user = self.ensure_user(user_id)
        new_val = max(0, int(user["tarot_coins"]) + amount)
        self._execute("UPDATE users SET tarot_coins = ? WHERE user_id = ?", (new_val, user_id))
        return new_val

    def add_corruption(self, user_id: int, amount: float) -> float:
        user = self.ensure_user(user_id)
        new_val = min(100.0, max(0.0, float(user["corruption"]) + amount))
        self._execute("UPDATE users SET corruption = ? WHERE user_id = ?", (new_val, user_id))
        return new_val

    def set_corruption(self, user_id: int, amount: float) -> float:
        new_val = min(100.0, max(0.0, amount))
        self._execute("UPDATE users SET corruption = ? WHERE user_id = ?", (new_val, user_id))
        return new_val

    def add_sanity(self, user_id: int, amount: float) -> float:
        user = self.ensure_user(user_id)
        new_val = min(100.0, max(0.0, float(user["sanity"]) + amount))
        self._execute("UPDATE users SET sanity = ? WHERE user_id = ?", (new_val, user_id))
        return new_val

    def set_sanity(self, user_id: int, amount: float) -> float:
        new_val = min(100.0, max(0.0, amount))
        self._execute("UPDATE users SET sanity = ? WHERE user_id = ?", (new_val, user_id))
        return new_val

    def touch_activity(self, user_id: int) -> int:
        """Record activity; increment active_days once per UTC day. Returns days."""
        user = self.ensure_user(user_id)
        today = self._today()
        if user["last_activity_date"] != today:
            days = int(user["active_days"]) + 1
            self._execute(
                "UPDATE users SET last_activity_date = ?, active_days = ? WHERE user_id = ?",
                (today, days, user_id),
            )
            return days
        return int(user["active_days"])

    def can_digest_from_message(self, user_id: int) -> bool:
        """True if the activity cooldown has elapsed for digestion."""
        user = self.ensure_user(user_id)
        return self._now() - float(user["last_digest_ts"]) >= int(
            settings.get("activity_digest_cooldown", config.ACTIVITY_DIGEST_COOLDOWN)
        )

    def mark_digest(self, user_id: int) -> None:
        self._execute("UPDATE users SET last_digest_ts = ? WHERE user_id = ?", (self._now(), user_id))

    def activity_tick(self, user_id: int, digestion: float, last_digest_ts: float,
                      active_days: int, last_activity_date: str) -> None:
        """Apply one atomic activity tick (digestion + cooldown + active-days)."""
        self._execute(
            "UPDATE users SET digestion = ?, last_digest_ts = ?, active_days = ?, "
            "last_activity_date = ? WHERE user_id = ?",
            (digestion, last_digest_ts, active_days, last_activity_date, user_id),
        )

    def set_beyond_role(self, user_id: int, role_id: str | None) -> None:
        """Record the Discord role id currently assigned as the Beyonder role."""
        self._execute(
            "UPDATE users SET beyond_role_id = ? WHERE user_id = ?", (role_id, user_id)
        )

    # --- corruption state -------------------------------------------------
    def set_corrupted(self, user_id: int, state: int, nickname_original: Optional[str] = None) -> None:
        self.ensure_user(user_id)
        self._execute(
            "UPDATE users SET corrupted_state = ?, nickname_original = COALESCE(?, nickname_original) "
            "WHERE user_id = ?",
            (state, nickname_original, user_id),
        )

    def clear_corrupted(self, user_id: int) -> None:
        self._execute(
            "UPDATE users SET corrupted_state = 0, nickname_original = NULL WHERE user_id = ?",
            (user_id,),
        )

    def set_fog_until(self, user_id: int, timestamp: float) -> None:
        self._execute("UPDATE users SET fog_until = ? WHERE user_id = ?", (timestamp, user_id))

    def clear_fog(self, user_id: int) -> None:
        self._execute("UPDATE users SET fog_until = 0 WHERE user_id = ?", (user_id,))

    # --- inventory --------------------------------------------------------
    def add_item(self, user_id: int, item_key: str, qty: int = 1) -> None:
        self.ensure_user(user_id)
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO inventory (user_id, item_key, qty) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, item_key) DO UPDATE SET qty = qty + excluded.qty",
                (user_id, item_key, qty),
            )

    def remove_item(self, user_id: int, item_key: str, qty: int = 1) -> bool:
        """Remove up to ``qty`` of an item; returns False if not enough present."""
        self.ensure_user(user_id)
        with self._lock, self._conn:
            cur = self._conn.execute(
                "SELECT qty FROM inventory WHERE user_id = ? AND item_key = ?",
                (user_id, item_key),
            ).fetchone()
            if cur is None or cur["qty"] < qty:
                return False
            if cur["qty"] == qty:
                self._conn.execute(
                    "DELETE FROM inventory WHERE user_id = ? AND item_key = ?",
                    (user_id, item_key),
                )
            else:
                self._conn.execute(
                    "UPDATE inventory SET qty = qty - ? WHERE user_id = ? AND item_key = ?",
                    (qty, user_id, item_key),
                )
            return True

    def get_inventory(self, user_id: int) -> Dict[str, int]:
        rows = self._fetchall("SELECT item_key, qty FROM inventory WHERE user_id = ?", (user_id,))
        return {r["item_key"]: r["qty"] for r in rows}

    def count_item(self, user_id: int, item_key: str) -> int:
        row = self._fetchone(
            "SELECT qty FROM inventory WHERE user_id = ? AND item_key = ?",
            (user_id, item_key),
        )
        return int(row["qty"]) if row else 0

    # --- artifacts --------------------------------------------------------
    def add_artifact(self, user_id: int, artifact_id: str, definition_key: Optional[str],
                     name: str, grade: int, effect: str, curse: str) -> None:
        self._execute(
            "INSERT INTO artifacts (artifact_id, owner_id, definition_key, name, grade, "
            "effect, curse, equipped, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
            (artifact_id, user_id, definition_key, name, grade, effect, curse,
             datetime.now(timezone.utc).isoformat()),
        )

    def get_artifact(self, artifact_id: str) -> Optional[Dict]:
        return self._fetchone("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,))

    def get_artifacts(self, user_id: int) -> List[Dict]:
        return self._fetchall("SELECT * FROM artifacts WHERE owner_id = ?", (user_id,))

    def get_equipped(self, user_id: int) -> Optional[Dict]:
        return self._fetchone(
            "SELECT * FROM artifacts WHERE owner_id = ? AND equipped = 1", (user_id,)
        )

    def equip_artifact(self, user_id: int, artifact_id: str) -> bool:
        art = self.get_artifact(artifact_id)
        if art is None or int(art["owner_id"]) != user_id:
            return False
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE artifacts SET equipped = 0 WHERE owner_id = ?", (user_id,)
            )
            self._conn.execute(
                "UPDATE artifacts SET equipped = 1 WHERE artifact_id = ?", (artifact_id,)
            )
            self._conn.execute(
                "UPDATE users SET equipped_artifact = ? WHERE user_id = ?",
                (artifact_id, user_id),
            )
        return True

    def unequip_artifact(self, user_id: int) -> Optional[str]:
        art = self.get_equipped(user_id)
        if art is None:
            return None
        self._execute(
            "UPDATE artifacts SET equipped = 0 WHERE artifact_id = ?", (art["artifact_id"],)
        )
        self._execute("UPDATE users SET equipped_artifact = NULL WHERE user_id = ?", (user_id,))
        return art["artifact_id"]

    def delete_artifact(self, artifact_id: str) -> bool:
        art = self.get_artifact(artifact_id)
        if art is None:
            return False
        self._execute("DELETE FROM artifacts WHERE artifact_id = ?", (artifact_id,))
        return True

    # --- oracle quotas ----------------------------------------------------
    def record_oracle_query(self, user_id: int) -> None:
        self._execute(
            "INSERT INTO oracle_queries (user_id, queried_at) VALUES (?, ?)",
            (user_id, self._now()),
        )

    def oracle_queries_since(self, user_id: int, seconds: int) -> int:
        cutoff = self._now() - seconds
        row = self._fetchone(
            "SELECT COUNT(*) AS n FROM oracle_queries WHERE user_id = ? AND queried_at > ?",
            (user_id, cutoff),
        )
        return int(row["n"]) if row else 0

    # --- gods / sequence 0 slots -----------------------------------------
    def set_god(self, pathway_key: str, user_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO gods (pathway, holder_id) VALUES (?, ?) "
                "ON CONFLICT(pathway) DO UPDATE SET holder_id = excluded.holder_id",
                (pathway_key, user_id),
            )

    def get_god(self, pathway_key: str) -> Optional[int]:
        row = self._fetchone("SELECT holder_id FROM gods WHERE pathway = ?", (pathway_key,))
        return int(row["holder_id"]) if row else None

    def all_gods(self) -> Dict[str, int]:
        rows = self._fetchall("SELECT pathway, holder_id FROM gods")
        return {r["pathway"]: r["holder_id"] for r in rows}

    def strip_god(self, pathway_key: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM gods WHERE pathway = ?", (pathway_key,))
            return cur.rowcount > 0

    # --- tarot aliases ----------------------------------------------------
    def set_tarot_alias(self, user_id: int, alias: str, card: str) -> None:
        self._execute(
            "INSERT INTO tarot_aliases (user_id, alias, card) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET alias = excluded.alias, card = excluded.card",
            (user_id, alias, card),
        )

    def get_tarot_alias(self, user_id: int) -> Optional[Dict]:
        return self._fetchone("SELECT * FROM tarot_aliases WHERE user_id = ?", (user_id,))

    def clear_tarot_alias(self, user_id: int) -> None:
        self._execute("DELETE FROM tarot_aliases WHERE user_id = ?", (user_id,))

    # --- anomalies --------------------------------------------------------
    def set_anomaly(self, channel_id: int, event_type: str, ends_at: float, data: Any) -> None:
        self._execute(
            "INSERT INTO anomalies (channel_id, event_type, ends_at, data) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(channel_id) DO UPDATE SET event_type = excluded.event_type, "
            "ends_at = excluded.ends_at, data = excluded.data",
            (channel_id, event_type, ends_at, json.dumps(data)),
        )

    def get_anomaly(self, channel_id: int) -> Optional[Dict]:
        row = self._fetchone("SELECT * FROM anomalies WHERE channel_id = ?", (channel_id,))
        if row is None:
            return None
        row = dict(row)
        row["data"] = json.loads(row["data"]) if row["data"] else {}
        return row

    def clear_anomaly(self, channel_id: int) -> None:
        self._execute("DELETE FROM anomalies WHERE channel_id = ?", (channel_id,))

    def all_anomalies(self) -> List[Dict]:
        rows = self._fetchall("SELECT * FROM anomalies")
        for r in rows:
            r["data"] = json.loads(r["data"]) if r["data"] else {}
        return rows

    # --- trials -----------------------------------------------------------
    def set_trial(self, user_id: int, target_sequence: int, trial_kind: str) -> None:
        self._execute(
            "INSERT INTO trials (user_id, target_sequence, trial_kind) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET target_sequence = excluded.target_sequence, "
            "trial_kind = excluded.trial_kind",
            (user_id, target_sequence, trial_kind),
        )

    def get_trial(self, user_id: int) -> Optional[Dict]:
        return self._fetchone("SELECT * FROM trials WHERE user_id = ?", (user_id,))

    def clear_trial(self, user_id: int) -> None:
        self._execute("DELETE FROM trials WHERE user_id = ?", (user_id,))

    # --- aggregate queries (madness engine / slot caps) -------------------
    def count_at_sequence(self, pathway_key: str, sequence: int) -> int:
        row = self._fetchone(
            "SELECT COUNT(*) AS n FROM users WHERE pathway = ? AND sequence = ?",
            (pathway_key, sequence),
        )
        return int(row["n"]) if row else 0

    def users_above_corruption(self, threshold: float) -> List[Dict]:
        return self._fetchall("SELECT * FROM users WHERE corruption >= ?", (threshold,))

    def corrupted_users(self) -> List[Dict]:
        return self._fetchall("SELECT * FROM users WHERE corrupted_state = 1")

    def equipped_artifacts_all(self) -> List[Dict]:
        return self._fetchall(
            "SELECT a.* FROM artifacts a WHERE a.equipped = 1"
        )

    # --- daily & leaderboard ---------------------------------------------
    def claim_daily(self, user_id: int) -> bool:
        """Attempt to claim a daily reward. Returns True if newly claimed."""
        user = self.ensure_user(user_id)
        today = self._today()
        if user.get("last_daily_date") == today:
            return False
        self._execute(
            "UPDATE users SET last_daily_date = ? WHERE user_id = ?", (today, user_id)
        )
        return True

    def leaderboard(self, limit: int = 10) -> List[Dict]:
        return self._fetchall(
            "SELECT user_id, pathway, sequence, digestion, active_days FROM users "
            "WHERE pathway IS NOT NULL AND sequence IS NOT NULL "
            "ORDER BY sequence ASC, digestion DESC, active_days DESC LIMIT ?",
            (limit,),
        )
