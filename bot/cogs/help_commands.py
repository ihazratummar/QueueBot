import discord
from discord.ext import commands
from discord import app_commands

class HelpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Displays all available slash commands.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        embed = discord.Embed(
            title="Bot Slash Commands",
            description="Here are all the available slash commands:",
            color=discord.Color.blue()
        )

        command_list = []

        for command in sorted(self.bot.tree.walk_commands(), key=lambda c: c.name):
            if command.guild_only and not interaction.guild:
                continue  # skip guild-only commands outside of guilds
            command_list.append(f"**/{command.name}**: {command.description or 'No description'}")

        embed.description = "\n".join(command_list) or "No commands available."

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))
