import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!")
    TOP_N_DPS: int = 10
    PHASE_INDEX: int = 0


if not Config.DISCORD_BOT_TOKEN:
    print(
        "[WARN] DISCORD_BOT_TOKEN is not set. "
        "Set it in environment or .env before running the bot."
    )
