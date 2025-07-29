from bot.cogs.twitch_ward_queue.commands import TwitchQueueCommands
from bot.cogs.twitch_ward_queue.queue_listner import QueueListener


async def setup(bot):
    await bot.add_cog(TwitchQueueCommands(bot=bot))
    await bot.add_cog(QueueListener(bot=bot))
