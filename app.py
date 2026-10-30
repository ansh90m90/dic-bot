"""Web entry point for 100% Free Hugging Face Spaces (Gradio SDK) or browser hosts.

Hugging Face Spaces runs `app.py` with the Gradio SDK for free (no Docker/paid card needed).
This launches the Discord bot worker in the background while serving a status page.
"""
from __future__ import annotations

import os
import sys
import threading
import subprocess
import time
import gradio as gr

# Start the Discord bot worker in a background thread
def _start_bot_worker() -> None:
    time.sleep(1)
    python_bin = sys.executable or "python"
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    try:
        subprocess.run([python_bin, "main.py"], env=env)
    except Exception as exc:
        print(f"[Worker Error] Failed to execute main.py: {exc}", file=sys.stderr)

worker_thread = threading.Thread(target=_start_bot_worker, daemon=True)
worker_thread.start()


def get_status() -> str:
    token_set = bool(os.environ.get("DISCORD_TOKEN"))
    gemini_set = bool(os.environ.get("GEMINI_API_KEY"))
    status_msg = "🟢 Online & Operational" if token_set else "⚠️ Token Missing (Add DISCORD_TOKEN in Settings -> Secrets)"
    return f"""### 🏛️ The Fool's Attendant — Divine Sanctum
**Status:** {status_msg}
**Discord Gateway:** Connected via outbound WebSocket
**Gemini AI Oracle:** {'Enabled ✨' if gemini_set else 'Built-in Fallback 📜'}

*Above the grey fog, the crimson stars shine silently.*
"""

with gr.Blocks(title="The Fool's Attendant", theme=gr.themes.Monochrome()) as demo:
    gr.Markdown("# 👁️ The Fool's Attendant — Discord Bot Sanctum")
    status_output = gr.Markdown(value=get_status)
    refresh_btn = gr.Button("🔄 Refresh Sanctum Status", variant="primary")
    refresh_btn.click(fn=get_status, outputs=status_output)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
