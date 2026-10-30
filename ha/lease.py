"""Firestore-based leader lease for active–passive failover.

A single document holds the current leader's identity and an expiry timestamp.
Only the lease holder should connect to Discord. Standbys poll :meth:`acquire`
until the lease expires; the holder renews it periodically and releases it on a
clean shutdown.
"""
from __future__ import annotations

import socket
import time
import uuid


class LeaderLease:
    def __init__(self, client, doc_path: str, ttl_seconds: int) -> None:
        self._client = client
        self._ref = client.document(doc_path)
        self._ttl = ttl_seconds
        self.owner = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

    def acquire(self) -> bool:
        """Atomically take the lease if it is free or expired."""
        from google.cloud import firestore

        now = time.time()

        @firestore.transactional
        def _txn(transaction):
            snap = self._ref.get(transaction=transaction)
            data = snap.to_dict() if snap.exists else None
            if not data or float(data.get("expires_at", 0)) < now:
                transaction.set(
                    self._ref, {"owner": self.owner, "expires_at": now + self._ttl}
                )
                return True
            return False

        return _txn(self._client.transaction())

    def renew(self) -> bool:
        """Extend the lease if we still own it."""
        from google.cloud import firestore

        now = time.time()

        @firestore.transactional
        def _txn(transaction):
            snap = self._ref.get(transaction=transaction)
            data = snap.to_dict() if snap.exists else None
            if data and data.get("owner") == self.owner:
                transaction.update(self._ref, {"expires_at": now + self._ttl})
                return True
            return False

        return _txn(self._client.transaction())

    def release(self) -> None:
        """Drop the lease (only if we still own it)."""
        try:
            snap = self._ref.get()
            if snap.exists and (snap.to_dict() or {}).get("owner") == self.owner:
                self._ref.delete()
        except Exception:
            pass
