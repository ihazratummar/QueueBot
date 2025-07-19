import discord
from discord.ext import commands
from discord import app_commands
import datetime

class QueueListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.main_config_collection = self.bot.db.main_config_collection

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        guild_id = member.guild.id
        config = await self.main_config_collection.find_one({"_id": guild_id})

        if not config:
            return

        queue_channels_ids = config.get("queue_channels_ids", [])
        live_event_channel_id = config.get("live_event_channel_id")
        queue_display_channel_id = config.get("queue_display_channel_id")
        log_channel_id = config.get("log_channel_id")

        # User joined a queue channel
        if after.channel and after.channel.id in queue_channels_ids and (not before.channel or before.channel.id not in queue_channels_ids):
            # Check if the member is the owner of the guild
            if member.id == member.guild.owner_id:
                return

            # Add user to queue if not already in it
            current_queue = config.get("current_queue", [])
            if not any(user["user_id"] == member.id for user in current_queue):
                current_queue.append({"user_id": member.id, "join_time": datetime.datetime.utcnow()})
                await self.main_config_collection.update_one(
                    {"_id": guild_id},
                    {"$set": {"current_queue": current_queue}},
                    upsert=True
                )
                await self.update_queue_display(member.guild, config)
                if log_channel_id:
                    log_channel = member.guild.get_channel(log_channel_id)
                    if log_channel:
                        await log_channel.send(f"{member.mention} joined the queue.")

        # User left a queue channel (but should not be removed from queue)
        # This part is handled by the requirement "leaving the queue channel wont remove the user from queue list"
        # So, no specific action needed here for removal.

    async def update_queue_display(self, guild: discord.Guild, config: dict):
        queue_display_channel_id = config.get("queue_display_channel_id")
        if not queue_display_channel_id:
            return

        queue_display_channel = guild.get_channel(queue_display_channel_id)
        if not queue_display_channel or not isinstance(queue_display_channel, discord.TextChannel):
            return

        current_queue = config.get("current_queue", [])
        current_queue.sort(key=lambda x: x["join_time"]) # Ensure time order

        embed = discord.Embed(title="Current Queue", color=discord.Color.blue())
        if current_queue:
            description = ""
            for i, user_data in enumerate(current_queue):
                member = guild.get_member(user_data["user_id"])
                if member:
                    description += f"{i+1}. {member.mention} (Joined: {user_data['join_time'].strftime('%H:%M:%S')})
"
            embed.description = description
        else:
            embed.description = "The queue is currently empty."

        view = discord.ui.View(timeout=None)
        for user_data in current_queue:
            member = guild.get_member(user_data["user_id"])
            if member:
                button = discord.ui.Button(label=f"Move {member.display_name}", style=discord.ButtonStyle.primary, custom_id=f"move_user_{member.id}")
                button.callback = self.move_user_callback
                view.add_item(button)

        queue_message_id = config.get("queue_message_id")
        try:
            if queue_message_id:
                message = await queue_display_channel.fetch_message(queue_message_id)
                await message.edit(embed=embed, view=view)
            else:
                message = await queue_display_channel.send(embed=embed, view=view)
                await self.main_config_collection.update_one(
                    {"_id": guild.id},
                    {"$set": {"queue_message_id": message.id}},
                    upsert=True
                )
        except discord.NotFound:
            message = await queue_display_channel.send(embed=embed, view=view)
            await self.main_config_collection.update_one(
                {"_id": guild.id},
                {"$set": {"queue_message_id": message.id}},
                upsert=True
            )
        except Exception as e:
            print(f"Error updating queue display: {e}")

    async def move_user_callback(self, interaction: discord.Interaction):
        custom_id_parts = interaction.custom_id.split("_")
        user_to_move_id = int(custom_id_parts[2])

        guild = interaction.guild
        config = await self.main_config_collection.find_one({"_id": guild.id})

        if not config:
            await interaction.response.send_message("Bot configuration not found.", ephemeral=True)
            return

        live_event_channel_id = config.get("live_event_channel_id")
        log_channel_id = config.get("log_channel_id")

        if not live_event_channel_id:
            await interaction.response.send_message("Live event channel is not set.", ephemeral=True)
            return

        live_event_channel = guild.get_channel(live_event_channel_id)
        if not live_event_channel or not isinstance(live_event_channel, discord.VoiceChannel):
            await interaction.response.send_message("Live event channel not found or is not a voice channel.", ephemeral=True)
            return

        # Check if the interaction user (owner) is in the live event channel
        if interaction.user.id == guild.owner_id: # Assuming owner is the one clicking the button
            if interaction.user.voice and interaction.user.voice.channel and interaction.user.voice.channel.id == live_event_channel_id:
                member_to_move = guild.get_member(user_to_move_id)
                if member_to_move and member_to_move.voice and member_to_move.voice.channel:
                    try:
                        await member_to_move.move_to(live_event_channel)
                        await interaction.response.send_message(f"Moved {member_to_move.mention} to {live_event_channel.mention}.", ephemeral=True)

                        # Remove user from queue after moving
                        current_queue = config.get("current_queue", [])
                        current_queue = [user for user in current_queue if user["user_id"] != user_to_move_id]
                        await self.main_config_collection.update_one(
                            {"_id": guild.id},
                            {"$set": {"current_queue": current_queue}}
                        )
                        await self.update_queue_display(guild, config)
                        if log_channel_id:
                            log_channel = guild.get_channel(log_channel_id)
                            if log_channel:
                                await log_channel.send(f"{member_to_move.mention} was moved to {live_event_channel.mention} by {interaction.user.mention}.")

                    except Exception as e:
                        await interaction.response.send_message(f"Failed to move user: {e}", ephemeral=True)
                else:
                    await interaction.response.send_message("User to move is not in a voice channel.", ephemeral=True)
            else:
                await interaction.response.send_message("You (the owner) must be in the live event channel to move users.", ephemeral=True)
        else:
            await interaction.response.send_message("Only the guild owner can move users from the queue.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(QueueListener(bot))
