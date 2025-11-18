from typing import Dict

PROFESSION_ICONS: Dict[str, str] = {
    "Guardian": "<:Guardian:1440254106793934868>",
    "Warrior": "<:Warrior:1440254023805440000>",
    "Revenant": "<:Revenant:1440254062938423356>",
    "Engineer": "<:Engineer:1440254248464945194>",
    "Ranger": "<:Ranger:1440254213480517713>",
    "Thief": "<:Thief:1440254170887229490>",
    "Elementalist": "<:Elementalist:1440254350231605279>",
    "Mesmer": "<:Mesmer:1440254315297112086>",
    "Necromancer": "<:Necromancer:1440254282099331142>",

    "Firebrand": "<:Firebrand:1440253162291204148>",
    "Dragonhunter": "<:Dragonhunter:1440253673581318154>",
    "Willbender": "<:Willbender:1440252605455663189>",
    "Berserker": "<:Berserker:1440253569335820330>",
    "Spellbreaker": "<:Spellbreaker:1440253037783420982>",
    "Bladesworn": "<:Bladesworn:1440252523964530688>",
    "Herald": "<:Herald:1440253629197062194>",
    "Renegade": "<:Renegade:1440253089268633672>",
    "Vindicator": "<:Vindicator:1440252566956150824>",

    "Scrapper": "<:Scrapper:1440253786911277166>",
    "Holosmith": "<:Holosmith:1440253275587874950>",
    "Mechanist": "<:Mechanist:1440252771780530187>",
    "Druid": "<:Druid:1440253332076757002>",
    "Soulbeast": "<:Soulbeast:1440253235981189131>",
    "Untamed": "<:Untamed:1440252705531494440>",

    "Deadeye": "<:Deadeye:1440253196722503740>",
    "Daredevil": "<:Daredevil:1440253732485857360>",
    "Specter": "<:Specter:1440252660514164757>",

    "Tempest": "<:Tempest:1440253938711400510>",
    "Weaver": "<:Weaver:1440253496375902238>",
    "Catalyst": "<:Catalyst:1440252885660205066>",

    "Chronomancer": "<:Chronomancer:1440253882587549778>",
    "Mirage": "<:Mirage:1440253444933025802>",
    "Virtuoso": "<:Virtuoso:1440252814868877392>",

    "Reaper": "<:Reaper:1440253835732975646>",
    "Scourge": "<:Scourge:1440253384895631433>",
    "Harbinger": "<:Harbinger:1440255938798944256>",

    "Evoker": "<:Evoker:1440252476975747151>",
    "Troubadour": "<:Troubadour:1440252409942376460>",
    "Ritualist": "<:Ritualist:1440252446566907924>",
    "Amalgam": "<:Amalgam:1440252376287019031>",
    "Galeshot": "<:Galeshot:1440252347162034248>",
    "Antiquary": "<:Antiquary:1440252312596516885>",
    "Luminary": "<:Luminary:1440252282758365256>",
    "Conduit": "<:Conduit:1440252248918593639>",
    "Paragon": "<:Paragon:1440252205285245099>",
}




def icon_for_profession(prof: str) -> str:
    """
    Look up the icon for a given profession/spec string.
    """
    return PROFESSION_ICONS.get(prof, "")