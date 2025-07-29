import discord
from discord.ext import commands
from discord import app_commands
from collections import defaultdict

class HelpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Displays all available slash commands.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        embed = discord.Embed(
            title="🤖 Bot Slash Commands",
            description="Here are all the available commands, organized by category:\n\u200b",
            color=discord.Color.blue()
        )

        commands_by_cog = defaultdict(list)
        for command in sorted(self.bot.tree.walk_commands(), key=lambda c: c.name):
            if command.guild_only and not interaction.guild:
                continue

            if command.binding:  # belongs to a Cog
                category = command.binding.__class__.__name__
            else:
                category = "Miscellaneous"

            commands_by_cog[category].append(command)

        category_emojis = {
            "ModerationCommands": "🛡️",
            "QueueCommands": "🎉",
            "TempCommands": "⚙️",
            "MainEventCommands": "📌",
        }

        for category, cmds in commands_by_cog.items():
            emoji = category_emojis.get(category, "📂")
            field_value = "\n".join(
                [f"> ⚡ **/{c.name}** – {c.description or 'No description'}" for c in cmds]
            )
            embed.add_field(
                name=f"{emoji} {category}",
                value=field_value + "\n\u200b",
                inline=False
            )

        embed.set_footer(text="Use /command to run a command.")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))
