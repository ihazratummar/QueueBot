import discord
from discord.ext import commands
from discord import app_commands

class TempCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_collection = self.bot.db.temp_collection

    @app_commands.command(name="temp_channels", description="Add a voice channel to the database (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def temp_channels(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        try:
            guild_id = interaction.guild.id
            result = await self.temp_collection.update_one(
                {"_id": guild_id},
                {"$addToSet": {"channel_ids": channel.id}},
                upsert=True
            )
            if result.upserted_id or (result.modified_count == 1 and result.matched_count == 1):
                await interaction.response.send_message(f"Successfully added voice channel: {channel.name} ({channel.id})", ephemeral=True)
            else:
                await interaction.response.send_message(f"Voice channel: {channel.name} ({channel.id}) is already in the database.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="remove_temp_channel", description="Remove a voice channel ID from the database (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_temp_channel(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        try:
            guild_id = interaction.guild.id
            result = await self.temp_collection.update_one(
                {"_id": guild_id},
                {"$pull": {"channel_ids": channel.id}}
            )
            if result.modified_count > 0:
                await interaction.response.send_message(f"Successfully removed voice channel: {channel.name} ({channel.id})", ephemeral=True)
            else:
                await interaction.response.send_message(f"Voice channel: {channel.name} ({channel.id}) was not found in the database for this guild.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="list_temp_channels", description="List all configured temporary voice channels (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_temp_channels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild_id = interaction.guild.id
            config = await self.temp_collection.find_one({"_id": guild_id})

            if not config or not config.get("channel_ids"):
                await interaction.followup.send("No temporary voice channels configured for this guild.", ephemeral=True)
                return

            channel_ids = config.get("channel_ids", [])
            message = "**Configured Temporary Voice Channels:**\n"

            if channel_ids:
                for channel_id in channel_ids:
                    channel = interaction.guild.get_channel(channel_id)
                    if channel:
                        message += f"- {channel.mention} (ID: {channel.id})\n"
                    else:
                        message += f"- Unknown Channel (ID: {channel_id}) - Channel might have been deleted.\n"
            else:
                message += "No temporary voice channels configured.\n"

            await interaction.followup.send(message, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)