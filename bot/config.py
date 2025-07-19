import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")

mongo_client = AsyncIOMotorClient(mongo_uri)

extensions = [
    "bot.cogs.twitch_ward_queue",
    "bot.cogs.main_event_queue",
]


class Bot(commands.Bot):
    def __init__(self, command_prefix: str, intent: discord.Intents, **kwargs):
        super().__init__(command_prefix=command_prefix, intents=intent, **kwargs)
        self.mongo_client = mongo_client
        self.db = self.mongo_client["QueueBot"]

    async def on_ready(self):
        for extension in extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f"Failed to load extension: {e}")

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands")

        print("Bot is ready....")
