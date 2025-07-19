from bot.cogs.temp_channels.temp_commands import TempCommands
from bot.cogs.temp_channels.temp_channel_builder import TempChannelBuilder



async def setup(bot):
    await  bot.wait_until_ready()
    await bot.add_cog(TempCommands(bot=bot))
    await bot.add_cog(TempChannelBuilder(bot=bot))