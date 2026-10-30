# The Fool's Attendant

A hardcore *Lord of the Mysteries* community Discord bot — the mystical arbiter
of the gray fog. It governs Beyonder progression, manages server privileges,
enforces a strict leveling curve, regulates sanity and corruption, hosts the
anonymous Tarot Club, triggers Spirit World Anomalies, and runs the Gemini-powered
**Mystical Oracle**.

Built with **Python + discord.py**, persisted in **SQLite**, with a
**Google Gemini** backend for `/ask-oracle`.

---

## Features

- **22 Beyonder Pathways** with full Sequence 9 → 0 ladders, groups, and
  above-sequence beings.
- **Hardcore progression** — potion digestion, the potion economy (Gold Pounds /
  Tarot Coins), formulas & Beyonder characteristics, ingredient gathering,
  acting/demigod/angel trials, ritual backlash hazards, capped Angel & King-of-Angels
  slots, and a one-per-Pathway Sequence 0 (Apotheosis).
- **Voice Channel (VC) Digestion Dominance** — continuous passive digestion per
  minute in voice channels with unmuted presence bonuses.
- **Inactivity Decay** — long-term inactivity degradation (>30 days) and Sequence
  regression (>365 days).
- **Visual Grimoire Profile Cards** — 880×500 Discord Dark Occult visual slates
  generated with Pillow.
- **The Tarot Club** — anonymous gatherings under Major Arcana aliases with
  automatic channel creation, permission syncing, and webhook relaying.
- **Spirit World Anomalies** — random `/pray` and `/enter` encounters in active
  channels, plus manual admin triggers.
- **The Madness Engine** — corruption, Mental Breakdowns, Zalgo nickname
  distortion, gibberish message filters, and banishment to the Fog of History.
- **The Mystical Oracle** (`/ask-oracle`) — strict LotM topic confinement, a hard
  refusal rule, spoiler protocol, and a rolling-24h daily limit.
- **Privilege hierarchy** — Owner (Above the Sequences), Admin (Archangel
  Council), and Moderator command groups with tiered authority and role synchronization.

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

In the Developer Portal, enable the **Message Content**, **Server Members**, and
**Voice States** privileged intents (required for chat & voice digestion, role sync,
and madness effects).

The bot invite needs, at minimum: *Manage Roles*, *Manage Messages*, *Manage Nicknames*,
*Moderate Members* (for timeouts), *Manage Webhooks* (Tarot Club anonymity),
*Manage Channels* (Tarot Club room), and *Send Messages*.

---

## Command reference

### Member commands

| Command | Description |
|---|---|
| `/profile [user]` | Inspect an 880×500 visual grimoire status card with estimated ascension timeline. |
| `/status [user]` | Check Sequence, Digestion %, Sanity, Corruption, and wealth. |
| `/pathway choose <pathway>` | Swear fealty to a Pathway at Sequence 9. |
| `/pathway list` | List all 22 Pathways and their groups. |
| `/digest` | View digestion multiplier and your Sequence's Acting Method. |
| `/advance` | Attempt to advance to the next Sequence (subject to ritual backlash). |
| `/divine <inquiry>` | Divine omens with the spirit pendulum to reap Gold Pounds & Tarot Coins. |
| `/bounty list` | Inspect available Spirit World hunting contracts. |
| `/bounty hunt <key>` | Hunt spirits and heretics for rich Gold and Tarot Coin bounties. |
| `/sacrifice <item> [qty]` | Offer monster ingredients to the gray fog in exchange for Gold and Tarot Coins. |
| `/inventory` | View ingredients, formulas, characteristics, and currencies. |
| `/market trade <user> <item> [amount]` | Transfer ingredients/formulas or Gold Pounds. |
| `/shop list` | View prices of ingredients, formulas, and characteristics. |
| `/shop buy <item>` | Purchase potion ingredients, formulas, or characteristics. |
| `/ask-oracle <question> [spoiler]` | Consult the Mystical Oracle (1 of your daily inquiries). |
| `/apotheosis initiate` | (Sequence 1 only) Begin the trial to ascend to Sequence 0. |
| `/pray <target>` | Beseech the gray fog during a "ravings"/"fog tide" anomaly. |
| `/enter` | Step through a mystical door during a "door" anomaly. |

### Tarot Club

| Command | Description |
|---|---|
| `/tarot join` | Join, receive an anonymous Major Arcana alias, and grant the Tarot role. |
| `/tarot speak <message>` | Speak anonymously as your alias via webhook. |
| `/tarot leave` | Vacate your seat and revoke the Tarot role. |
| `/tarot open [channel_name]` | *(Admin)* Auto-create or open the private Tarot Club channel. |
| `/tarot close` | *(Admin)* Close the Club, strip aliases, and revoke roles. |

### Creator — Server Owner (`Above the Sequences`)

| Command | Description |
|---|---|
| `/creator appoint <user> <pathway> <seq>` | Grant any rank, Sequence 9 → 0. |
| `/creator item <user> <item> [qty]` | Grant gold, Tarot Coins, ingredients, formulas, characteristics, or Uniqueness. |
| `/creator strip <user>` | Strip a Deity's Uniqueness and cast them back to Sequence 1. |
| `/creator force-loss <user>` | Force a Beyonder into Loss of Control. |

### Angel — Server Admin (`Archangel Council`)

| Command | Description |
|---|---|
| `/angel grant <user> <currency> <amount>` | Bestow any quantity of Gold Pounds or Tarot Coins upon any member. |
| `/angel sync-roles` | Resynchronize all Beyonder roles in the guild and return metrics. |
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

| Target Sequence | Gold | Tarot | Characteristics | Ingredients | Other | Hazard |
|---|---|---|---|---|---|---|
| 8 | 150 | 0 | 1× Seq 8 | 2 Common + 1 Uncommon | 2 active days · Sanity ≥60% · Corruption ≤50% | 5% |
| 7 | 400 | 1 | 1× Seq 7 | 3 Common + 2 Uncommon | 5 active days · Sanity ≥65% · Corruption ≤45% | 10% |
| 6 | 1,000 | 2 | 1× Seq 6 | 4 Common + 3 Uncommon + 1 Rare | 10 active days · Sanity ≥70% · Corruption ≤40% | 15% |
| 5 | 2,500 | 4 | 1× Seq 5 | 5 Common + 4 Uncommon + 2 Rare | 18 active days · Sanity ≥75% · Corruption ≤35% · **Acting Trial** | 20% |
| 4 (Demigod) | 7,500 | 8 | 1× Seq 4 | 5 Common + 5 Uncommon + 3 Rare + 1 Legendary | 35 active days · Sanity ≥80% · Corruption ≤25% · **Demigod Trial** | 25% |
| 3 (Saint) | 20,000 | 15 | 1× Seq 3 | 6 Uncommon + 4 Rare + 2 Legendary | 60 active days · Sanity ≥85% · Corruption ≤20% · **Demigod Trial** | 30% |
| 2 (Angel) | 55,000 | 30 | 2× Seq 2 | 6 Rare + 4 Legendary | 100 active days · Sanity ≥88% · Corruption ≤15% · **Angel Trial** · max 6 Angels | 35% |
| 1 (King) | 150,000 | 60 | 3× Seq 1 | 8 Rare + 6 Legendary | 180 active days · Sanity ≥92% · Corruption ≤10% · **Acting Trial** · max 3 Kings | 40% |
| 0 (True God) | — | 25 | 3× Seq 1 | Uniqueness | Sanity ≥90% · Corruption ≤10% · **Apotheosis Event** | — |

---

## Project layout

```
fools-attendant/
├── main.py               # entry point, bot setup, command sync, role sync
├── config.py             # env-driven configuration
├── requirements.txt
├── .env.example
├── data/
│   ├── pathways.py       # 22 pathways, sequences, groups, leveling curve & multipliers
│   └── ingredients.py    # ingredients, drop table, formula/characteristic keys
├── db/
│   └── database.py       # SQLite persistence layer
├── utils/
│   ├── persona.py        # voice, embeds, oracle prompt, refusal lines
│   ├── profile_card.py   # 880x500 Discord Dark Occult Pillow visual generator
│   ├── roles.py          # role resolution, formatting, hoisting & sync diagnostics
│   ├── zalgo.py          # zalgo/gibberish text
│   ├── gemini.py         # Gemini REST client + fallback lore bank
│   └── checks.py         # privilege-tier checks
└── cogs/
    ├── progression.py    # /profile, /status, /digest, /advance, VC digestion loop
    ├── oracle.py         # /ask-oracle
    ├── economy.py        # /inventory, /market trade
    ├── apotheosis.py     # /apotheosis initiate
    ├── tarot.py          # /tarot join, speak, leave, open, close
    ├── anomalies.py      # /pray, /enter, anomaly scheduler
    ├── madness.py        # corruption & inactivity decay engine (>30d, >365d)
    ├── admin.py          # /creator, /angel, /moderator, /angel sync-roles
    ├── features.py       # /daily, /leaderboard, /shop
    └── meta.py           # /settings, /help with subtopics
```
