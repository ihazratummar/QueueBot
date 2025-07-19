import os

import discord
from dotenv import load_dotenv

from bot.config import Bot
from bot.database import setup_database

load_dotenv()

token = os.getenv("DISCORD_BOT_TOKEN")

if __name__ == "__main__":
    setup_database()
    bot = Bot(command_prefix="q!", intent=discord.Intents.all())
    bot.run(token=token)
