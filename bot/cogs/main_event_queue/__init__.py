from bot.cogs.main_event_queue.main_event_commnads import MainEventCommands
from bot.cogs.main_event_queue.main_event_queue_listener import MainEventQueueListener


async def setup(bot):
    await bot.add_cog(MainEventCommands(bot=bot))
    await bot.add_cog(MainEventQueueListener(bot=bot))