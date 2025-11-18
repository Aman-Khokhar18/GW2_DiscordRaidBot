from typing import Dict

SUCCESS_MECHANICS_CONFIG: Dict[str, Dict[str, float]] = {
    "Vale Guardian":{
    "Attune B": 0.1,
    "Attune G": 0.1,
    "Attune R": 0.3,
    "Res": 0.5,
    }, 

    "Gorseval the Multifarious": {
        "Res": 0.3,
    },

    "Sabetha the Saboteur": {
        "Res": 1,
        "Launched": 1.5,
        "Sap Bomb": 0.5,
        "Timed Bomb": 0.25,
        "Kick Bomb": 0.25,
        "TimeB Kill": 0.5,
    },

    "Slothasor": {
        "Slub": 3,
        "Poison": 0.8,
        "Res": 1.5,
        "Fixate": 0.5,
    },

    "Matthias Gabrel": {
        "Res": 2,
        "Rmv.Sh.Stck": 0.05,
        "Corruption": 0.5,
        "Sacrifice": 3,
        "Well": 0.75,
        "Bombs": 0.1,
    },

    "Keep Construct": {
        "GW.Orb": 0.1,
        "GR.Orb": 0.1,
        "Res": 1,
    },

    "Xera": {
        "Button1": 0.1,
        "Button2": 0.1,
        "Button3": 0.1,
        "TP Out": 1.5,
        "TP Back": 1,
        "Shield": 0.5,
        "Res": 0.5,
    },

    "Cairn": {
        "Agony 25": 0.8,
        "Agony 50": 1,
        "Agony 75": 0.5,
        "Res": 1.5,
        "Stab.Green": 0.1,
    },

    "Mursaat Overseer": {
        "Res": 1,
        "Dispel (SAK)": 0.8,
        "Protect (SAK)": 0.5,
        "Claim (SAK)": 0.8,
    },

    "Samarog": {
        "Res": 0.5,
        "S.Fix": 0.1,
        "B.Gr": 0.6,
        "S.Gr": 0.2,
        "Gr.Fl": 0.6,        
    },

    "Deimos": {
        "Res": 0.8,
        "Green": 0.7,
        "TP": 0.3,
    },

    "Soulless Horror": {
        "Fixate": 0.2,
        "Necrosis": 0.5,
        "Res": 0.8,
        "Immob.Golem": 0.3,
    },

    "Dhumm": {
        "Res": 1.2,
        "Bomb": 0.5,
        "Shackles": 0.3,
        "Mess Fix": 0.3,
        "Orb CD": 0.8,
    },

    "Conjured Amalgamate": {
        "Res": 0.5,
        "Sword.Cst": 0.1,
        "Shield.Cst": 0.2,
        "Sword.C": 0.1,
        "Shield.C": 0.2,
    },

    "Twin Largos": {
        "Res": 1,
    },

    "Qadim": {
        "Res": 1,
        "Lamp": 0.8,
    },

    "Cardinal Adina": {
        "Res": 0.8,
        "Slctd.Pillar": 0.5,
    },

    "Cardinal Sabir": {
        "Res": 1,
    },

    "Qadim the Peerless": {
        "E.Aff": 0.5,
        "Res": 0.8,
    },

    "_default": {
        "__success_default__": 1.0,
    },
}

FAILED_MECHANICS_CONFIG: Dict[str, Dict[str, float]] = {
    "Vale Guardian": {
        "Boss TP": 1,
        "Orbs": 0.05,
        "Dead": 3,
        "Downed": 1.5,
        "Floor B": 0.05,
        "Floor G": 0.05,
        "Floor R": 0.05,
        "Seeker": 0.5,
    },

    "Gorseval the Multifarious": {
        "Egg": 1,
        "Kick": 0.1,
        "Knck.Pll": 0.25,
        "Dead": 3,
        "Downed": 0.5,
    },

    "Sabetha the Saboteur": {
        "Cannon": 0.5,
        "Kick": 0.25,
        "Karde Flame": 0.05,
        "Flak": 0.1,
        "Dead": 3,
        "Downed": 1,
        "Knck.Pll": 0.01,
    },

    "Slothasor": {
        "Breath": 0.25,
        "Tantrum": 1.5,
        "Downed": 1.5,
        "Dead": 3,
        "Floor": 0.01,
        "Poison dmg": 0.15,
        "Shake": 0.5,
    },

    "Matthias Gabrel": {
        "Refl.Jump Shards": 1,
        "Tornado": 1.5,
        "Storm": 0.5,
        "KD": 0.5,
        "Icy KD": 3,
        "Well dmg": 0.1,
        "Corr. dmg": 0.05,
        "Spirit": 1,
        "Downed": 3,
        "Dead": 3,
    },

    "Keep Construct": {
        "Pizza": 0.25,
        "Debris": 0.1,
        "BW.Orb": 0.3,
        "BR.Orb": 0.3,
        "Bomb": 0.2,
        "Downed": 3,
        "Dead": 3,
    },

    "Xera": {
        "Flt": 2,
        "Orb": 2,
        "Orb Aoe": 0.2,
        "Stacks": 0.05,
        "Downed": 1.5,
        "Dead": 4,
    },

    "Cairn": {
        "KB": 0.5,
        "Port": 0.8,
        "Dead": 3,
        "Downed": 2,
        "Flt": 0.8,
        "Green": 0.5,
    },

    "Mursaat Overseer": {
        "Jade Expl": 0.3,
        "Downed": 2,
        "Dead": 3,
    },

    "Samarog": {
        "Dead": 0.1,
        "Downed": 1.5,
        "Knck.Pll": 0.1,
        "Slam": 0.2,
        "Wall": 0.2,
        "Stun": 0.2,
        "Gr.Fl": 1,
    },

    "Deimos": {
        "Dead": 2,
        "Downed": 1.5,
        "Lnch": 0.5,
        "Oil": 0.5,
        "Pizza": 0.5,
    },

    "Soulless Horror": {
        "Dead": 3,
        "Downed": 2,
        "Slice2": 0.6,
        "8Slice": 0.3,
        "Golem": 0.5,
        "Donut Out": 0.3,
        "Donut In": 0.1,
        "Scythe": 0.4,
    },

    "Dhuum": {
        "Golem": 0.5,
        "Crack": 0.8,
        "Mark": 0.3,
        "Suck dmg": 0.6,
        "Bomb Trig": 0.1,
        "Enf.Swipe": 1,
        "Dip": 1,
        "Dead": 3,
        "Downed": 2,
        "Shackles Dmg": 0.5,
    },

    "Conjured Amalgamate": {
        "Dead": 3.0,
        "Downed": 2,
        "Junk": 0.5,
    },

    "Twin Largos": {
        "Float": 0.5,
        "Charge": 0.3,
        "Pool": 0.5,
        "Debuff": 0.2,
        "Poison": 0.2,
        "Wave": 0.5,
        "Tornado": 0.1,
        "Steal": 1,
        "Downed": 2,
        "Dead": 3,
    },

    "Qadim": {
        "F.Dance": 0.2,
        "Q.Hitbox": 0.2,
        "KB": 0.5,
        "Q.Wave": 0.5,
        "Mace": 0.5,
        "Inf.": 0.3,
        "D.Wave": 0.5,
        "D.Pizza": 0.5,
        "Slash": 0.5,
        "W.Pizza": 0.7,
        "W.Breath": 0.5,
        "Port": 0.5,
        "Claw": 0.2,
        "Dead": 3,
        "Downed": 2,
    },

    "Cardinal Adina": {
        "Dead": 3,
        "Downed": 2,
        "Knck.Dwn": 0.5,
        "Knck.Pll": 0.4,
        "R.Blind": 0.8,
        "Eye": 0.5,
        "Mines": 1,
    },

    "Cardinal Sabir": {
        "Dead": 3,
        "Downed": 2,
        "Shockwave": 1,
    },

    "Qadim the Peerless": {
        "Dead": 3,
        "Downed": 1.8,
        "Lnch": 0.6,
        "Magma.F": 0.3,
        "P.Rect": 0.02,
        "S.Lght.H": 0.2,
        "A.Prj.H": 0.6,
        "Rush.H": 0.5,
    },

    "_default": {
        "__fail_default__": 1.0,
    },
}


def get_success_rules_for_boss(boss_name: str) -> Dict[str, float]:
    if boss_name in SUCCESS_MECHANICS_CONFIG:
        return SUCCESS_MECHANICS_CONFIG[boss_name]
    return SUCCESS_MECHANICS_CONFIG.get("_default", {})


def get_fail_rules_for_boss(boss_name: str) -> Dict[str, float]:
    if boss_name in FAILED_MECHANICS_CONFIG:
        return FAILED_MECHANICS_CONFIG[boss_name]
    return FAILED_MECHANICS_CONFIG.get("_default", {})
