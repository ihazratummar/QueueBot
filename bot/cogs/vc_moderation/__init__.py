from bot.cogs.vc_moderation.vc_moderation_cog import VCModerationCog
from bot.cogs.vc_moderation.moderation_commands import ModerationCommands


async def setup(bot):
    await  bot.add_cog(VCModerationCog(bot = bot))
    await  bot.add_cog(ModerationCommands(bot = bot))