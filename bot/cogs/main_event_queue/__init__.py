from bot.cogs.main_event_queue.main_event_commnads import MainEventCommands
from bot.cogs.main_event_queue.main_event_queue_listener import MainEventQueueListener
from bot.cogs.main_event_queue.main_event_queue_listener import QueueDisplayView


async def setup(bot):
    await  bot.wait_until_ready()
    await bot.add_cog(MainEventCommands(bot=bot))
    cog = MainEventQueueListener(bot)
    await bot.add_cog(cog)
    bot.add_view(QueueDisplayView())