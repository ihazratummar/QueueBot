import discord
from discord.ext import commands
from discord import app_commands

class MainEventCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.main_config_collection = self.bot.db.main_config_collection

    @app_commands.command(name="main_event_live_channel", description="Set the voice channel for live events.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def main_event_live_channel(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """
        Sets the voice channel where live events will be broadcast.
        """
        try:
            await self.main_config_collection.update_one(
                {"_id": interaction.guild.id},
                {"$set": {"live_event_channel_id": channel.id}},
                upsert=True
            )
            await interaction.response.send_message(f"Live event channel set to {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="main_event_queue_channels", description="Add a voice channel to the queue channels.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def main_event_queue_channels(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """
        Adds a voice channel to the list of queue channels.
        """
        try:
            await self.main_config_collection.update_one(
                {"_id": interaction.guild.id},
                {"$addToSet": {"queue_channels_ids": channel.id}},
                upsert=True
            )
            await interaction.response.send_message(f"Added {channel.mention} to queue channels.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="main_event_remove_queue_channel", description="Remove a voice channel from the queue channels.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def main_event_remove_queue_channel(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """
        Removes a voice channel from the list of queue channels.
        """
        try:
            await self.main_config_collection.update_one(
                {"_id": interaction.guild.id},
                {"$pull": {"queue_channels_ids": channel.id}}
            )
            await interaction.response.send_message(f"Removed {channel.mention} from queue channels.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="main_event_queue_display_channel", description="Set the text channel for displaying the queue.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def main_event_queue_display_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Sets the text channel where the queue will be displayed.
        """
        try:
            await self.main_config_collection.update_one(
                {"_id": interaction.guild.id},
                {"$set": {"queue_display_channel_id": channel.id}},
                upsert=True
            )
            await interaction.response.send_message(f"Queue display channel set to {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="main_event_log_channel", description="Set the text channel for logging events.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def main_event_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Sets the text channel where event logs will be sent.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.main_config_collection.update_one(
                {"_id": interaction.guild.id},
                {"$set": {"log_channel_id": channel.id}},
                upsert=True
            )
            await interaction.followup.send(f"Log channel set to {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="main_event_clear_queue", description="Clears the current queue and updates the display.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def main_event_clear_queue(self, interaction: discord.Interaction):
        """
        Clears the current queue and updates the queue display message.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            # Clear the current_queue in the database
            await self.main_config_collection.update_one(
                {"_id": interaction.guild.id},
                {"$set": {"current_queue": []}}
            )

            # Get the QueueListener cog to update the display
            queue_listener_cog = self.bot.get_cog("MainEventQueueListener")
            if queue_listener_cog:
                await queue_listener_cog.update_queue_display(interaction.guild)
                await interaction.followup.send("Queue cleared and display updated.", ephemeral=True)
            else:
                await interaction.followup.send("Error: Queue listener cog not found.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="main_event_skip_queue", description="Skips the first member in the queue.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def main_event_skip_queue(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            config = await self.main_config_collection.find_one({"_id": interaction.guild.id})
            queue = config.get("current_queue", [])

            if not queue:
                await interaction.followup.send("The queue is already empty.", ephemeral=True)
                return

            queue.pop(0)

            await self.main_config_collection.update_one(
                {"_id": interaction.guild.id},
                {"$set": {"current_queue": queue}}
            )

            queue_listener_cog = self.bot.get_cog("MainEventQueueListener")
            if queue_listener_cog:
                await queue_listener_cog.update_queue_display(interaction.guild)
                await interaction.followup.send("Skipped the first member and updated the display.", ephemeral=True)
            else:
                await interaction.followup.send("Error: Queue listener cog not found.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="main_event_remove_queue", description="Removes a specific member from the queue.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def main_event_remove_queue(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            config = await self.main_config_collection.find_one({"_id": interaction.guild.id})
            queue = config.get("current_queue", [])

            member_id = member.id

            # Find the queue entry
            updated_queue = [entry for entry in queue if entry["user_id"] != member_id]

            if len(updated_queue) == len(queue):
                await interaction.followup.send(f"{member.mention} is not in the queue.", ephemeral=True)
                return

            # Save updated queue
            await self.main_config_collection.update_one(
                {"_id": interaction.guild.id},
                {"$set": {"current_queue": updated_queue}}
            )
            queue_listener_cog = self.bot.get_cog("MainEventQueueListener")
            if queue_listener_cog:
                await queue_listener_cog.update_queue_display(interaction.guild)
            await interaction.followup.send(f"{member.mention} has been removed from the queue.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error removing user from queue: {e}", ephemeral=True)

