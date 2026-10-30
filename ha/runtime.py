"""Active–passive failover runtime.

Only one process may hold Discord's gateway connection, so instances compete for
a Firestore lease. The holder downloads the latest SQLite snapshot, runs the
bot, heartbeats the lease, uploads snapshots periodically, and releases on a
clean shutdown. Standbys poll until the lease frees up.
"""
from __future__ import annotations

import asyncio
import sys

import config


async def run_ha(bot_factory) -> None:
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        print(
            "HA_ENABLED is set but `firebase-admin` is not installed.\n"
            "Run: pip install -r requirements-ha.txt",
            file=sys.stderr,
        )
        return

    from ha.lease import LeaderLease
    from ha.snapshot import SnapshotSync

    if not config.FIREBASE_CREDENTIALS or not config.FIREBASE_BUCKET:
        print(
            "HA requires FIREBASE_CREDENTIALS (service-account JSON path) and "
            "FIREBASE_BUCKET.",
            file=sys.stderr,
        )
        return

    cred = credentials.Certificate(config.FIREBASE_CREDENTIALS)
    try:
        firebase_admin.initialize_app(cred, {"storageBucket": config.FIREBASE_BUCKET})
    except ValueError:
        pass  # already initialised

    client = firestore.client()
    lease = LeaderLease(client, "fools_attendant/leader", config.HA_LEASE_SECONDS)
    snapshot = SnapshotSync(config.FIREBASE_BUCKET, config.DATABASE_PATH)

    while True:
        if await asyncio.to_thread(lease.acquire):
            break
        print("[HA] Standby — waiting for leadership...")
        await asyncio.sleep(config.HA_POLL_SECONDS)

    print(f"[HA] Acquired leadership as {lease.owner}.")
    if await asyncio.to_thread(snapshot.download_if_present):
        print("[HA] Downloaded latest snapshot from Firebase.")

    bot = bot_factory()
    stop = asyncio.Event()

    async def heartbeat() -> None:
        while not stop.is_set():
            await asyncio.sleep(config.HA_LEASE_SECONDS / 3)
            if stop.is_set():
                return
            ok = await asyncio.to_thread(lease.renew)
            if not ok:
                print("[HA] Lease lost — shutting this instance down.")
                stop.set()
                try:
                    await bot.close()
                except Exception:
                    pass
                return
            await asyncio.to_thread(snapshot.maybe_upload)

    task = asyncio.create_task(heartbeat())
    try:
        await bot.start(config.DISCORD_TOKEN)
    except Exception as exc:
        print(f"[HA] Bot stopped: {exc!r}")
    finally:
        stop.set()
        task.cancel()
        try:
            await asyncio.to_thread(snapshot.upload)
        except Exception as exc:
            print(f"[HA] final snapshot failed: {exc!r}")
        await asyncio.to_thread(lease.release)
        try:
            await bot.close()
        except Exception:
            pass
