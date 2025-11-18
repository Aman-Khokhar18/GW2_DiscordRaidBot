from typing import Dict, List, Tuple, Optional


def normalize(values: List[float]) -> List[float]:
    """
    Normalize a list into [0, 1] by dividing each value by the max.
    If all values are zero, returns all zeros.
    """
    if not values:
        return []
    max_v = max(values)
    if max_v <= 0:
        return [0.0 for _ in values]
    return [v / max_v for v in values]


# ---------------------------------------------------------------------------
# DEFAULT WEIGHTS (edit these here)
# ---------------------------------------------------------------------------

SUPPORT_WEIGHTS: Dict[str, float] = {
    "healing": 0.0,   # your logs currently have no healing, so 0 is fine
    "boon": 0.1,      # weighted boon generation from gw2_stats
    "mech": 0.5,      # weighted mechanic success (from mechanics_config)
    "breakbar": 0.7,  # normalized breakbar damage
}

# Mechanics contribution to MVP is now *only* via support_scores
# (which already includes mechanics through SUPPORT_WEIGHTS["mech"]).
MVP_WEIGHTS: Dict[str, float] = {
    "dps": 0.75,          # % boss HP contribution
    "support": 0.25,      # support score from compute_support_scores
    "fail_penalty": 0.4, # penalty based on weighted fail score
}


# ---------------------------------------------------------------------------
# SUPPORT SCORING
# ---------------------------------------------------------------------------

def compute_support_scores(
    players_metrics: Dict[str, Dict[str, float]],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Compute a normalized support score per player.

    players_metrics[name] should come from gw2_stats.compute_support_metrics:

      players_metrics[name] = {
          "healing": float,
          "boon_score": float,
          "mech_success": float,
          "breakbar": float,
      }
    """
    if weights is None:
        weights = SUPPORT_WEIGHTS

    names = list(players_metrics.keys())
    if not names:
        return {}

    healing_vals = [float(players_metrics[n].get("healing", 0.0)) for n in names]
    boon_vals = [float(players_metrics[n].get("boon_score", 0.0)) for n in names]
    mech_vals = [float(players_metrics[n].get("mech_success", 0.0)) for n in names]
    breakbar_vals = [float(players_metrics[n].get("breakbar", 0.0)) for n in names]

    nh = normalize(healing_vals)
    nb = normalize(boon_vals)
    nm = normalize(mech_vals)
    nc = normalize(breakbar_vals)

    scores: Dict[str, float] = {}
    for i, name in enumerate(names):
        scores[name] = (
            weights.get("healing", 0.0) * nh[i]
            + weights.get("boon", 0.0) * nb[i]
            + weights.get("mech", 0.0) * nm[i]
            + weights.get("breakbar", 0.0) * nc[i]
        )
    return scores


# ---------------------------------------------------------------------------
# MVP SCORING
# ---------------------------------------------------------------------------

def compute_mvp(
    boss_damage: Dict[str, float],
    support_scores: Dict[str, float],
    mech_success_scores: Dict[str, float],
    mech_fail_scores: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> Tuple[Optional[str], Dict[str, float]]:
    """
    Compute MVP based on:
      - % of boss HP contributed (damage / boss total health),
      - support score (which already includes mechanics),
      - weighted mechanic fails (penalty).

    boss_damage : dict
        name -> percentage of boss HP (0..1+). Caller is responsible for
        computing damage / totalHealth or fallback normalization.

    support_scores : dict
        name -> supportScore from compute_support_scores.

    mech_success_scores : dict
        name -> weighted positive mechanic score (still passed in, but
                not directly weighted here; only used if you want to
                debug or extend later).

    mech_fail_scores : dict
        name -> weighted fail mechanic score (used for penalty).
    """
    if weights is None:
        weights = MVP_WEIGHTS

    if not boss_damage:
        return None, {}

    names = list(boss_damage.keys())

    # damage share already prepared by caller
    damage_share: Dict[str, float] = {
        name: float(boss_damage.get(name, 0.0)) for name in names
    }

    # We still normalize success in case you want to inspect/extend,
    # but we don't add it again to MVP because it's already in support.
    succ_vals = [float(mech_success_scores.get(n, 0.0)) for n in names]
    _n_succ = normalize(succ_vals)  # not used in MVP formula now

    fail_vals = [float(mech_fail_scores.get(n, 0.0)) for n in names]
    max_fail = max(fail_vals) if fail_vals else 0.0
    if max_fail <= 0:
        max_fail = 1.0
    fail_norm: Dict[str, float] = {
        name: float(mech_fail_scores.get(name, 0.0)) / max_fail for name in names
    }

    mvp_scores: Dict[str, float] = {}
    for name in names:
        dmg_component = damage_share[name]
        support_component = float(support_scores.get(name, 0.0))
        fail_component = fail_norm[name]

        mvp = (
            weights.get("dps", 0.0) * dmg_component
            + weights.get("support", 0.0) * support_component
            - weights.get("fail_penalty", 0.0) * fail_component
        )
        mvp_scores[name] = mvp

    mvp_name = max(mvp_scores.items(), key=lambda kv: kv[1])[0]
    return mvp_name, mvp_scores
