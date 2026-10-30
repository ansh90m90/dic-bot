import sqlite3
import tempfile

from db.database import Database
from settings import SCHEMA, settings

assert "features_roles" in SCHEMA
assert settings.get("features_roles") is True

# Fresh DB has the column and set_beyond_role works.
db = Database(tempfile.mktemp(suffix=".db"))
cols = [r[1] for r in db._conn.execute("PRAGMA table_info(users)")]
assert "beyond_role_id" in cols, cols
db.ensure_user(1)
db.set_beyond_role(1, "123456789")
assert db.get_user(1)["beyond_role_id"] == "123456789"
db.close()
print("fresh DB OK")

# An existing DB (pre-beyond_role_id) is migrated.
old = tempfile.mktemp(suffix=".db")
c = sqlite3.connect(old)
c.execute(
    "CREATE TABLE users (user_id INTEGER PRIMARY KEY, pathway TEXT, sequence INTEGER, "
    "digestion REAL DEFAULT 0, sanity REAL DEFAULT 100, corruption REAL DEFAULT 0, "
    "gold INTEGER DEFAULT 100, tarot_coins INTEGER DEFAULT 0, joined_at TEXT, "
    "last_activity_date TEXT, active_days INTEGER DEFAULT 0, last_digest_ts REAL DEFAULT 0, "
    "corrupted_state INTEGER DEFAULT 0, nickname_original TEXT, fog_until REAL DEFAULT 0, "
    "last_daily_date TEXT, equipped_artifact TEXT)"
)
c.commit()
c.close()
db2 = Database(old)
cols2 = [r[1] for r in db2._conn.execute("PRAGMA table_info(users)")]
assert "beyond_role_id" in cols2, cols2
db2.close()
print("old DB migration OK")

print("ALL PASS")
