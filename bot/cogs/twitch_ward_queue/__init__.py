from bot.cogs.twitch_ward_queue.commands import QueueCommands
from bot.cogs.twitch_ward_queue.queue_listner import QueueListener


async def setup(bot):
    await bot.add_cog(QueueCommands(bot=bot))
    await bot.add_cog(QueueListener(bot=bot))
