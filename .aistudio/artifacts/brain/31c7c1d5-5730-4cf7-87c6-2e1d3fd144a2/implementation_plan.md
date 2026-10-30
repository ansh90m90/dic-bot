# System Update: "The Fool's Attendant" Implementation Plan

A comprehensive architectural overhaul and balance pass for **The Fool's Attendant** Discord bot, featuring enhanced role management and Tarot sync, steepened progression with ritual backlash hazards, complete elimination of the Sealed Artifact subsystem, voice channel digestion dominance & long-term inactivity decay, and an 880×500 Discord-Dark Occult hybrid profile card renderer.

## User Review & Critical Decisions

> [!IMPORTANT]
> The following architectural and user preferences are confirmed:

- **Confirmed Decision 1 (Profile Card Aesthetic)**: A hybrid **Discord Dark Occult** design—combining sleek Discord dark theme surfaces (`#1E1F22`, `#2B2D31`, `#313338`, `#5865F2`) with mystical *Lord of the Mysteries* accents: glowing sacred geometry avatar frames tinted by Above-the-Sequences cosmic group colors, rounded status gauges, and runic stat cards.
- **Confirmed Decision 2 (365-Day Inactivity Demotion)**: Both actions are executed:
  1. The bot updates the database (drops Sequence by 1, resets digestion to 0%, clears deity slots if Sequence 0, cancels pending trials) and synchronizes Discord roles.
  2. The bot broadcasts an omen announcement to the server's default announcement / system channel warning the realm of a fallen Beyonder.
- **Confirmed Decision 3 (Tarot Club Auto-Creation with Custom Name)**:
  - `/tarot open [channel_name]`: Accepts an optional `channel_name` parameter (defaulting to `tarot-club`).
  - If the designated channel does not exist, the bot **automatically creates it** as a private chamber with permission overwrites (hidden from `@everyone`, read/write granted to the bot and the Tarot Club role), raising it in the guild and announcing its opening.
- **Confirmed Decision 4 (Digestion XP & Voice Dominance)**: Both text chatting and active presence in voice channels generate digestion XP. Being active in Voice Channels (VC) yields the most XP (60 ticks/hour with continuous progression and a +25% unmuted group presence bonus, far exceeding rate-limited chat ticks).

---

## 1. Overview & Core Concept

**The Fool's Attendant** simulates the perilous, mystical world of *Lord of the Mysteries*. This update reinforces the dread and prestige of advancing through the Sequences:

- **Strict Discord Hierarchy**: Roles now reflect formal sequence ranks (`{Pathway} · Seq {sequence} {Sequence Title}`), high sequences (Seq 4–0) are hoisted to tower over server member lists, and role synchronization is verified with diagnostic checks.
- **Punishing Advancement Curve**: Digestion multipliers drop sharply at higher sequences, messages require sustained substance (≥15 characters), and advancing carries a ritual backlash hazard that consumes reagents and inflicts severe sanity and corruption penalties upon failure.
- **Voice Presence Dominance & Decay**: Vocal presence in voice channels is the premier method of potion digestion, while extended inactivity invites mental fraying, corruption rise, and eventual sequence regression.
- **Complete Artifact Purge**: The legacy Sealed Artifact system is cleanly eradicated from the database, commands, lore prompt, and message loops.
- **Visual Hybrid Profile Cards**: `/profile` and `/status` generate an 880×500 Discord Dark Occult status slate with circular avatar framing, sacred geometry motifs, dynamic status gauges, and currency/progression stats.

---

## 2. User Experience & Visual Design

### Key User Flows

1. **Viewing Profile & Status (`/profile` & `/status`)**:
   - The user executes `/profile` or `/status [user]`.
   - The bot renders an 880×500 PNG graphic using Pillow, styling the card with Discord dark theme surfaces and mystical accents.
   - The card features the user's avatar enclosed in a sacred geometry ring, sequence badge, pathway name, group title, Tarot seat, rounded stat bars (Digestion, Sanity, Corruption), a 4-card metric grid (Gold, Tarot Coins, Active Days, Voice Hours), and the exact requirements for the next sequence ascension.
   - The graphic is attached to an evocative response embed.

2. **Digestion Progression (Chat vs. Voice Channel Dominance)**:
   - **Text Chat XP**: Awards `1.0% × multiplier × sanity_factor × corruption_penalty` for substantive messages (≥15 characters), throttled by an activity cooldown (180s base; 225s for Seq 4–3; 270s for Seq 2–1).
   - **Voice Channel (VC) Digestion (Highest Yield)**: Evaluated every 60 seconds. Active, non-deafened members in non-AFK voice channels earn continuous digestion ticks (`0.4% × multiplier × sanity_factor × corruption_penalty` per minute). If unmuted with other members present, a **+25% presence bonus** increases the rate to `0.5% × multiplier × sanity_factor × corruption_penalty` per minute, yielding up to **30.0% base digestion per hour**.

3. **Advancing Sequences (`/advance`)**:
   - The user attempts to ascend. If requirements (100% digestion, formula, characteristic, ingredients, gold, tarot coins, active days, sanity minimum, corruption maximum) are met:
   - If the sequence involves an Acting, Demigod, or Angel Trial, the trial is registered for Archangel adjudication.
   - If `advancement_hazard_enabled` is active, the ritual checks for backlash. On backlash failure, non-characteristic reagents and currencies are consumed, digestion drops by 15%–50%, sanity drops by 15%, and corruption spikes by 10%–45%. On success, the potion takes hold, the new hoisted role is granted, and the old sequence role is deleted.

4. **Tarot Club Gathering (`/tarot`)**:
   - Admin runs `/tarot open [channel_name]`. If the channel doesn't exist, it is auto-created with private permissions.
   - When a user runs `/tarot join`, their Major Arcana alias is assigned and the `tarot_role` is granted.
   - Inside the channel, `/tarot speak` relays messages via webhooks under their Tarot alias, concealing their true identity.
   - When a user leaves (`/tarot leave`) or an admin closes the gathering (`/tarot close`), the role is revoked.

5. **Inactivity Decay & Sequence Regression**:
   - Beyonders inactive for >30 days suffer daily degradation (+5.0% Corruption, -5.0% Digestion, -2.0% Sanity).
   - Beyonders inactive for >365 days suffer regression: Sequence drops by 1, digestion resets to 0%, deity slots and trials are cleared, roles are updated, and an ominous omen announcement is broadcast to the server's default announcement/system channel.

6. **Help Directory (`/help [topic]`)**:
   - Running `/help` displays an index explaining core systems.
   - Autocomplete provides deep dive subtopics (`mechanics`, `progression`, `inactivity`, `voice`, `roles`) with exact numerical formulas and requirements.

### Visual Identity & Theme (Discord Dark Occult Hybrid)

- **Canvas Size**: 880 × 500 px.
- **Background & Card Surfaces**:
  - Outer background: Deep Discord canvas (`#111214`).
  - Card container: Modern dark slate (`#1E1F22`) with subtle `#2B2D31` card panels and rounded corners.
  - Border: Soft 1px stroke in `#35373C` with luminous corner glyphs.
- **Group Color Accents (Sacred Geometry Ring)**:
  - *Lord of the Mysteries*: `#7B74B8` (Ethereal Amethyst)
  - *God Almighty*: `#D9B44A` (Solar Gold)
  - *Eternal Darkness*: `#4E4E6A` (Abyssal Slate)
  - *Calamity of Destruction*: `#C43D49` (Crimson Flame)
  - *Demon of Knowledge*: `#4E9A78` (Emerald Glyphs)
  - *Father of Devils*: `#8A3A50` (Blood Rune)
  - *Goddess of Origin*: `#C98CB6` (Lunar Rose)
  - *Anarchy*: `#A88848` (Bronze Arbiter)
  - *Key of Light*: `#B39FE0` (Silver Wheel)
- **Bar Gauges**:
  - Digestion: Violet / Gold gradient
  - Sanity: Serene Teal (`#38B2AC`) fading to Amber
  - Corruption: Eldritch Crimson (`#E53E3E`)

---

## 3. Key Product Decisions & Trade-Offs

- **Decision 1: Removal of Sealed Artifacts**:
  - *Chosen Approach*: Clean deletion of `data/artifacts.py`, database table, user columns, and command references.
  - *Why*: The Sealed Artifact system created balance anomalies, text clutter, and unwanted message deletions. Purging it completely streamlines the database schema and focuses the game loop on authentic pathway progression.

- **Decision 2: In-Memory Headless Image Generation with Pillow**:
  - *Chosen Approach*: Use Pillow to draw geometric vectors, text, and circular masked avatars directly into an in-memory `io.BytesIO` buffer, served as `discord.File(fp=buf, filename="profile.png")`.
  - *Why*: Zero browser or Chromium overhead, instant sub-50ms generation time, robust offline compatibility, and deterministic layout math.

- **Decision 3: Fail-Safe Role Synchronization & Diagnostics**:
  - *Chosen Approach*: `sync_beyonder_role` checks bot permissions (`manage_roles`) and role hierarchy (`guild.me.top_role > role`), in-place renames legacy roles to avoid orphaned duplicates, deletes older sequence roles, and returns `(role, error_reason)` so users and administrators receive actionable diagnostics if Discord permission errors occur.

---

## 4. Technical Architecture & Data Strategy

### System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Discord Gateway & Loops                         │
│  ┌────────────────┐    ┌─────────────────┐    ┌──────────────────────┐ │
│  │ on_message     │    │ on_voice_state  │    │ 60s VC Digestion     │ │
│  │ Digestion Gain │    │ Activity Update │    │ Loop & Madness Loop  │ │
│  └───────┬────────┘    └────────┬────────┘    └──────────┬───────────┘ │
└──────────┼──────────────────────┼────────────────────────┼─────────────┘
           │                      │                        │
           ▼                      ▼                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          Database (SQLite)                             │
│  users: [user_id, pathway, sequence, digestion, sanity, corruption,    │
│          gold, tarot_coins, active_days, last_active_ts,               │
│          last_decay_check_ts, last_demotion_ts, vc_minutes,            │
│          beyond_role_id, ...]                                          │
│  (Dropped: artifacts table & equipped_artifact column)                 │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌────────────────────────────────┐         ┌─────────────────────────────┐
│    Progression & Ascension     │         │      Presentation & UI      │
│  • DIGESTION_MULTIPLIERS       │         │  • utils/profile_card.py    │
│  • VC Dominant Digestion       │         │    (880x500 Discord-Occult  │
│  • Sanity & corruption scaling │         │     Pillow Slate)           │
│  • Backlash Hazard Calculation │         │  • cogs/meta.py /help       │
│  • utils/roles.py Sync & Hoist │         │    (Subtopic Autocomplete)  │
└────────────────────────────────┘         └─────────────────────────────┘
```

### Database Schema Migrations

```sql
-- Purge sealed artifacts
DROP TABLE IF EXISTS artifacts;
DROP INDEX IF EXISTS idx_artifacts_equipped;

-- Add Voice & Decay tracking columns
ALTER TABLE users ADD COLUMN last_active_ts REAL DEFAULT 0;
ALTER TABLE users ADD COLUMN last_decay_check_ts REAL DEFAULT 0;
ALTER TABLE users ADD COLUMN last_demotion_ts REAL DEFAULT 0;
ALTER TABLE users ADD COLUMN vc_minutes INTEGER DEFAULT 0;
```

### Detailed File Modification Map

1. **`requirements.txt`**:
   - Add `Pillow>=10.0.0`.

2. **`db/database.py`**:
   - Run schema migrations for new columns (`last_active_ts`, `last_decay_check_ts`, `last_demotion_ts`, `vc_minutes`).
   - Purge artifact methods (`add_artifact`, `get_artifact`, `get_artifacts`, `get_equipped`, `equip_artifact`, `unequip_artifact`, `delete_artifact`, `equipped_artifacts_all`).
   - Add helper methods: `touch_activity(user_id)`, `add_vc_minutes(user_id, minutes)`, `apply_decay(...)`, and `demote_user_sequence(user_id)`.

3. **`utils/roles.py`**:
   - Implement `resolve_member(guild, user_or_member)`.
   - Update role naming format to `"{Pathway Name} · Seq {sequence} {Sequence Title}"`.
   - In-place rename legacy roles (`"{Pathway Name} · {Sequence Title}"`).
   - Delete older sequence roles upon promotion/demotion.
   - Set `hoist=True` for sequences `<= 4`.
   - Return `(role, error_reason)` with full permission and hierarchy diagnostics.
   - Implement `sync_all_guild_roles(bot, guild)` helper.

4. **`data/pathways.py` & `data/ingredients.py`**:
   - Configure `DIGESTION_MULTIPLIERS` (Seq 9: 1.0 down to Seq 1: 0.015, Seq 0: 0.0).
   - Update advancement requirements table with new gold, tarot coins, characteristics, multi-rarity ingredients, active days, sanity/corruption thresholds, and hazard risks.

5. **`cogs/progression.py`**:
   - Enforce minimum message length (`15` chars), scaled cooldowns, sanity factor, and corruption penalty in `on_message`.
   - Add 60s `vc_digestion_loop` tracking `vc_minutes`, checking non-AFK, non-deafened state, and granting bonus XP if unmuted with others present.
   - Implement backlash calculation in `/advance` with reagent loss and stat penalties.
   - Hook `/profile` and `/status` to send the generated Pillow profile card.

6. **`cogs/madness.py`**:
   - Purge artifact loops and text curses.
   - Implement `_apply_inactivity_decay()` inside `madness_loop`:
     - `> 30 days`: Daily +5.0% corruption, -5.0% digestion, -2.0% sanity.
     - `> 365 days`: Sequence drop by 1, digestion reset to 0%, deity/trial clearing, role re-sync, and system channel omen broadcast.

7. **`cogs/tarot.py`**:
   - Auto-create/grant `settings.get("tarot_role")` on `/tarot join`.
   - In `/tarot open [channel_name]`, accept optional custom channel name, auto-create the channel if missing with private overwrites, and grant read/write access to the tarot role.
   - Revoke role on `/tarot leave` and `/tarot close`.

8. **`cogs/admin.py` & `cogs/economy.py`**:
   - Remove artifact commands (`/creator artifact`, `/moderator confiscate`, `/equip`, `/unequip`).
   - Add `/angel sync-roles` command returning synchronization metrics.
   - Add `/shop buy characteristic` and update shop prices.

9. **`utils/profile_card.py`**:
   - Create Pillow rendering module producing 880×500 Discord Dark Occult hybrid cards with geometry, avatars, stat bars, and progression cards.

10. **`cogs/meta.py` & `main.py`**:
    - Overhaul `/help` with high-level summaries and autocomplete subtopics (`mechanics`, `progression`, `inactivity`, `voice`, `roles`).
    - Enable `intents.voice_states = True` in `main.py` and run `sync_all_guild_roles` on `on_ready`.
    - Add `on_member_join` role restoration listener.

---
