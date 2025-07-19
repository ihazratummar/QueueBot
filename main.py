import os

import discord
from dotenv import load_dotenv

from bot.config import Bot

load_dotenv()

token = os.getenv("DISCORD_BOT_TOKEN")

if __name__ == "__main__":
    bot = Bot(command_prefix="q!", intent=discord.Intents.all(), help_command=None)
    bot.run(token=token)
