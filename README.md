# GW2 Discord Raid Bot

A small Discord bot for **Guild Wars 2** raids that reads **ArcDPS / Elite Insights logs from dps.report** and posts quick summaries:

- Top DPS with profession icons  
- MVP ranking (DPS, support, mechanics)  
- Mechanics fail overview (who ate what 😈)  
- Support rankings (boons, CC, resses)  
- Mechanics contribution overview  

Bot prefix is configurable via `Config.COMMAND_PREFIX` (default: `!` in `.env`).

---

## Features & Commands

### 1. Encounter Summary

**`!log [link|id]`**

- Input:  
  - `!log https://dps.report/XXXX-YYYY_boss`  
  - `!log XXXX-YYYY_boss`  
  - Or just `!log` with an attached `.evtc`, `.evtc.zip`, or `.zevtc` file
- Output:
  - Boss name, result (success/fail), duration
  - Top DPS list with profession icons  
  - MVP (best overall contribution)
  - Link to the dps.report page

---

### 2. MVP Ranking

**`!mvp [link|id]`**

- Ranks all players by **MVP score**, combining:
  - Share of total boss damage (DPS%)
  - Support score (boons, CC, etc.)
  - Positive mechanics done
  - Penalty for failed mechanics
- Shows per player:
  - Overall MVP score  
  - DPS%  
  - Support score  
  - Positive / negative mechanic scores  

---

### 3. Mechanics Fail Ranking

**`!fail [link|id]`**

- Ranks players by **weighted fail score** (using your `mechanics_config`).
- For each player shows:
  - Weighted fail score  
  - Total failed mechanics count  
  - Worst (heaviest) mechanic failed (excluding death/downed)  
  - Number of downs  
  - 💀 if they died

---

### 4. Support Ranking

**`!support [link|id]`**

- Ranks players by **support score** based on:
  - Boons generated for the group (with per-boon weights)
  - Breakbar damage
  - Successful mechanics
- For each player shows:
  - Support score  
  - Breakbar damage  
  - Top boon generated (highest contribution, shown as % of fight time or seconds)  
  - Res count (number of successful res mechanics), if any  

---

### 5. Mechanics Contribution

**`!mechs [link|id]`**

- Shows **mechanics done** per player.
- For each player:
  - Top 3 successful mechanics (by weighted contribution, excluding res)
  - Breakbar damage
  - Res count (if they did any resses)

---

## Debug / Developer Commands

These are mainly for inspecting how Elite Insights JSON looks and tuning weights:

### `!jsondebug [link|id]`
- Downloads the full **Elite Insights JSON** from dps.report and uploads it as a gzipped file (`.json.gz`) to Discord.

### `!supportdebug [link|id]`
- Shows raw support metrics per player:
  - Internal support score
  - Per-boon generation (with weights)
  - Healing, breakbar, mechanic success score  

### `!mechdebug [link|id]`
- Lists all mechanic names for that encounter.
- Also uploads the full `mechanics` array as a JSON file.

---

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/<your-username>/GW2_DiscordRaitBot.git
   cd GW2_DiscordRaitBot
