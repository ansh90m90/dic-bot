"""SQLite snapshot sync to Firebase Cloud Storage for failover continuity."""
from __future__ import annotations

import os
import sqlite3
import time

import config


class SnapshotSync:
    def __init__(
        self, bucket_name: str, db_path: str, blob_name: str = "fools_attendant.db"
    ) -> None:
        self._bucket_name = bucket_name
        self._db_path = db_path
        self._blob_name = blob_name
        self._last_upload = 0.0

    def _blob(self):
        from firebase_admin import storage

        return storage.bucket(self._bucket_name).blob(self._blob_name)

    def _checkpoint(self) -> None:
        """Flush the WAL into the main DB file so the snapshot is complete."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
        except sqlite3.DatabaseError:
            pass

    def download_if_present(self) -> bool:
        """Replace the local DB with the latest cloud snapshot, if any."""
        blob = self._blob()
        if not blob.exists():
            return False
        for suffix in ("-wal", "-shm"):
            path = self._db_path + suffix
            if os.path.exists(path):
                os.remove(path)
        blob.download_to_filename(self._db_path)
        return True

    def upload(self) -> None:
        self._checkpoint()
        self._blob().upload_from_filename(self._db_path)
        self._last_upload = time.time()

    def maybe_upload(self) -> None:
        if time.time() - self._last_upload >= config.HA_SYNC_SECONDS:
            try:
                self.upload()
            except Exception as exc:  # network / permission errors
                print(f"[HA] snapshot upload failed: {exc!r}")
