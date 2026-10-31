"""The Fool's Attendant — Web Sanctum & Discord Bot Process Manager.

Pure Python standard-library implementation with ZERO external package requirements
(no pip, gradio, or aiohttp needed for the web server).
Binds to host 0.0.0.0 and port 3000 (or PORT env var) to serve the AI Studio preview
and cloud hosts while managing the Discord bot worker process in the background.
"""
from __future__ import annotations

import collections
import html
import http.server
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse

# Global state & log buffer
LOG_BUFFER: collections.deque[str] = collections.deque(maxlen=200)
WORKER_PROCESS: subprocess.Popen | None = None
WORKER_LOCK = threading.Lock()
START_TIME = time.time()


def log_message(msg: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    LOG_BUFFER.append(formatted)


def run_bot_worker() -> None:
    """Run main.py as a subprocess, streaming its stdout/stderr to LOG_BUFFER."""
    global WORKER_PROCESS
    python_bin = sys.executable or "python3"
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    token_set = bool(os.environ.get("DISCORD_TOKEN"))
    if not token_set:
        log_message("⚠️ DISCORD_TOKEN is not set in environment. Bot worker will wait for token configuration.")
        return

    log_message("⚡ Launching Discord bot worker (main.py)...")
    try:
        with WORKER_LOCK:
            WORKER_PROCESS = subprocess.Popen(
                [python_bin, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )

        if WORKER_PROCESS and WORKER_PROCESS.stdout:
            for line in iter(WORKER_PROCESS.stdout.readline, ""):
                clean = line.rstrip()
                if clean:
                    log_message(clean)

        WORKER_PROCESS.wait()
        log_message(f"🛑 Discord bot worker exited with return code {WORKER_PROCESS.returncode}.")
    except Exception as exc:
        log_message(f"❌ Failed to run bot worker: {exc}")


def start_worker_thread() -> None:
    thread = threading.Thread(target=run_bot_worker, daemon=True)
    thread.start()


def get_sanctum_stats() -> dict:
    """Read summary statistics from fools_attendant.db safely."""
    stats = {
        "beyonders_count": 0,
        "gods_count": 0,
        "trials_count": 0,
        "angel_titles": [],
        "db_connected": False,
    }
    db_path = "fools_attendant.db"
    if not os.path.exists(db_path):
        return stats

    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT count(*) as cnt FROM users WHERE pathway IS NOT NULL;")
        row = cur.fetchone()
        stats["beyonders_count"] = row["cnt"] if row else 0

        cur.execute("SELECT count(*) as cnt FROM gods;")
        row = cur.fetchone()
        stats["gods_count"] = row["cnt"] if row else 0

        cur.execute("SELECT count(*) as cnt FROM trials;")
        row = cur.fetchone()
        stats["trials_count"] = row["cnt"] if row else 0

        try:
            cur.execute("SELECT user_id, title FROM angel_titles LIMIT 10;")
            stats["angel_titles"] = [
                {"user_id": str(r["user_id"]), "title": r["title"]} for r in cur.fetchall()
            ]
        except Exception:
            pass

        try:
            cur.execute("SELECT user_id, username FROM divine_permissions;")
            stats["divine_permissions"] = [
                {"user_id": str(r["user_id"]), "username": r["username"] or "Unknown"}
                for r in cur.fetchall()
            ]
        except Exception:
            stats["divine_permissions"] = []

        conn.close()
        stats["db_connected"] = True
    except Exception as exc:
        stats["error"] = str(exc)

    return stats


def generate_html_page() -> str:
    """Render the Lord of the Mysteries themed Web Sanctum console."""
    token_set = bool(os.environ.get("DISCORD_TOKEN"))
    gemini_set = bool(os.environ.get("GEMINI_API_KEY"))
    stats = get_sanctum_stats()
    uptime_sec = int(time.time() - START_TIME)
    uptime_str = f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m {uptime_sec % 60}s"

    worker_status = "Inactive"
    worker_class = "status-warn"
    if WORKER_PROCESS:
        if WORKER_PROCESS.poll() is None:
            worker_status = "Online & Running"
            worker_class = "status-ok"
        else:
            worker_status = f"Stopped (Code {WORKER_PROCESS.returncode})"
            worker_class = "status-err"
    elif token_set:
        worker_status = "Starting..."
        worker_class = "status-warn"

    token_badge = '<span class="badge badge-ok">Configured</span>' if token_set else '<span class="badge badge-warn">Missing</span>'
    gemini_badge = '<span class="badge badge-ok">Configured</span>' if gemini_set else '<span class="badge badge-neutral">Built-in Fallback</span>'

    angel_items = "".join(
        f'<div class="angel-badge">🪽 <strong>Archangel · {html.escape(a["title"])}</strong> (ID: {html.escape(a["user_id"])})</div>'
        for a in stats.get("angel_titles", [])
    ) or '<div class="empty-state">No Angel Titles claimed yet. Use <code>/angel title-set</code> in Discord.</div>'

    divine_perm_items = "".join(
        f'<div class="angel-badge">✨ <strong>{html.escape(d["username"])}</strong> (ID: {html.escape(d["user_id"])})</div>'
        for d in stats.get("divine_permissions", [])
    ) or '<div class="empty-state">No dynamic permissions granted yet. Use <code>/divine-permission add</code> in Discord.</div>'

    logs_text = "\n".join(html.escape(line) for line in list(LOG_BUFFER)[-50:]) or "Waiting for bot activity..."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Fool's Attendant — Divine Sanctum</title>
  <style>
    :root {{
      --bg: #0e1015;
      --card-bg: #16181f;
      --card-border: #252836;
      --text-main: #e2e8f0;
      --text-muted: #94a3b8;
      --gold: #f0b229;
      --gold-glow: rgba(240, 178, 41, 0.2);
      --purple: #8b5cf6;
      --purple-glow: rgba(139, 92, 246, 0.2);
      --green: #10b981;
      --red: #ef4444;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      padding: 24px;
    }}
    .container {{
      max-width: 1040px;
      margin: 0 auto;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 20px;
      margin-bottom: 24px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .brand-icon {{
      font-size: 36px;
      filter: drop-shadow(0 0 12px var(--gold-glow));
    }}
    .brand h1 {{
      font-size: 24px;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.5px;
    }}
    .brand p {{
      font-size: 13px;
      color: var(--text-muted);
    }}
    .server-uptime {{
      font-family: var(--font-mono);
      font-size: 12px;
      background: #1e2230;
      padding: 6px 12px;
      border-radius: 6px;
      border: 1px solid var(--card-border);
      color: var(--gold);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      position: relative;
      overflow: hidden;
    }}
    .card h3 {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      margin-bottom: 8px;
    }}
    .stat-val {{
      font-size: 26px;
      font-weight: 700;
      color: #fff;
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      margin-top: 6px;
    }}
    .status-ok {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .status-warn {{ background: rgba(240, 178, 41, 0.15); color: #fbbf24; border: 1px solid rgba(240, 178, 41, 0.3); }}
    .status-err {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
    
    .badge {{
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 4px;
    }}
    .badge-ok {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
    .badge-warn {{ background: rgba(240, 178, 41, 0.2); color: #fbbf24; }}
    .badge-neutral {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; }}

    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 24px;
    }}
    @media (max-width: 768px) {{
      .two-col {{ grid-template-columns: 1fr; }}
    }}
    .section-title {{
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .angel-list {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .angel-badge {{
      background: #1b1e2a;
      border: 1px solid rgba(240, 178, 41, 0.3);
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 13px;
      color: #fff;
    }}
    .angel-badge strong {{
      color: var(--gold);
    }}
    .empty-state {{
      font-size: 13px;
      color: var(--text-muted);
      font-style: italic;
      padding: 12px;
      background: #1a1d26;
      border-radius: 6px;
    }}

    .console-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}
    .btn {{
      background: #252a38;
      color: #fff;
      border: 1px solid var(--card-border);
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 500;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .btn:hover {{
      background: #32384a;
      border-color: #434c62;
    }}
    .btn-gold {{
      background: var(--gold);
      color: #000;
      font-weight: 600;
      border: none;
    }}
    .btn-gold:hover {{
      background: #e5a720;
    }}

    .console-box {{
      background: #090a0d;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px;
      font-family: var(--font-mono);
      font-size: 12px;
      color: #94a3b8;
      height: 280px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }}
    .quick-guide {{
      background: #141721;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      font-size: 13px;
    }}
    .quick-guide ul {{
      margin-left: 18px;
      margin-top: 8px;
    }}
    .quick-guide li {{
      margin-bottom: 6px;
    }}
    code {{
      background: #202433;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 12px;
      color: #f1f5f9;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-icon">👁️</div>
        <div>
          <h1>The Fool's Attendant</h1>
          <p>Lord of the Mysteries · Discord Mystical Progression & Archangel Council</p>
        </div>
      </div>
      <div class="server-uptime">Uptime: {uptime_str}</div>
    </header>

    <div class="grid">
      <div class="card">
        <h3>Discord Gateway Status</h3>
        <div class="status-pill {worker_class}">● {worker_status}</div>
      </div>
      <div class="card">
        <h3>Registered Beyonders</h3>
        <div class="stat-val">{stats['beyonders_count']}</div>
      </div>
      <div class="card">
        <h3>True Gods (Seq 0)</h3>
        <div class="stat-val">{stats['gods_count']}</div>
      </div>
      <div class="card">
        <h3>Pending Trials</h3>
        <div class="stat-val">{stats['trials_count']}</div>
      </div>
    </div>

    <div class="two-col">
      <div class="card">
        <div class="section-title">🪽 Archangel Council of Divine Titles</div>
        <div class="angel-list">
          {angel_items}
        </div>
        <div style="margin-top: 14px; font-size: 12px; color: var(--text-muted);">
          Bestow titles via <code>/angel title-set &lt;title&gt; [member]</code> or auto-provision all 22 pathways via <code>/angel setup-roles</code>.
        </div>
      </div>

      <div class="card">
        <div class="section-title">🔮 Environment Credentials</div>
        <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
          <tr style="border-bottom: 1px solid #252836; height: 36px;">
            <td style="color: var(--text-muted);">DISCORD_TOKEN</td>
            <td style="text-align: right;">{token_badge}</td>
          </tr>
          <tr style="border-bottom: 1px solid #252836; height: 36px;">
            <td style="color: var(--text-muted);">GEMINI_API_KEY</td>
            <td style="text-align: right;">{gemini_badge}</td>
          </tr>
          <tr style="border-bottom: 1px solid #252836; height: 36px;">
            <td style="color: var(--text-muted);">SQLite Database</td>
            <td style="text-align: right;"><span class="badge badge-ok">fools_attendant.db</span></td>
          </tr>
          <tr style="height: 36px;">
            <td style="color: var(--text-muted);">Role Management</td>
            <td style="text-align: right;"><span class="badge badge-ok">Dual-Role & Hoisting</span></td>
          </tr>
        </table>

        <div style="margin-top: 16px;">
          <form method="POST" action="/api/restart" style="display: inline;">
            <button type="submit" class="btn btn-gold">🔄 Restart Bot Worker</button>
          </form>
          <button onclick="window.location.reload();" class="btn" style="margin-left: 8px;">Refresh UI</button>
        </div>
      </div>
    </div>

    <div class="card" style="margin-bottom: 24px; border-color: rgba(240, 178, 41, 0.35);">
      <div class="section-title" style="color: var(--gold);">👑 Above the Sequences — Supreme Divine Authority</div>
      <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">
        Entities holding supreme authority can execute all commands (Creator, Archangel, Moderator, Beyonder) regardless of Sequence rank (even at Sequence 9).
      </p>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <div>
          <div style="font-size: 12px; font-weight: 600; color: var(--gold); margin-bottom: 6px;">Permanent Master Creators:</div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <div class="angel-badge">👑 <strong>core.inbox1999</strong></div>
            <div class="angel-badge">👑 <strong>mr.fool_here</strong></div>
          </div>
        </div>
        <div>
          <div style="font-size: 12px; font-weight: 600; color: #a78bfa; margin-bottom: 6px;">Dynamic Divine Permissions:</div>
          <div class="angel-list">
            {divine_perm_items}
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="console-header">
        <div class="section-title" style="margin-bottom: 0;">📜 Divine Sanctum Log Stream</div>
        <div>
          <button class="btn" onclick="fetchLogs()">Fetch Latest Logs</button>
        </div>
      </div>
      <div class="console-box" id="log-box">{logs_text}</div>
    </div>

    <div class="quick-guide" style="margin-top: 20px;">
      <strong>🌟 Quick Discord Commands Reference:</strong>
      <ul>
        <li><code>/divine-permission add &lt;user&gt;</code> — Bestow supreme Above-the-Sequences Divine Permission on any user to authorize all commands.</li>
        <li><code>/divine-permission list</code> — Display all active Divine Permission holders and permanent Master Creators.</li>
        <li><code>/divine-permission remove &lt;user&gt;</code> — Revoke a user's Above-the-Sequences Divine Permission.</li>
        <li><code>/angel setup-roles</code> — Automatically create and configure all 22 Pathway roles and the Archangel Council role in one click.</li>
        <li><code>/angel title-set &lt;title&gt; [member]</code> — Bestow unique hoisted Archangel Titles (e.g. Angel of Time, Angel of Retribution).</li>
        <li><code>/angel console</code> — Interactive management dashboard inside Discord (Beyonder roster, trials review, one-click treasury).</li>
        <li><code>/profile</code> &amp; <code>/status</code> — Inspect 880×500 Discord Dark Occult visual status slate.</li>
      </ul>
    </div>
  </div>

  <script>
    function fetchLogs() {{
      fetch('/api/logs')
        .then(res => res.json())
        .then(data => {{
          const box = document.getElementById('log-box');
          box.textContent = data.logs.join('\\n');
          box.scrollTop = box.scrollHeight;
        }})
        .catch(err => console.error(err));
    }}
    setInterval(fetchLogs, 5000);
  </script>
</body>
</html>
"""


class SanctumHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        # Suppress noisy standard HTTP request logging in terminal
        pass

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            content = generate_html_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        elif parsed.path == "/api/status":
            stats = get_sanctum_stats()
            stats["token_set"] = bool(os.environ.get("DISCORD_TOKEN"))
            stats["gemini_set"] = bool(os.environ.get("GEMINI_API_KEY"))
            stats["worker_running"] = WORKER_PROCESS is not None and WORKER_PROCESS.poll() is None
            body = json.dumps(stats).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        elif parsed.path == "/api/logs":
            body = json.dumps({"logs": list(LOG_BUFFER)}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/restart":
            global WORKER_PROCESS
            log_message("🔄 Received restart request from Web UI...")
            with WORKER_LOCK:
                if WORKER_PROCESS and WORKER_PROCESS.poll() is None:
                    try:
                        WORKER_PROCESS.terminate()
                        WORKER_PROCESS.wait(timeout=3)
                    except Exception:
                        try:
                            WORKER_PROCESS.kill()
                        except Exception:
                            pass
                WORKER_PROCESS = None

            start_worker_thread()

            # Redirect back to home
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()


def run_server() -> None:
    port = int(os.environ.get("PORT", 3000))
    host = "0.0.0.0"

    log_message(f"🏛️ Starting The Fool's Attendant Web Sanctum on http://{host}:{port}...")
    start_worker_thread()

    server = http.server.ThreadingHTTPServer((host, port), SanctumHTTPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
