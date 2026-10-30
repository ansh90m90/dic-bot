# The Fool's Attendant

A hardcore *Lord of the Mysteries* community Discord bot — the mystical arbiter
of the gray fog. It governs Beyonder progression, manages server privileges,
enforces a strict leveling curve, oversees Sealed Artifacts, regulates sanity and
corruption, hosts the anonymous Tarot Club, triggers Spirit World Anomalies, and
runs the Gemini-powered **Mystical Oracle**.

Built with **Python + discord.py**, persisted in **SQLite**, with a
**Google Gemini** backend for `/ask-oracle`.

---

## Features

- **22 Beyonder Pathways** with full Sequence 9 → 0 ladders, groups, and
  above-sequence beings.
- **Hardcore progression** — potion digestion, the potion economy (Gold Pounds /
  Tarot Coins), formulas & Beyonder characteristics, ingredient gathering,
  demigod/angel/acting trials, capped Angel & King-of-Angels slots, and a
  one-per-Pathway Sequence 0 (Apotheosis).
- **Sealed Artifacts** — equipable perks with dangerous curses (XP multipliers,
  message-devouring, daily corruption/sanity drain).
- **The Tarot Club** — anonymous gatherings under Major Arcana aliases, relayed
  through webhooks so true identities stay hidden.
- **Spirit World Anomalies** — random `/pray` and `/enter` encounters in active
  channels, plus manual admin triggers.
- **The Madness Engine** — corruption, Mental Breakdowns, Zalgo nickname
  distortion, gibberish message filters, and banishment to the Fog of History.
- **The Mystical Oracle** (`/ask-oracle`) — strict LotM topic confinement, a hard
  refusal rule, spoiler protocol, and a rolling-24h daily limit.
- **Privilege hierarchy** — Owner (Above the Sequences), Admin (Archangel
  Council), and Moderator command groups with tiered authority.

---

## Requirements

- Python **3.9+**
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
- A Google **Gemini API key** ([Google AI Studio](https://aistudio.google.com/apikey)) — optional; the Oracle falls back to a curated lore bank without it.

## Setup

```bash
# 1. Clone / copy this folder, then install dependencies
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
#    Edit `.env` and fill in DISCORD_TOKEN and GEMINI_API_KEY.

# 3. Run
python main.py
```

### Discord permissions & intents

In the Developer Portal, enable the **Message Content** and **Server Members**
privileged intents (required for digestion-from-activity, the madness filter,
and nickname/timeout effects).

The bot invite needs, at minimum: *Manage Messages*, *Manage Nicknames*,
*Moderate Members* (for timeouts), *Manage Webhooks* (Tarot Club anonymity),
*Manage Channels* (Tarot Club room), and *Send Messages*.

---

## Command reference

### Member commands

| Command | Description |
|---|---|
| `/pathway choose <pathway>` | Swear fealty to a Pathway at Sequence 9. |
| `/pathway list` | List all 22 Pathways and their groups. |
| `/status [user]` | Check Sequence, Digestion %, Sanity, Corruption, Artifacts, and wealth. |
| `/digest` | View digestion and your Sequence's Acting Method. |
| `/advance` | Attempt to advance to the next Sequence (consumes resources, may demand a trial). |
| `/inventory` | View ingredients, formulas, characteristics, and Sealed Artifacts. |
| `/market trade <user> <item> [amount]` | Transfer ingredients/formulas or Gold Pounds. |
| `/equip <artifact_id>` | Equip a Sealed Artifact (accepting its curse). |
| `/unequip` | Seal (unequip) your artifact before logging off. |
| `/ask-oracle <question> [spoiler]` | Consult the Mystical Oracle (1 of your daily inquiries). |
| `/apotheosis initiate` | (Sequence 1 only) Begin the trial to ascend to Sequence 0. |
| `/pray <target>` | Beseech the gray fog during a "ravings"/"fog tide" anomaly. |
| `/enter` | Step through a mystical door during a "door" anomaly. |

### Tarot Club

| Command | Description |
|---|---|
| `/tarot join` | Join and receive an anonymous Major Arcana alias. |
| `/tarot speak <message>` | Speak anonymously as your alias. |
| `/tarot leave` | Vacate your seat. |
| `/tarot open` / `/tarot close` | *(Admin)* Open/close the Club channel and aliases. |

### Creator — Server Owner (`Above the Sequences`)

| Command | Description |
|---|---|
| `/creator appoint <user> <pathway> <seq>` | Grant any rank, Sequence 9 → 0. |
| `/creator artifact <grade> <effect> [target]` | Forge a custom Sealed Artifact. |
| `/creator item <user> <item> [qty]` | Grant gold, Tarot Coins, ingredients, formulas, characteristics, or Uniqueness. |
| `/creator strip <user>` | Strip a Deity's Uniqueness and cast them back to Sequence 1. |
| `/creator force-loss <user>` | Force a Beyonder into Loss of Control. |

### Angel — Server Admin (`Archangel Council`)

| Command | Description |
|---|---|
| `/angel bestow <user> <pathway> <seq>` | Promote up to Sequence 4 only (Sequence 3+ is divinely rejected). |
| `/angel anomaly <event_type>` | Manually spawn a Spirit World Anomaly. |
| `/angel cleanse <user>` | Reset a member's madness meter (corruption + sanity). |
| `/angel purify <user>` | Purge corruption only. |
| `/angel trial pass <user>` | Pass a pending advancement trial. |
| `/angel apotheosis crown <user>` | Crown a King of Angels who completed their Apotheosis. |

### Moderator

| Command | Description |
|---|---|
| `/moderator warn <user>` | Issue a sanity warning (corruption spike). |
| `/moderator confiscate <user> <artifact_id>` | Confiscate a Grade 3 Artifact. |

---

## Privilege tiers

| Tier | Entity | Who counts |
|---|---|---|
| Above the Sequences | Server Owner | Guild owner **or** any ID in `OWNER_IDS`. |
| Archangel Council | Server Admins | `Administrator` permission **or** the `ADMIN_ROLE` role. |
| Delegated Roles | Moderators | `Manage Messages` permission **or** the `MOD_ROLE` role. |

Role names are configurable via `ADMIN_ROLE` / `MOD_ROLE` in `.env`.

---

## Progression curve

| Target Sequence | Gold | Ingredients | Other |
|---|---|---|---|
| 8 | 50 | 1 common | — |
| 7 | 100 | 2 common | — |
| 6 | 250 | 3 common + 2 uncommon | — |
| 5 | 500 | 3 common + 2 uncommon | — |
| 4 (Demigod) | 1,500 | 3 common + 3 uncommon + 1 rare | 30 days · **Demigod Trial** |
| 3 (Saint) | 4,000 | 4 uncommon + 2 rare + 1 legendary | **Demigod Trial** |
| 2 (Angel) | 10,000 | 3 rare + 2 legendary | 90 days · **Angel's Acting Trial** |
| 1 (King of Angels) | 25,000 | 3 legendary | 180 days · **Acting Trial** · capped slots |
| 0 (True God) | — | Uniqueness + Apotheosis | One per Pathway · **server-wide event** |

Every advancement also requires the target Sequence's **potion formula** and a
**Beyonder characteristic**, plus 100% digestion. Requirements are defined in
`data/pathways.py` (`advancement_requirements`) and are easy to tune.

---

## Deploy on Fly.io

The repo ships a `Dockerfile`, `fly.toml`, and `.dockerignore` ready for Fly.
A bot needs one always-on process (no HTTP), so `fly.toml` defines a worker and
mounts a **volume** at `/data` so the SQLite DB and `settings.json` survive
restarts.

```bash
fly auth login
# Edit `app = "..."` in fly.toml to a globally unique name, then:
fly launch --no-deploy
fly volumes create fools_data --region iad --size 1
fly secrets set DISCORD_TOKEN=... GEMINI_API_KEY=...
fly deploy
fly logs
```

Expected first boot: `Logged in as The Fool's Attendant...` and
`Synced N slash commands`.

- `DATABASE_PATH=/data/fools_attendant.db` and `SETTINGS_PATH=/data/settings.json`
  are set in `fly.toml` and point at the mounted volume.
- Keep it at a single machine (`fly scale count 1`) — SQLite + one worker.
- The `shared-cpu-1x` / 512 MB VM in `fly.toml` is the cheapest practical size.

---

## Multi-PC failover (optional)

Discord allows only **one** gateway connection per bot token, so this is
**active–passive**: one PC leads, the others wait and take over if the leader
goes dark. A Firestore **lease** elects the leader; the SQLite DB is synced to
Firebase Cloud Storage so a standby can resume.

**Setup**
1. In Firebase: create a project, enable **Firestore** and **Cloud Storage**.
2. Project settings → Service accounts → generate a JSON key; save it locally.
3. On every PC: `pip install -r requirements-ha.txt`.
4. Add to `.env` on every PC:
   ```
   HA_ENABLED=true
   FIREBASE_CREDENTIALS=path/to/service-account.json
   FIREBASE_BUCKET=your-project.appspot.com
   ```
5. Run `python main.py` on each PC. One prints `Acquired leadership` and runs;
   the others print `Standby — waiting for leadership...`.

**How it works** — the leader renews the lease every `HA_LEASE_SECONDS/3`,
uploads a snapshot every `HA_SYNC_SECONDS`, and on shutdown uploads a final
snapshot and releases the lease. If the leader dies, its lease expires after
`HA_LEASE_SECONDS` and a standby downloads the last snapshot and takes over.

**Caveats**
- A force-killed PC loses up to `HA_SYNC_SECONDS` of recent activity (the last
  snapshot is slightly stale). Lower `HA_SYNC_SECONDS` to shrink that window.
- Keep exactly one leader — the lease enforces this, and a standby that steals
  an expired lease makes the old instance shut itself down.
- Leave `HA_ENABLED=false` for a normal single-PC run.

---

## Project layout

```
fools-attendant/
├── main.py               # entry point, bot setup, command sync
├── config.py             # env-driven configuration
├── requirements.txt
├── .env.example
├── data/
│   ├── pathways.py       # 22 pathways, sequences, groups, leveling curve
│   ├── ingredients.py    # ingredients, drop table, formula/characteristic keys
│   └── artifacts.py      # sealed artifact definitions
├── db/
│   └── database.py       # SQLite persistence layer
├── utils/
│   ├── persona.py        # voice, embeds, oracle prompt, refusal lines
│   ├── zalgo.py          # zalgo/gibberish text
│   ├── gemini.py         # Gemini REST client + fallback lore bank
│   └── checks.py         # privilege-tier checks
└── cogs/
    ├── progression.py    # /pathway, /status, /digest, /advance
    ├── oracle.py         # /ask-oracle
    ├── economy.py        # /inventory, /market, /equip, /unequip
    ├── apotheosis.py     # /apotheosis
    ├── tarot.py          # /tarot
    ├── anomalies.py      # /pray, /enter, anomaly scheduler
    ├── madness.py        # corruption engine
    └── admin.py          # /creator, /angel, /moderator
```

---

## Notes

- The Oracle consumes Gemini when `GEMINI_API_KEY` is set; otherwise it answers
  from a small curated lore bank (and still enforces the refusal rule).
- Sequence-0 uniqueness and Angel slots are tracked per pathway in SQLite.
- All timings, thresholds, role names, and costs are configurable in `.env`.
- Sequence-name ladders use the widely circulated English translations; tweak any
  of them in `data/pathways.py` and every command follows automatically.
