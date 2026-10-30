# The Fool's Attendant — Beginner Setup Guide (Windows)

This walks you through everything, assuming zero coding experience. Do the steps
in order. If something breaks, check **Troubleshooting** at the end.

---

## What you need

- A Windows PC.
- About 10–15 minutes.
- A Discord account with **Manage Server** permission.
- *(Optional)* a free Google Gemini API key (for `/ask-oracle`).

---

## Step 1 — Install Python

1. Open <https://www.python.org/downloads/> in your browser.
2. Click the big yellow **Download Python 3.12** button and run the installer.
3. **IMPORTANT:** on the very first installer screen, tick the box
   **"Add python.exe to PATH"** at the bottom.
4. Click **Install Now** and wait for it to finish.
5. Test it: press the **Windows key**, type `cmd`, press Enter. In the black
   window type:
   ```
   python --version
   ```
   You should see something like `Python 3.12.7`.

> If you instead see `'python' is not recognized`, reinstall and make sure the
> "Add python.exe to PATH" box is ticked.

---

## Step 2 — Locate the bot folder

The bot files are already on your PC here:

```
C:\Users\Ansh\Documents\deepseek-harness\default-workspace\fools-attendant
```

Open **File Explorer** (the yellow folder icon) and paste that path into the
address bar at the top, then press Enter. You should see files like `main.py`,
`requirements.txt`, and a `cogs` folder.

---

## Step 3 — Create your Discord bot

1. Go to <https://discord.com/developers/applications> and log in.
2. Click **New Application**, type a name (e.g. `Fool's Attendant`), click **Create**.
3. In the left menu click **Bot**.
4. Click **Reset Token** → **Copy**. This is your bot's password. **Never share it.**
   If you lose it, just reset it again later.
5. Still on the **Bot** page, scroll down to **Privileged Gateway Intents** and
   turn **ON** these two:
   - **Message Content Intent**
   - **Server Members Intent**
   Then click **Save Changes**.
6. In the left menu click **OAuth2** → **URL Generator**.
7. Under **Scopes**, tick **bot** and **applications.commands**.
8. Under **Bot Permissions**, tick:
   - Manage Messages
   - Manage Nicknames
   - Moderate Members
   - Manage Webhooks
   - Manage Channels
   - View Channels
   - Send Messages
   - Manage Roles
9. Copy the **Generated URL** near the bottom, open it in a new tab, choose your
   server, and click **Authorize**.

---

## Step 4 — Put your token in the config

1. In the `fools-attendant` folder, find the file **`.env.example`**.
2. Right-click it → **Copy**, then right-click empty space → **Paste**. You'll get
   `.env - Copy`.
3. Rename the copy to **`.env`** (exactly that, with a dot and no `.txt`).
   - Tip: in File Explorer, click **View → Show → File name extensions** so you
     can see the real file names. Rename so it ends in just `.env`.
4. Right-click **`.env`** → **Open with** → **Notepad**.
5. Find the line `DISCORD_TOKEN=` and paste your bot token right after the `=`,
   so it looks like:
   ```
   DISCORD_TOKEN=MTIzNDU2Nzg5...
   ```
6. Find `GEMINI_API_KEY=` and paste your Gemini key there (or leave it blank).
7. Press **Ctrl+S** to save, then close Notepad.

> Warning: if you name the file `.env.txt` it will be ignored. It must be `.env`.

---

## Step 5 — Install the bot's libraries (once)

1. Open the `fools-attendant` folder in File Explorer.
2. Click the address bar, type `powershell`, and press Enter. A blue terminal
   opens, already pointed at the folder.
3. Type this and press Enter:
   ```
   python -m pip install -r requirements.txt
   ```
4. Wait for it to download and install (it fetches discord.py). Warnings are
   fine; only red **errors** matter.

---

## Step 6 — Run the bot

1. In that same PowerShell window, type:
   ```
   python main.py
   ```
2. Wait a few seconds. You should see:
   ```
   [The Fool's Attendant] Logged in as Fool's Attendant#....
   [The Fool's Attendant] Synced N slash commands.
   ```
3. In Discord, type **`/help`** — the bot should reply.
4. To **stop** the bot, click the terminal and press **Ctrl+C**.

> The bot only runs while this window is open and your PC is on. Closing the
> window stops it.

### Easier way to start it next time

Double-click **`run.bat`** in the folder — it opens a terminal and starts the
bot for you. (Close the window to stop it.)

### Profile roles (pathway + sequence)

When a member chooses a Pathway or advances a Sequence, the bot gives them a
Discord role like **"Fool · Seer"** and updates it as they climb, so it shows on
their profile. This needs the **Manage Roles** permission (Step 3) — if you
didn't tick it, re-invite the bot with it. Toggle off via `/settings set
features_roles false`.

---

## Step 7 (optional) — Enable the AI Oracle

- Go to <https://aistudio.google.com/apikey>, click **Create API key**, copy it.
- Paste it into `.env` after `GEMINI_API_KEY=`.
- Without it, `/ask-oracle` still works from a built-in lore bank.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python and tick **Add to PATH**. Then open a **new** terminal. |
| Terminal says `can't open file 'main.py'` | You're in the wrong folder. In File Explorer, open the `fools-attendant` folder, then type `powershell` in its address bar. |
| Bot logs in, but `/help` shows nothing | In Discord press **Ctrl+R** to refresh. Commands can take ~1 minute to appear. Make sure you invited it with the **applications.commands** scope. |
| `DISCORD_TOKEN is not set` | The `.env` file is missing or misnamed (e.g. `.env.txt`), or the token line is empty. |
| `Improper token has been passed` | The token is wrong/expired. Reset it in the portal and paste the new one. |
| `Privileged intent ... not enabled` | Go back to the Bot page and turn on **Message Content** + **Server Members** intents. |
| Bot can't delete messages / change nicknames | Re-invite with the permissions listed in Step 3. |
| `pip` fails with a network error | Check internet, then retry. If you're behind a school/office network it may block downloads. |

---

## Step 8 (advanced) — Run on multiple PCs with failover

> Skip this until the bot works on **one** PC. It's advanced and optional.

**The rule:** Discord allows only **one** copy of a bot connected at a time. So
this feature is **active–passive**: one PC runs the bot, the others wait, and a
standby takes over automatically if the leader stops.

**You need a Firebase project** (free tier is enough for the lease):

1. Go to <https://console.firebase.google.com/> → **Add project** → give it a
   name → Continue.
2. Left menu → **Build → Firestore Database** → **Create database** → choose
   **Native mode** → pick a location → Create.
3. Project settings (gear icon) → **Service accounts** → **Generate new private
   key**. Save the `.json` file somewhere safe (e.g. inside the bot folder).
4. To store the database snapshot you need **Cloud Storage**:
   - Left menu → **Build → Storage → Get started**.
   - ⚠️ New Firebase projects require the **Blaze (pay‑as‑you‑go) plan** to use
     Cloud Storage — it needs a credit card, though usage for a small bot stays
     within the free tier. If you don't want to add billing, ask me to switch
     the snapshot storage to Firestore instead (free).

**On every PC:**

1. Install the extra library:
   ```
   pip install -r requirements-ha.txt
   ```
2. Edit `.env` and add:
   ```
   HA_ENABLED=true
   FIREBASE_CREDENTIALS=C:\path\to\service-account.json
   FIREBASE_BUCKET=your-project.appspot.com
   ```
3. Run `python main.py` on each PC.
   - One PC prints `[HA] Acquired leadership` and runs the bot.
   - The others print `[HA] Standby — waiting for leadership...`.

**How failover works:** the leader renews its lease every ~30 s and uploads a
database snapshot every 2 minutes. If the leader's PC shuts off, its lease
expires after ~90 s, and a standby downloads the latest snapshot and takes over.
Recent activity up to ~2 minutes old can be lost if a PC is force‑killed.

---

## Keeping it online 24/7

- Simplest: leave the PC on and keep `run.bat`'s window open (minimize it).
- To auto-restart on crash, use `run.bat` (it has a `pause`, so you can see
  errors). For true 24/7, a cheap cloud VM or a small always-on PC is more
  reliable than a home computer.
- Never commit or share your `.env` file — it contains your token.

---

## Run in background & start on boot

Three helper files do this:

| File | What it does |
|---|---|
| `start-bot.bat` | Runs the bot and restarts it 10 s after any crash. Logs to `bot.log`. |
| `start-hidden.vbs` | Launches `start-bot.bat` with **no visible window**. |
| `stop-bot.bat` | Stops the bot. |

**First make sure `python main.py` works** (Step 6). Only automate once it runs.

### Register it to start when you log in (Task Scheduler)

1. Press the **Windows key**, type `Task Scheduler`, open it.
2. On the right, click **Create Task…** (not "Create Basic Task").
3. **General** tab: Name = `FoolsAttendant`; choose **Run only when user is logged on**.
4. **Triggers** tab → **New…** → "Begin the task: **At log on**" → OK.
5. **Actions** tab → **New…** → Action "**Start a program**":
   - Program: `wscript.exe`
   - Add arguments:
     ```
     "C:\Users\Ansh\Documents\deepseek-harness\default-workspace\fools-attendant\start-hidden.vbs"
     ```
   - Start in:
     ```
     C:\Users\Ansh\Documents\deepseek-harness\default-workspace\fools-attendant
     ```
6. **Conditions** tab: untick "Start the task only if the computer is on AC power".
7. **Settings** tab: untick "Stop the task if it runs longer than"; tick
   "Allow task to be run on demand".
8. Click **OK**. Test it: right-click **FoolsAttendant** → **Run** — the bot goes
   online with no window.

> If you prefer the command line, run this in a normal PowerShell window (re-open
> as Administrator if it refuses):
> ```powershell
> $dir = "C:\Users\Ansh\Documents\deepseek-harness\default-workspace\fools-attendant"
> $action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument ('"' + $dir + '\start-hidden.vbs"') -WorkingDirectory $dir
> $trigger = New-ScheduledTaskTrigger -AtLogOn
> $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
> Register-ScheduledTask -TaskName "FoolsAttendant" -Action $action -Trigger $trigger -Settings $settings -Force
> ```

### Stopping it

Double-click **`stop-bot.bat`**. To remove auto-start entirely: Task Scheduler →
right-click **FoolsAttendant** → **Delete**.

### Logs

While it runs hidden, output goes to **`bot.log`** in the bot folder — open it in
Notepad when something seems wrong.

### Notes

- **At log on** starts the bot when you sign in. Starting *before* login requires
  running as SYSTEM, which usually can't find a per-user Python — so at-logon is
  the reliable choice.
- The loop restarts the bot after a crash (e.g. a temporary internet drop). Reboot
  your PC and sign in to verify it comes back on its own.
