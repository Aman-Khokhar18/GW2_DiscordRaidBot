from typing import Dict, List, Any, Optional, Set

from mechanics_config import get_success_rules_for_boss, get_fail_rules_for_boss


IMPORTANT_BOONS: Set[str] = {
    "Might",
    "Fury",
    "Quickness",
    "Alacrity",
    "Protection",
    "Stability",
}

# Per-boon weights for support score
BOON_GENERATION_WEIGHTS: Dict[str, float] = {
    "Might": 0.4,
    "Fury": 0.2,
    "Quickness": 1.5,
    "Alacrity": 1.5,
    "Protection": 0.5,
    "Stability": 0.3,
}


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def _safe_get_player_name(player: dict) -> str:
    return player.get("name") or player.get("character_name") or "Unknown"


def _safe_get_profession(player: dict) -> str:
    return (
        player.get("profession")
        or player.get("professionName")
        or player.get("spec")
        or "Unknown"
    )


# ---------------------------------------------------------------------------
# DPS / Breakbar
# ---------------------------------------------------------------------------

def get_player_dps(ei_json: dict, phase_index: int = 0) -> List[Dict[str, Any]]:
    """
    Returns a sorted list of players with DPS and breakbar damage for the given phase.

    [
      {"name": "...", "profession": "...", "dps": float, "breakbar": float},
      ...
    ]
    """
    players = ei_json.get("players", [])
    rows: List[Dict[str, Any]] = []

    for p in players:
        name = _safe_get_player_name(p)
        prof = _safe_get_profession(p)

        dps_all = p.get("dpsAll", []) or p.get("dpsTargets", [])
        if not dps_all or phase_index >= len(dps_all):
            continue

        stats = dps_all[phase_index] or {}
        dps = stats.get("dps") or stats.get("Dps") or stats.get("dpsAll") or 0.0
        breakbar = stats.get("breakbarDamage") or stats.get("BreakbarDamage") or 0.0

        rows.append(
            {
                "name": name,
                "profession": prof,
                "dps": float(dps),
                "breakbar": float(breakbar),
            }
        )

    rows.sort(key=lambda r: r["dps"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Mechanics (success / fail)
# ---------------------------------------------------------------------------

def get_mechanic_summary(
    ei_json: dict,
    boss_name: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Extract mechanics and compute per-player success/fail info.

    Uses Elite Insights "mechanics" array with entries like:
      {
        "name": "Downed",
        "mechanicsData": [
           {"time": 12395, "actor": "Unholy Princess"},
           ...
        ]
      }

    Also uses mechanics_config.{SUCCESS,FAILED}_MECHANICS_CONFIG
    via get_success_rules_for_boss/get_fail_rules_for_boss.

    Returns:
    {
      "Player Name": {
         "fails": [ "Breath", "Tantrum", ... ],
         "success": [ "CC", "Slub", ... ],
         "fail_score": float,    # weighted by FAILED_MECHANICS_CONFIG
         "success_score": float, # weighted by SUCCESS_MECHANICS_CONFIG
      },
      ...
    }
    """
    if boss_name is None:
        boss_name = ei_json.get("fightName") or ""

    players = ei_json.get("players", [])
    result: Dict[str, Dict[str, Any]] = {
        _safe_get_player_name(p): {
            "fails": [],
            "success": [],
            "fail_score": 0.0,
            "success_score": 0.0,
        }
        for p in players
    }

    mechanics = ei_json.get("mechanics", []) or []

    success_rules = get_success_rules_for_boss(boss_name)
    fail_rules = get_fail_rules_for_boss(boss_name)

    default_success_weight = success_rules.get("__success_default__")
    default_fail_weight = fail_rules.get("__fail_default__")

    for mech in mechanics:
        label = (
            mech.get("name")
            or mech.get("fullName")
            or mech.get("description")
            or "Unknown mechanic"
        )
        lower_label = label.lower()

        # Config-based classification
        conf_success_weight = success_rules.get(label)
        conf_fail_weight = fail_rules.get(label)

        is_success_conf = conf_success_weight is not None
        is_fail_conf = conf_fail_weight is not None

        # Fallback to simple heuristics if not configured
        if not (is_success_conf or is_fail_conf):
            is_fail = False
            is_success = False

            # Fail-ish keywords
            if any(
                k in lower_label
                for k in ("downed", "death", "floor", "fail", "breath", "tantrum", "poison dmg")
            ):
                is_fail = True

            # Success-ish keywords
            if any(k in lower_label for k in ("cc", "slub", "res", "got up", "fixate")):
                is_success = True

            # Assign default weights if available
            if is_fail and default_fail_weight is not None:
                conf_fail_weight = float(default_fail_weight)
                is_fail_conf = True
            if is_success and default_success_weight is not None:
                conf_success_weight = float(default_success_weight)
                is_success_conf = True

        # Apply mechanic to each occurrence
        for entry in mech.get("mechanicsData", []) or []:
            actor_name = entry.get("actor")
            if actor_name not in result:
                # Could be an NPC / non-player
                continue

            count = 1.0  # each occurrence counts as 1
            if is_fail_conf:
                w = float(conf_fail_weight)
                result[actor_name]["fails"].append(label)
                result[actor_name]["fail_score"] += w * count

            if is_success_conf:
                w = float(conf_success_weight)
                result[actor_name]["success"].append(label)
                result[actor_name]["success_score"] += w * count

    return result


def mechanic_fail_counts(mechanic_summary: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    """name -> number of failed mechanics (unweighted count)."""
    return {name: len(data.get("fails", [])) for name, data in mechanic_summary.items()}


def mechanic_success_scores(mechanic_summary: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """name -> weighted success mechanic score."""
    return {name: float(data.get("success_score", 0.0)) for name, data in mechanic_summary.items()}


def mechanic_fail_scores(mechanic_summary: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """name -> weighted fail mechanic score."""
    return {name: float(data.get("fail_score", 0.0)) for name, data in mechanic_summary.items()}


# ---------------------------------------------------------------------------
# Buff map & group boon generation
# ---------------------------------------------------------------------------

def build_buff_id_map(ei_json: dict) -> Dict[int, Dict[str, str]]:
    """
    Elite Insights JSON stores buff metadata under "buffMap" with keys like "b740":

      "buffMap": {
        "b740": {
           "name": "Might",
           "classification": "Boon",
           ...
        },
        ...
      }

    This returns:
      {740: {"name": "Might", "classification": "Boon"}, ...}
    """
    buff_map: Dict[int, Dict[str, str]] = {}
    raw = ei_json.get("buffMap", {}) or {}

    for key, val in raw.items():
        if (
            isinstance(key, str)
            and key.startswith("b")
            and key[1:].isdigit()
            and isinstance(val, dict)
        ):
            buff_id = int(key[1:])
            buff_map[buff_id] = {
                "name": val.get("name"),
                "classification": val.get("classification"),
            }

    return buff_map


def compute_group_boon_generation(
    ei_json: dict,
    phase_index: int = 0,
    important_boons: Optional[Set[str]] = None,
) -> Dict[str, Dict[str, float]]:
    """
    Per-player group boon generation based on players[*].groupBuffs.

    Returns:
    {
      "Player Name": {
        "Might":  12.3,  # seconds generated in given phase
        "Quickness": 5.6,
        "Alacrity": 27.8,
        ...
      },
      ...
    }
    """
    if important_boons is None:
        important_boons = IMPORTANT_BOONS

    buff_map = build_buff_id_map(ei_json)
    result: Dict[str, Dict[str, float]] = {}

    for p in ei_json.get("players", []) or []:
        name = _safe_get_player_name(p)
        per_boon: Dict[str, float] = {}

        for gb in p.get("groupBuffs", []) or []:
            buff_id = gb.get("id")
            if buff_id is None:
                continue

            info = buff_map.get(buff_id)
            if not info:
                continue

            boon_name = info.get("name")
            classification = info.get("classification")
            if classification != "Boon":
                continue
            if important_boons and boon_name not in important_boons:
                continue

            buff_data = gb.get("buffData", []) or []
            if not buff_data:
                continue

            idx = phase_index if phase_index < len(buff_data) else 0
            phase_entry = buff_data[idx] or {}
            gen = float(phase_entry.get("generation", 0.0))
            if gen <= 0.0:
                continue

            per_boon[boon_name] = per_boon.get(boon_name, 0.0) + gen

        result[name] = per_boon

    return result


# ---------------------------------------------------------------------------
# Support metrics (healing + boons + mechanics)
# ---------------------------------------------------------------------------

def compute_support_metrics(
    ei_json: dict,
    phase_index: int = 0,
    mechanic_summary: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Per-player support metrics used for support score & MVP.

    {
      "Player Name": {
         "healing": float,
         "boon_score": float,          # weighted sum of generated boons
         "boons_generated": {          # per-boon group generation (seconds)
             "Might": 12.3,
             "Quickness": 5.6,
             ...
         },
         "mech_success": float,        # weighted mechanics done
         "breakbar": float,            # breakbar damage
      }
    }

    NOTE: On sample logs there may be no extHealingStats/healingStats,
    so "healing" can be 0.0 for everyone unless EI has healing data.
    """
    players = ei_json.get("players", []) or []
    if mechanic_summary is None:
        mechanic_summary = get_mechanic_summary(ei_json)

    boon_gen_per_player = compute_group_boon_generation(
        ei_json, phase_index=phase_index
    )

    metrics: Dict[str, Dict[str, Any]] = {}

    for p in players:
        name = _safe_get_player_name(p)
        ms = mechanic_summary.get(name, {})

        # --- Boons generated (per boon) ---
        boons_generated = boon_gen_per_player.get(name, {}) or {}

        # Weighted boon score
        boon_score = 0.0
        for boon_name, amount in boons_generated.items():
            weight = BOON_GENERATION_WEIGHTS.get(boon_name, 1.0)
            boon_score += amount * weight

        # --- Healing (extended stats if available) ---
        healing_val = 0.0
        healing_stats = p.get("extHealingStats") or p.get("healingStats") or []
        if healing_stats and phase_index < len(healing_stats):
            phase_heal = healing_stats[phase_index] or {}
            out_heal = (
                phase_heal.get("outgoingHealing")
                or phase_heal.get("healing")
                or 0.0
            )
            out_barrier = phase_heal.get("outgoingBarrier") or 0.0
            healing_val = float(out_heal) + float(out_barrier)

        # --- Breakbar damage from DPS stats ---
        breakbar_val = 0.0
        dps_all = p.get("dpsAll", []) or p.get("dpsTargets", [])
        if dps_all and phase_index < len(dps_all):
            stats = dps_all[phase_index] or {}
            breakbar_val = float(
                stats.get("breakbarDamage") or stats.get("BreakbarDamage") or 0.0
            )

        metrics[name] = {
            "healing": healing_val,
            "boon_score": boon_score,
            "boons_generated": boons_generated,
            "mech_success": float(ms.get("success_score", 0.0)),
            "breakbar": breakbar_val,
        }

    return metrics


# ---------------------------------------------------------------------------
# Boss damage (for MVP: % boss HP)
# ---------------------------------------------------------------------------

def compute_boss_damage(
    ei_json: dict,
    phase_index: int = 0,
    target_index: int = 0,
) -> Dict[str, float]:
    """
    Compute per-player damage to the main boss target for a given phase.

    Uses players[*].dpsTargets[target_index][phase_index]["damage"].

    Returns:
      { "Player Name": damage }
    """
    players = ei_json.get("players", []) or []
    result: Dict[str, float] = {}

    for p in players:
        name = _safe_get_player_name(p)
        dmg_val = 0.0

        dps_targets = p.get("dpsTargets", []) or []
        if target_index < len(dps_targets):
            target_phases = dps_targets[target_index] or []
            if phase_index < len(target_phases):
                stats = target_phases[phase_index] or {}
                dmg_val = float(stats.get("damage", 0.0))

        result[name] = dmg_val

    return result
