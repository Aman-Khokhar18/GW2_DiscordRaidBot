from typing import Dict

import discord
from discord.ext import commands
import io
import json
import gzip

from aiohttp import ClientResponseError

from config import Config
from dps_report_client import (
    upload_to_dps_report,
    fetch_ei_json,
    fetch_upload_metadata,
)
from gw2_stats import (
    get_player_dps,
    get_mechanic_summary,
    compute_support_metrics,
    mechanic_fail_counts,
    mechanic_success_scores,
    mechanic_fail_scores,
    compute_boss_damage,
    BOON_GENERATION_WEIGHTS,
)
from mechanics_config import get_fail_rules_for_boss, get_success_rules_for_boss
from scoring import compute_support_scores, compute_mvp
from icons import icon_for_profession


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=Config.COMMAND_PREFIX,
    intents=intents,
    help_command=None,  # custom help if you want later
)

# ---------------------------------------------------------------------------
# Profession -> Icon mapping
# Replace these with your server's custom emojis if you want real GW2 icons.
# Example custom emoji: "Guardian": "<:guardian:123456789012345678>"
# ---------------------------------------------------------------------------




def build_name_prof_map(ei_json: dict) -> Dict[str, str]:
    """
    Build a mapping from player name -> profession/spec string
    using the same logic as gw2_stats._safe_get_profession.
    """
    mapping: Dict[str, str] = {}
    for p in ei_json.get("players", []) or []:
        name = p.get("name") or p.get("character_name") or "Unknown"
        prof = (
            p.get("profession")
            or p.get("professionName")
            or p.get("spec")
            or "Unknown"
        )
        mapping[name] = prof
    return mapping





def format_with_icon(name: str, name_prof_map: Dict[str, str]) -> str:
    """
    Given a player name and a name->profession map, return "[icon] name"
    if we can find a matching icon, else just "name".
    """
    prof = name_prof_map.get(name)
    if not prof:
        return name
    icon = icon_for_profession(prof)
    return f"{icon} {name}" if icon else name


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def fetch_log_ei(
    ctx: commands.Context,
    report: str | None,
):
    """
    Shared helper that:
      - If `report` is provided: treats it as dps.report URL or ID.
      - Else: expects an attached ArcDPS log file.

    Returns:
      (ei_json, boss_name, duration_seconds, success, is_cm, permalink)
    or None on error (after sending a message to ctx).
    """
    # -----------------------------
    # Mode 1: dps.report link or ID
    # -----------------------------
    if report is not None:
        ref = report.strip().strip("<>")

        if "dps.report" in ref:
            ref = ref.split("/")[-1]

        report_id = ref
        await ctx.send(f"Fetching existing report `{report_id}` from dps.report…")

        try:
            ei_json = await fetch_ei_json(report_id)
        except ClientResponseError as e:
            if e.status in (403, 404):
                # Try to see if EI JSON is even available for this log
                try:
                    meta = await fetch_upload_metadata(report_id)
                except Exception:
                    await ctx.send(
                        f"Elite Insights JSON for `{report_id}` is not accessible (HTTP {e.status}).\n"
                        f"- The HTML page can still work fine.\n"
                        f"- What the bot needs is the API endpoint:\n"
                        f"  https://dps.report/getJson?id={report_id}\n"
                        f"If opening that URL (or the `permalink` variant) in your browser "
                        f"also gives an error, then EI JSON for this log is not publicly "
                        f"exposed by dps.report."
                    )
                    return None

                encounter = meta.get("encounter", {}) if isinstance(meta, dict) else {}
                json_available = encounter.get("jsonAvailable")

                if json_available is False:
                    await ctx.send(
                        f"Elite Insights JSON is **not available** for this report (`{report_id}`).\n"
                        f"Re-upload the log to dps.report with EI JSON enabled, or use a different report."
                    )
                else:
                    await ctx.send(
                        f"dps.report refused EI JSON for `{report_id}` (HTTP {e.status}).\n"
                        f"This can happen if the log is private or restricted. "
                        f"Try opening these in your browser:\n"
                        f"- https://dps.report/getJson?id={report_id}\n"
                        f"- https://dps.report/getJson?permalink={report_id}"
                    )
                return None

            await ctx.send(f"Failed to fetch Elite Insights JSON: HTTP {e.status} – {e.message}")
            return None

        except Exception as e:
            await ctx.send(f"Failed to fetch Elite Insights JSON: `{e}`")
            return None

        boss_name = (
            ei_json.get("fightName")
            or ei_json.get("encounter", {}).get("boss")
            or "Unknown Boss"
        )
        success = bool(
            ei_json.get("success")
            or ei_json.get("encounter", {}).get("success", False)
        )
        is_cm = bool(
            ei_json.get("isCM")
            or ei_json.get("isCm")
            or ei_json.get("encounter", {}).get("isCm", False)
        )

        duration = None
        duration_ms = (
            ei_json.get("durationMS")
            or ei_json.get("encounterDuration")
        )
        if duration_ms is None:
            phases = ei_json.get("phases") or []
            if phases:
                duration_ms = (
                    phases[0].get("durationMS")
                    or phases[0].get("duration")
                )
        if isinstance(duration_ms, (int, float)):
            duration = duration_ms / 1000.0

        permalink = f"https://dps.report/{report_id}"
        return ei_json, boss_name, duration, success, is_cm, permalink

    # ----------------------------------
    # Mode 2: attached ArcDPS log upload
    # ----------------------------------
    if not ctx.message.attachments:
        await ctx.send(
            "Attach a GW2 ArcDPS log (`.evtc`, `.evtc.zip`, `.zevtc`) "
            "or pass a dps.report link: `!log https://dps.report/xxxxx`."
        )
        return None

    attachment = ctx.message.attachments[0]
    if not any(
        attachment.filename.endswith(ext)
        for ext in (".evtc", ".evtc.zip", ".zevtc")
    ):
        await ctx.send(
            "That doesn't look like an ArcDPS log. "
            "Please upload a `.evtc`, `.evtc.zip`, or `.zevtc` file."
        )
        return None

    await ctx.send(f"Uploading `{attachment.filename}` to dps.report…")
    file_bytes = await attachment.read()

    try:
        upload_json = await upload_to_dps_report(file_bytes, attachment.filename)
    except Exception as e:
        await ctx.send(f"Upload to dps.report failed: `{e}`")
        return None

    if upload_json.get("error"):
        await ctx.send(f"dps.report returned an error: `{upload_json['error']}`")
        return None

    report_id = upload_json.get("id")
    permalink = upload_json.get("permalink")
    encounter = upload_json.get("encounter", {})

    boss_name = encounter.get("boss", "Unknown Boss")
    duration = encounter.get("duration", None)
    success = encounter.get("success", False)
    json_available = encounter.get("jsonAvailable", False)
    is_cm = encounter.get("isCm", False)

    if not json_available:
        await ctx.send(
            f"{boss_name} – Elite Insights JSON is not available for this log.\n"
            f"Report: {permalink or 'N/A'}"
        )
        return None

    try:
        ei_json = await fetch_ei_json(report_id)
    except Exception as e:
        await ctx.send(f"Failed to fetch EI JSON: `{e}`")
        return None

    return ei_json, boss_name, duration, success, is_cm, permalink


def compute_encounter_metrics(
    ei_json: dict,
    boss_name: str,
    phase_index: int,
):
    """
    Compute all the stuff needed for log/mvp/fail/support:

      - player_rows (DPS list)
      - mechanic_summary
      - fail_counts (unweighted count)
      - mech_success_scores (weighted success)
      - fail_score_map (weighted fails)
      - support_metrics + support_scores
      - damage_share (boss HP%)
      - mvp_name + mvp_scores
      - name_prof_map (player name -> profession/spec)
    """
    player_rows = get_player_dps(ei_json, phase_index=phase_index)

    mechanic_summary = get_mechanic_summary(ei_json, boss_name=boss_name)
    fail_counts = mechanic_fail_counts(mechanic_summary)
    mech_success = mechanic_success_scores(mechanic_summary)
    fail_score_map = mechanic_fail_scores(mechanic_summary)

    support_metrics = compute_support_metrics(
        ei_json, phase_index=phase_index, mechanic_summary=mechanic_summary
    )
    support_scores = compute_support_scores(support_metrics)

    # Boss damage -> % boss HP per player
    # Boss damage -> share of total boss damage (matches log "Target All" style)
    raw_boss_damage = compute_boss_damage(
        ei_json, phase_index=phase_index, target_index=0
    )

    total_damage = sum(max(float(v), 0.0) for v in raw_boss_damage.values()) or 1.0
    damage_share: Dict[str, float] = {}
    for name, dmg in raw_boss_damage.items():
        damage_share[name] = max(float(dmg), 0.0) / total_damage

    mvp_name, mvp_scores = compute_mvp(
        boss_damage=damage_share,
        support_scores=support_scores,
        mech_success_scores=mech_success,
        mech_fail_scores=fail_score_map,
    )

    name_prof_map = build_name_prof_map(ei_json)

    return {
        "player_rows": player_rows,
        "mechanic_summary": mechanic_summary,
        "fail_counts": fail_counts,
        "mech_success_scores": mech_success,
        "fail_score_map": fail_score_map,
        "support_metrics": support_metrics,
        "support_scores": support_scores,
        "damage_share": damage_share,
        "mvp_name": mvp_name,
        "mvp_scores": mvp_scores,
        "name_prof_map": name_prof_map,
    }


async def render_encounter_summary(
    ctx: commands.Context,
    ei_json: dict,
    boss_name: str,
    duration,
    success: bool,
    is_cm: bool,
    permalink: str | None,
):
    """
    Used by !log – just DPS, success/fail, MVP (and a brief fail summary).
    """
    status_text = "✅ Success" if success else "❌ Fail"
    cm_text = " (CM)" if is_cm else ""
    if isinstance(duration, (int, float)):
        duration_text = f"{duration:.1f}s"
    else:
        duration_text = "Unknown"

    phase_index = Config.PHASE_INDEX

    metrics = compute_encounter_metrics(ei_json, boss_name, phase_index)
    player_rows = metrics["player_rows"]
    fail_counts = metrics["fail_counts"]
    mvp_name = metrics["mvp_name"]
    name_prof_map = metrics["name_prof_map"]

    if not player_rows:
        await ctx.send(
            f"{boss_name}{cm_text} – Could not find player DPS data in EI JSON."
        )
        return

    # DPS block
    dps_lines = []
    for rank, row in enumerate(player_rows[: Config.TOP_N_DPS], start=1):
        formatted_name = format_with_icon(row["name"], name_prof_map)
        dps_lines.append(
            f"**{rank}. {formatted_name}** – "
            f"{int(row['dps']):,} DPS"
        )

    # Failed mechanics (count only, for quick glance)
    mech_fail_lines = []
    for name, count in sorted(fail_counts.items(), key=lambda kv: kv[1], reverse=True):
        if count <= 0:
            continue
        formatted_name = format_with_icon(name, name_prof_map)
        mech_fail_lines.append(f"{formatted_name}: {count}")
    mech_fail_text = ", ".join(mech_fail_lines) if mech_fail_lines else "None 🎉"

    title = f"📜 {boss_name}{cm_text} – Encounter Summary"
    embed = discord.Embed(
        title=title,
        description="\n".join(dps_lines),
        colour=discord.Colour.blurple(),
    )

    embed.add_field(name="Result", value=status_text, inline=True)
    embed.add_field(name="Duration", value=duration_text, inline=True)
    if permalink:
        embed.add_field(name="Report", value=permalink, inline=False)


    if mvp_name is not None:
        mvp_label = format_with_icon(mvp_name, name_prof_map)
        embed.add_field(
            name="MVP",
            value=f"🏆 **{mvp_label}**",
            inline=False,
        )

    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# Bot events
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")
    print("------")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@bot.command(name="jsondebug")
async def jsondebug_command(ctx: commands.Context, *, report: str):
    """
    Fetch the full Elite Insights JSON for a dps.report link/ID
    and upload it as a compressed .json.gz file.
    """
    ref = report.strip().strip("<>")
    if "dps.report" in ref:
        ref = ref.split("/")[-1]

    report_id = ref
    await ctx.send(f"Fetching full EI JSON for `{report_id}`…")

    try:
        ei_json = await fetch_ei_json(report_id)
    except Exception as e:
        await ctx.send(f"Failed to fetch EI JSON: `{e}`")
        return

    raw = json.dumps(ei_json, ensure_ascii=False).encode("utf-8")
    compressed = gzip.compress(raw)

    size_kb = len(compressed) / 1024
    if size_kb > 8 * 1024:
        await ctx.send(
            f"Compressed JSON is still too large to upload (~{size_kb:.1f} KB). "
            f"Try using a smaller log or run the fetch script locally."
        )
        return

    buf = io.BytesIO(compressed)
    buf.seek(0)
    filename = f"ei_{report_id}.json.gz"
    await ctx.send(
        "Here is the full Elite Insights JSON (gzipped):",
        file=discord.File(buf, filename=filename),
    )


@bot.command(name="supportdebug")
async def supportdebug_command(ctx: commands.Context, *, report: str):
    """
    Debug command to inspect support metrics for a log.
    Shows per-player:
      - supportScore
      - per-boon group generation
      - healing, breakbar, mechSuccess
    """
    ref = report.strip().strip("<>")
    if "dps.report" in ref:
        ref = ref.split("/")[-1]

    report_id = ref
    await ctx.send(f"Fetching support metrics for `{report_id}`…")

    try:
        ei_json = await fetch_ei_json(report_id)
    except Exception as e:
        await ctx.send(f"Failed to fetch EI JSON: `{e}`")
        return

    mech_summary = get_mechanic_summary(ei_json)
    support = compute_support_metrics(
        ei_json,
        phase_index=Config.PHASE_INDEX,
        mechanic_summary=mech_summary,
    )

    # Build name->prof map for icons
    name_prof_map = build_name_prof_map(ei_json)

    lines: list[str] = []
    for name, m in support.items():
        boons_generated = m.get("boons_generated", {}) or {}
        if boons_generated:
            boon_parts = []
            for boon, amount in sorted(boons_generated.items()):
                w = BOON_GENERATION_WEIGHTS.get(boon, 1.0)
                boon_parts.append(f"{boon}={amount:.1f}s (w={w})")
            boon_str = ", ".join(boon_parts)
        else:
            boon_str = "none"

        label = format_with_icon(name, name_prof_map)

        line = (
            f"{label}: "
            f"supportScore={m['boon_score']:.1f} | "
            f"boons[{boon_str}] | "
            f"heal={m['healing']:.0f} | "
            f"bb={m['breakbar']:.0f} | "
            f"mechSuccess={m['mech_success']:.1f}"
        )
        lines.append(line)

    if not lines:
        await ctx.send("No support metrics found.")
        return

    chunk: list[str] = []
    for line in lines:
        chunk.append(line)
        if len("\n".join(chunk)) > 1800:
            await ctx.send("```text\n" + "\n".join(chunk) + "\n```")
            chunk = []
    if chunk:
        await ctx.send("```text\n" + "\n".join(chunk) + "\n```")


@bot.command(name="mechdebug")
async def mechdebug_command(ctx: commands.Context, *, report: str):
    """
    Debug command to inspect mechanics JSON from a dps.report link or ID.
    """
    ref = report.strip().strip("<>")
    if "dps.report" in ref:
        ref = ref.split("/")[-1]

    report_id = ref
    await ctx.send(f"Fetching mechanics for `{report_id}`…")

    try:
        ei_json = await fetch_ei_json(report_id)
    except Exception as e:
        await ctx.send(f"Failed to fetch EI JSON: `{e}`")
        return

    boss_name = (
        ei_json.get("fightName")
        or ei_json.get("encounter", {}).get("boss")
        or "Unknown Boss"
    )

    mechanics = ei_json.get("mechanics") or ei_json.get("mechanicLogs") or []
    if not mechanics:
        await ctx.send(f"No 'mechanics' section found in EI JSON for **{boss_name}**.")
        return

    mech_names = sorted(
        {m.get("name") or m.get("description") or "Unnamed mechanic" for m in mechanics}
    )
    summary = "\n".join(f"- {name}" for name in mech_names)
    if len(summary) > 1900:
        summary = summary[:1900] + "\n…(truncated)"

    await ctx.send(
        f"Mechanics for **{boss_name}**:\n"
        "```text\n" + summary + "\n```"
    )

    pretty = json.dumps(mechanics, indent=2, ensure_ascii=False)
    data = pretty.encode("utf-8")
    buf = io.BytesIO(data)
    buf.seek(0)

    safe_boss = "".join(c for c in boss_name if c.isalnum() or c in ("_", "-")) or "boss"

    await ctx.send(
        f"Full mechanics JSON for **{boss_name}**:",
        file=discord.File(buf, filename=f"mechanics_{safe_boss}_{report_id}.json"),
    )


@bot.command(name="log")
async def log_command(ctx: commands.Context, *, report: str | None = None):
    """
    Parse a log (upload or dps.report) and show:
      - DPS ranking
      - success/fail
      - MVP
    """
    result = await fetch_log_ei(ctx, report)
    if result is None:
        return

    ei_json, boss_name, duration, success, is_cm, permalink = result

    await render_encounter_summary(
        ctx,
        ei_json=ei_json,
        boss_name=boss_name,
        duration=duration,
        success=success,
        is_cm=is_cm,
        permalink=permalink,
    )


@bot.command(name="mvp")
async def mvp_command(ctx: commands.Context, *, report: str | None = None):
    """
    Rank players by MVP score (boss HP%, support, mechanics).
    """
    result = await fetch_log_ei(ctx, report)
    if result is None:
        return

    ei_json, boss_name, duration, success, is_cm, permalink = result
    phase_index = Config.PHASE_INDEX

    metrics = compute_encounter_metrics(ei_json, boss_name, phase_index)
    mvp_scores = metrics["mvp_scores"]
    damage_share = metrics["damage_share"]
    support_scores = metrics["support_scores"]
    mech_success_scores = metrics["mech_success_scores"]
    fail_score_map = metrics["fail_score_map"]
    name_prof_map = metrics["name_prof_map"]

    if not mvp_scores:
        await ctx.send("Could not compute MVP scores for this encounter.")
        return

    cm_text = " (CM)" if is_cm else ""
    title = f"🏆 {boss_name}{cm_text} – MVP Ranking"

    ranking = sorted(mvp_scores.items(), key=lambda kv: kv[1], reverse=True)

    lines = []
    for idx, (name, score) in enumerate(ranking, start=1):
        dmg_pct = damage_share.get(name, 0.0) * 100.0
        sup = support_scores.get(name, 0.0)
        mech_s = mech_success_scores.get(name, 0.0)
        mech_f = fail_score_map.get(name, 0.0)
        label = format_with_icon(name, name_prof_map)
        lines.append(
            f"**{idx}. {label}** – Score= {score:.3f} | "
            f"DPS%= {dmg_pct:.1f}% | Support= {sup:.2f} | "
            f"mech= +{mech_s:.1f} | fail= -{mech_f:.1f}"
        )

    desc = "\n".join(lines)
    embed = discord.Embed(
        title=title,
        description=desc[:4000],
        colour=discord.Colour.gold(),
    )
    if permalink:
        embed.add_field(name="Report", value=permalink, inline=False)

    await ctx.send(embed=embed)


@bot.command(name="fail")
async def fail_command(ctx: commands.Context, *, report: str | None = None):
    """
    Rank players by weighted mechanics fail score (desc), and also show:
      - total fail count
      - worst (heaviest) failed mechanic (excluding Dead/Downed)
      - down count
      - death count
    """
    result = await fetch_log_ei(ctx, report)
    if result is None:
        return

    ei_json, boss_name, duration, success, is_cm, permalink = result
    phase_index = Config.PHASE_INDEX

    metrics = compute_encounter_metrics(ei_json, boss_name, phase_index)
    fail_score_map = metrics["fail_score_map"]
    mechanic_summary = metrics["mechanic_summary"]
    name_prof_map = metrics["name_prof_map"]

    if not fail_score_map:
        await ctx.send("No mechanics fail data found.")
        return

    # Get per-mechanic fail weights for this boss
    fail_rules = get_fail_rules_for_boss(boss_name)
    default_fail_weight = float(fail_rules.get("__fail_default__", 1.0))

    cm_text = " (CM)" if is_cm else ""
    title = f"💀 {boss_name}{cm_text} – Mechanics Fail Ranking "

    ranking = sorted(fail_score_map.items(), key=lambda kv: kv[1], reverse=True)

    lines = []
    for idx, (name, score) in enumerate(ranking, start=1):
        if score <= 0:
            continue

        summary = mechanic_summary.get(name, {})
        fails: list[str] = summary.get("fails", []) or []

        # Total count of failed mechanics
        total_fails = len(fails)

        # Count downs & deaths separately
        down_count = 0
        death_count = 0
        for label in fails:
            lower = label.lower()
            if "downed" in lower:
                down_count += 1
            if "dead" in lower or "death" in lower:
                death_count += 1

        # Compute "worst" failed mechanic (weighted by config × count),
        # but ignore Dead / Downed types.
        worst_label = None
        worst_severity = 0.0
        worst_count = 0

        # Count occurrences per label
        label_counts: Dict[str, int] = {}
        for label in fails:
            label_counts[label] = label_counts.get(label, 0) + 1

        for label, count in label_counts.items():
            lower = label.lower()
            # skip generic death/downed events
            if "downed" in lower or "dead" in lower or "death" in lower:
                continue

            w = float(fail_rules.get(label, default_fail_weight))
            severity = w * count
            if severity > worst_severity:
                worst_severity = severity
                worst_label = label
                worst_count = count

        if worst_label is None:
            worst_str = "worst: (only deaths/downed)"
        else:
            worst_str = f"worst: {worst_label} x{worst_count}"

        label_with_icon = format_with_icon(name, name_prof_map)

        # Build detail string with optional downs/deaths
        detail_parts = [
            f"score= -{score:.1f}",
            f"fails={total_fails}",
            worst_str,
        ]
        if down_count > 0:
            detail_parts.append(f"downs= {down_count}")
        if death_count > 0:
            detail_parts.append(f"💀")

        details = " | ".join(detail_parts)

        lines.append(
            f"**{idx}. {label_with_icon}** – {details}"
        )

    if not lines:
        await ctx.send("No failed mechanics recorded. 🎉")
        return

    desc = "\n".join(lines)
    embed = discord.Embed(
        title=title,
        description=desc[:4000],
        colour=discord.Colour.red(),
    )
    if permalink:
        embed.add_field(name="Report", value=permalink, inline=False)

    await ctx.send(embed=embed)




@bot.command(name="support")
async def support_command(ctx: commands.Context, *, report: str | None = None):
    """
    Rank players by support score, also showing:
      - breakbar damage
      - highest boon generated for group (approx. % of fight duration)
      - res count (number of successful resurrect mechanics)
    """
    result = await fetch_log_ei(ctx, report)
    if result is None:
        return

    ei_json, boss_name, duration, success, is_cm, permalink = result
    phase_index = Config.PHASE_INDEX

    # Compute all encounter metrics
    metrics = compute_encounter_metrics(ei_json, boss_name, phase_index)
    support_scores = metrics["support_scores"]
    support_metrics = metrics["support_metrics"]
    mech_success_scores = metrics["mech_success_scores"]  # kept if you want later
    mechanic_summary = metrics["mechanic_summary"]
    name_prof_map = metrics["name_prof_map"]

    if not support_scores:
        await ctx.send("No support metrics found.")
        return

    # Try to get fight duration in seconds (for converting boon seconds -> %)
    fight_seconds = None
    duration_ms = (
        ei_json.get("durationMS")
        or ei_json.get("encounterDuration")
    )
    if duration_ms is None:
        phases = ei_json.get("phases") or []
        if phases:
            duration_ms = (
                phases[0].get("durationMS")
                or phases[0].get("duration")
            )
    if isinstance(duration_ms, (int, float)):
        fight_seconds = max(float(duration_ms) / 1000.0, 1.0)  # avoid divide-by-zero
    elif isinstance(duration, (int, float)):
        fight_seconds = max(float(duration), 1.0)

    cm_text = " (CM)" if is_cm else ""
    title = f"🛡️ {boss_name}{cm_text} – Support Ranking"

    # Sort by support score (desc)
    ranking = sorted(support_scores.items(), key=lambda kv: kv[1], reverse=True)

    lines = []
    for idx, (name, score) in enumerate(ranking, start=1):
        label = format_with_icon(name, name_prof_map)

        m = support_metrics.get(name, {}) or {}
        breakbar = float(m.get("breakbar", 0.0))
        boons_generated = m.get("boons_generated", {}) or {}

        # --- Top boon generated ---
        top_boon_str = "Boon: none"
        if boons_generated:
            boon_name, boon_seconds = max(
                boons_generated.items(),
                key=lambda kv: kv[1],
            )
            if fight_seconds:
                # Approximate % uptime this player generated for the group
                boon_pct = (float(boon_seconds) / fight_seconds) * 100.0
                # Clamp just in case of weird logs
                if boon_pct > 300.0:
                    boon_pct = 300.0
                top_boon_str = f"Boon: {boon_name} {boon_pct:.1f}%"
            else:
                top_boon_str = f"Boon: {boon_name} {boon_seconds:.1f}s"

        # --- Res count from mechanics summary ---
        res_count = 0
        summary = mechanic_summary.get(name, {}) or {}
        success_mechs = summary.get("success", []) or []
        for label_mech in success_mechs:
            lower = label_mech.lower()
            # Your EI mechanics use "Res" as the label, this keeps it robust
            if "res" in lower:
                res_count += 1

        # Build detail string
        parts = [
            f"Support={score:.3f}",
            f"Breakbar={breakbar:.0f}",
            top_boon_str,
        ]
        if res_count > 0:
            parts.append(f"Res={res_count}")

        detail_str = " | ".join(parts)

        lines.append(
            f"**{idx}. {label}** – {detail_str}"
        )

    desc = "\n".join(lines)
    embed = discord.Embed(
        title=title,
        description=desc[:4000],
        colour=discord.Colour.green(),
    )
    if permalink:
        embed.add_field(name="Report", value=permalink, inline=False)

    await ctx.send(embed=embed)

@bot.command(name="mechs")
async def mechs_command(ctx: commands.Context, *, report: str | None = None):
    """
    Rank players by mechanic success (done) score, showing:
      - weighted mechanic success score
      - top 3 success mechanics (by count, excluding res)
      - res count (if any)
    """
    result = await fetch_log_ei(ctx, report)
    if result is None:
        return

    ei_json, boss_name, duration, success, is_cm, permalink = result
    phase_index = Config.PHASE_INDEX

    metrics = compute_encounter_metrics(ei_json, boss_name, phase_index)
    mech_success_scores = metrics["mech_success_scores"]
    mechanic_summary = metrics["mechanic_summary"]
    name_prof_map = metrics["name_prof_map"]

    if not mech_success_scores:
        await ctx.send("No mechanic success data found.")
        return

    cm_text = " (CM)" if is_cm else ""
    title = f"🎯 {boss_name}{cm_text} – Mechanics"

    # Sort players by their weighted mechanic success score (desc)
    ranking = sorted(mech_success_scores.items(), key=lambda kv: kv[1], reverse=True)

    lines = []
    for idx, (name, score) in enumerate(ranking, start=1):
        summary = mechanic_summary.get(name, {}) or {}
        success_mechs = summary.get("success", []) or []

        # Build counts for top mechanics, EXCLUDING res
        label_counts: Dict[str, int] = {}
        res_count = 0
        for label in success_mechs:
            lower = label.lower()
            if "res" in lower:
                res_count += 1
                continue  # don't include in top mechanics
            label_counts[label] = label_counts.get(label, 0) + 1

        # Top 3 mechanics by count (non-res only)
        if label_counts:
            top_mechs = sorted(
                label_counts.items(),
                key=lambda kv: kv[1],
                reverse=True,
            )[:3]
            top_str = ", ".join(f"{label} x{cnt}" for label, cnt in top_mechs)
            top_str = f"Top: {top_str}"
        else:
            top_str = "Top: none"

        parts = [f"MechScore=+{score:.1f}", top_str]
        if res_count > 0:
            parts.append(f"Res={res_count}")

        details = " | ".join(parts)
        label_with_icon = format_with_icon(name, name_prof_map)

        lines.append(f"**{idx}. {label_with_icon}** – {details}")

    if not lines:
        await ctx.send("No successful mechanics recorded.")
        return

    desc = "\n".join(lines)
    embed = discord.Embed(
        title=title,
        description=desc[:4000],
        colour=discord.Colour.blue(),
    )
    if permalink:
        embed.add_field(name="Report", value=permalink, inline=False)

    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from config import Config as _C

    if not _C.DISCORD_BOT_TOKEN:
        raise SystemExit(
            "DISCORD_BOT_TOKEN is not set. Add it to your environment or .env file."
        )
    bot.run(_C.DISCORD_BOT_TOKEN)
