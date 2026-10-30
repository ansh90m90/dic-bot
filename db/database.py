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
                    last_active_ts REAL NOT NULL DEFAULT 0,
                    last_decay_check_ts REAL NOT NULL DEFAULT 0,
                    last_demotion_ts REAL NOT NULL DEFAULT 0,
                    vc_minutes INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    qty INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (user_id, item_key)
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

        # Drop artifacts table and legacy indexes if they exist
        with self._lock, self._conn:
            self._conn.execute("DROP TABLE IF EXISTS artifacts")
            self._conn.execute("DROP INDEX IF EXISTS idx_artifacts_equipped")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_users_corruption ON users(corruption)")

        # Migration: drop equipped_artifact column if it exists
        try:
            with self._lock, self._conn:
                self._conn.execute("ALTER TABLE users DROP COLUMN equipped_artifact")
        except sqlite3.OperationalError:
            pass

        # Migrations for new columns on older database files
        migrations = (
            "ALTER TABLE users ADD COLUMN last_daily_date TEXT",
            "ALTER TABLE users ADD COLUMN beyond_role_id TEXT",
            "ALTER TABLE users ADD COLUMN last_active_ts REAL NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_decay_check_ts REAL NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_demotion_ts REAL NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN vc_minutes INTEGER NOT NULL DEFAULT 0",
        )
        for stmt in migrations:
            try:
                with self._lock, self._conn:
                    self._conn.execute(stmt)
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
            now = self._now()
            self._execute(
                "INSERT INTO users (user_id, gold, last_active_ts, last_decay_check_ts) "
                "VALUES (?, ?, ?, ?)",
                (user_id, int(settings.get("starting_gold", config.STARTING_GOLD)), now, now),
            )
            user = self.get_user(user_id)
        return user  # type: ignore[return-value]

    def get_user(self, user_id: int) -> Optional[Dict]:
        return self._fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))

    def register_pathway(self, user_id: int, pathway_key: str) -> None:
        self.ensure_user(user_id)
        now = self._now()
        self._execute(
            "UPDATE users SET pathway = ?, sequence = 9, digestion = 0, joined_at = ?, "
            "last_active_ts = ? WHERE user_id = ?",
            (pathway_key, datetime.now(timezone.utc).isoformat(), now, user_id),
        )

    def set_sequence(self, user_id: int, pathway_key: str, sequence: int) -> None:
        self._execute(
            "UPDATE users SET pathway = ?, sequence = ?, digestion = 0, last_active_ts = ? "
            "WHERE user_id = ?",
            (pathway_key, sequence, self._now(), user_id),
        )

    def add_digestion(self, user_id: int, amount: float) -> float:
        """Add digestion, cap at 100, return the new value."""
        user = self.ensure_user(user_id)
        new_val = min(100.0, float(user["digestion"]) + amount)
        self._execute(
            "UPDATE users SET digestion = ?, last_active_ts = ? WHERE user_id = ?",
            (new_val, self._now(), user_id),
        )
        return new_val

    def set_digestion(self, user_id: int, amount: float) -> float:
        new_val = min(100.0, max(0.0, amount))
        self._execute(
            "UPDATE users SET digestion = ?, last_active_ts = ? WHERE user_id = ?",
            (new_val, self._now(), user_id),
        )
        return new_val

    def add_gold(self, user_id: int, amount: int) -> int:
        user = self.ensure_user(user_id)
        new_val = max(0, int(user["gold"]) + amount)
        self._execute(
            "UPDATE users SET gold = ?, last_active_ts = ? WHERE user_id = ?",
            (new_val, self._now(), user_id),
        )
        return new_val

    def add_tarot(self, user_id: int, amount: int) -> int:
        user = self.ensure_user(user_id)
        new_val = max(0, int(user["tarot_coins"]) + amount)
        self._execute(
            "UPDATE users SET tarot_coins = ?, last_active_ts = ? WHERE user_id = ?",
            (new_val, self._now(), user_id),
        )
        return new_val

    def add_corruption(self, user_id: int, amount: float) -> float:
        user = self.ensure_user(user_id)
        new_val = min(100.0, max(0.0, float(user["corruption"]) + amount))
        self._execute(
            "UPDATE users SET corruption = ?, last_active_ts = ? WHERE user_id = ?",
            (new_val, self._now(), user_id),
        )
        return new_val

    def set_corruption(self, user_id: int, amount: float) -> float:
        new_val = min(100.0, max(0.0, amount))
        self._execute(
            "UPDATE users SET corruption = ?, last_active_ts = ? WHERE user_id = ?",
            (new_val, self._now(), user_id),
        )
        return new_val

    def add_sanity(self, user_id: int, amount: float) -> float:
        user = self.ensure_user(user_id)
        new_val = min(100.0, max(0.0, float(user["sanity"]) + amount))
        self._execute(
            "UPDATE users SET sanity = ?, last_active_ts = ? WHERE user_id = ?",
            (new_val, self._now(), user_id),
        )
        return new_val

    def set_sanity(self, user_id: int, amount: float) -> float:
        new_val = min(100.0, max(0.0, amount))
        self._execute(
            "UPDATE users SET sanity = ?, last_active_ts = ? WHERE user_id = ?",
            (new_val, self._now(), user_id),
        )
        return new_val

    def touch_activity(self, user_id: int) -> int:
        """Record activity; increment active_days once per UTC day. Returns days."""
        user = self.ensure_user(user_id)
        today = self._today()
        now = self._now()
        if user["last_activity_date"] != today:
            days = int(user["active_days"]) + 1
            self._execute(
                "UPDATE users SET last_activity_date = ?, active_days = ?, last_active_ts = ? "
                "WHERE user_id = ?",
                (today, days, now, user_id),
            )
            return days
        self._execute("UPDATE users SET last_active_ts = ? WHERE user_id = ?", (now, user_id))
        return int(user["active_days"])

    def touch_active(self, user_id: int) -> None:
        """Update last_active_ts timestamp without ticking active_days."""
        self.ensure_user(user_id)
        self._execute("UPDATE users SET last_active_ts = ? WHERE user_id = ?", (self._now(), user_id))

    def add_vc_minutes(self, user_id: int, minutes: int = 1) -> int:
        """Increment voice channel presence minutes and refresh last_active_ts."""
        user = self.ensure_user(user_id)
        new_mins = int(user.get("vc_minutes") or 0) + minutes
        now = self._now()
        self._execute(
            "UPDATE users SET vc_minutes = ?, last_active_ts = ? WHERE user_id = ?",
            (new_mins, now, user_id),
        )
        return new_mins

    def can_digest_from_message(self, user_id: int, cooldown: int | None = None) -> bool:
        """True if the activity cooldown has elapsed for digestion."""
        user = self.ensure_user(user_id)
        if cooldown is None:
            cooldown = int(
                settings.get("activity_digest_cooldown", config.ACTIVITY_DIGEST_COOLDOWN)
            )
        return self._now() - float(user["last_digest_ts"]) >= cooldown

    def mark_digest(self, user_id: int) -> None:
        now = self._now()
        self._execute(
            "UPDATE users SET last_digest_ts = ?, last_active_ts = ? WHERE user_id = ?",
            (now, now, user_id),
        )

    def activity_tick(self, user_id: int, digestion: float, last_digest_ts: float,
                      active_days: int, last_activity_date: str) -> None:
        """Apply one atomic activity tick (digestion + cooldown + active-days + active_ts)."""
        now = self._now()
        self._execute(
            "UPDATE users SET digestion = ?, last_digest_ts = ?, active_days = ?, "
            "last_activity_date = ?, last_active_ts = ? WHERE user_id = ?",
            (digestion, last_digest_ts, active_days, last_activity_date, now, user_id),
        )

    def set_beyond_role(self, user_id: int, role_id: str | None) -> None:
        """Record the Discord role id currently assigned as the Beyonder role."""
        self._execute(
            "UPDATE users SET beyond_role_id = ? WHERE user_id = ?", (role_id, user_id)
        )

    def update_decay_check(self, user_id: int, ts: float | None = None) -> None:
        check_ts = self._now() if ts is None else ts
        self._execute(
            "UPDATE users SET last_decay_check_ts = ? WHERE user_id = ?",
            (check_ts, user_id),
        )

    def demote_user_sequence(self, user_id: int) -> tuple[int, int] | None:
        """Demote user by 1 sequence (capped at 9). Reset digestion, clear God slot & trials.

        Returns (old_sequence, new_sequence) or None.
        """
        user = self.get_user(user_id)
        if not user or user["pathway"] is None or user["sequence"] is None:
            return None
        old_seq = int(user["sequence"])
        if old_seq >= 9:
            # Already at Sequence 9, just reset digestion
            self._execute(
                "UPDATE users SET digestion = 0, last_demotion_ts = ? WHERE user_id = ?",
                (self._now(), user_id),
            )
            return (old_seq, 9)
        new_seq = old_seq + 1
        pathway = user["pathway"]
        now = self._now()
        if old_seq == 0:
            self.strip_god(pathway)
        self.clear_trial(user_id)
        self._execute(
            "UPDATE users SET sequence = ?, digestion = 0, last_demotion_ts = ? WHERE user_id = ?",
            (new_seq, now, user_id),
        )
        return (old_seq, new_seq)

    # --- corruption state -------------------------------------------------
    def set_corrupted(self, user_id: int, state: int, nickname_original: Optional[str] = None) -> None:
        self.ensure_user(user_id)
        self._execute(
            "UPDATE users SET corrupted_state = ?, nickname_original = COALESCE(?, nickname_original), "
            "last_active_ts = ? WHERE user_id = ?",
            (state, nickname_original, self._now(), user_id),
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

    def all_trials(self) -> List[Dict]:
        return self._fetchall("SELECT * FROM trials")

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

    def all_beyonders(self) -> List[Dict]:
        """Return all users who have sworn fealty to a pathway."""
        return self._fetchall(
            "SELECT * FROM users WHERE pathway IS NOT NULL AND sequence IS NOT NULL"
        )

    # --- daily & leaderboard ---------------------------------------------
    def claim_daily(self, user_id: int) -> bool:
        """Attempt to claim a daily reward. Returns True if newly claimed."""
        user = self.ensure_user(user_id)
        today = self._today()
        if user.get("last_daily_date") == today:
            return False
        self._execute(
            "UPDATE users SET last_daily_date = ?, last_active_ts = ? WHERE user_id = ?",
            (today, self._now(), user_id),
        )
        return True

    def leaderboard(self, limit: int = 10) -> List[Dict]:
        return self._fetchall(
            "SELECT user_id, pathway, sequence, digestion, active_days, vc_minutes FROM users "
            "WHERE pathway IS NOT NULL AND sequence IS NOT NULL "
            "ORDER BY sequence ASC, digestion DESC, active_days DESC LIMIT ?",
            (limit,),
        )
