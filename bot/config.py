import discord
from discord.ext import commands


extentions = ["bot.cogs.queue"]


class Bot(commands.Bot):
    def __init__(self, command_prefix: str, intent: discord.Intents, **kwargs):
        super().__init__(command_prefix=command_prefix, intents=intent, **kwargs)

    async def on_ready(self):
        for extention in extentions:
            try:
                await self.load_extension(extention)
            except Exception as e:
                print(f"Failed to load extension: {e}")

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands")

        print("Bot is ready....")
