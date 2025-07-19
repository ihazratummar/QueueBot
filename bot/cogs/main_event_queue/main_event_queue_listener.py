import discord
from discord.ext import commands
import datetime


class QueueDisplayView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = None  # Make the view persistent

    async def add_buttons(self, guild: discord.Guild, current_queue: list):
        self.clear_items() # Clear existing buttons
        for entry in current_queue:
            user = guild.get_member(entry["user_id"])
            if user:
                button = discord.ui.Button(
                    label=f"Move {user.display_name}",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"move_user_{user.id}"
                )
                button.callback = self.move_user_callback
                self.add_item(button)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

    async def move_user_callback(self, interaction: discord.Interaction):
        # This method will now handle the logic, getting the cog from the bot
        cog = interaction.client.get_cog("MainEventQueueListener")
        if not cog:
            await interaction.response.send_message("Error: Queue listener not found.", ephemeral=True)
            return

        try:
            user_id = int(interaction.data["custom_id"].split("_")[-1])
        except (KeyError, ValueError):
            await interaction.response.send_message("Invalid button.", ephemeral=True)
            return

        guild = interaction.guild
        config = await cog.main_config_collection.find_one({"_id": guild.id})
        if not config:
            await interaction.response.send_message("Config not found.", ephemeral=True)
            return

        live_event_channel = guild.get_channel(int(config.get("live_event_channel_id", 0)))
        log_channel = guild.get_channel(int(config.get("log_channel_id", 0)))

        if not isinstance(live_event_channel, discord.VoiceChannel):
            await interaction.response.send_message("Live channel not set correctly.", ephemeral=True)
            return

        if interaction.user.id != 475357995367137282:# guild.owner_id:
            await interaction.response.send_message("Only the owner can move users.", ephemeral=True)
            return

        if not interaction.user.voice or interaction.user.voice.channel.id != live_event_channel.id:
            await interaction.response.send_message("You must be in the live event channel.", ephemeral=True)
            return

        member_to_move = guild.get_member(user_id)
        if not member_to_move or not member_to_move.voice:
            await interaction.response.send_message("User is not in a voice channel.", ephemeral=True)
            return

        try:
            await member_to_move.move_to(live_event_channel)
            await interaction.response.send_message(f"✅ Moved {member_to_move.mention} to {live_event_channel.mention}.", ephemeral=True)

            current_queue = config.get("current_queue", [])
            updated_queue = [entry for entry in current_queue if entry["user_id"] != user_id]
            await cog.main_config_collection.update_one(
                {"_id": guild.id},
                {"$set": {"current_queue": updated_queue}}
            )

            await cog.update_queue_display(guild)

            if log_channel:
                await log_channel.send(f"{member_to_move.mention} was moved to {live_event_channel.mention} by {interaction.user.mention}.")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to move members.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)


class MainEventQueueListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.main_config_collection = bot.db.main_config_collection

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        guild = member.guild
        config = await self.main_config_collection.find_one({"_id": guild.id})
        if not config:
            return

        queue_channel_ids = [int(cid.get("$numberLong", 0)) if isinstance(cid, dict) else int(cid) for cid in config.get("queue_channels_ids", [])]
        queue_display_channel_id = int(config.get("queue_display_channel_id", 0))
        log_channel_id = int(config.get("log_channel_id", 0))

        if after.channel and after.channel.id in queue_channel_ids and (not before.channel or before.channel.id not in queue_channel_ids):
            if member.id == 475357995367137282:# guild.owner_id:
                return

            current_queue = config.get("current_queue", [])
            if not any(entry["user_id"] == member.id for entry in current_queue):
                current_queue.append({
                    "user_id": member.id,
                    "join_time": datetime.datetime.utcnow().isoformat()
                })
                await self.main_config_collection.update_one(
                    {"_id": guild.id},
                    {"$set": {"current_queue": current_queue}},
                    upsert=True
                )
                await self.update_queue_display(guild)

                if log_channel_id:
                    log_channel = guild.get_channel(log_channel_id)
                    if log_channel:
                        await log_channel.send(f"{member.mention} joined the queue.")

    async def update_queue_display(self, guild: discord.Guild):
        config = await self.main_config_collection.find_one({"_id": guild.id})
        queue_display_channel_id = int(config.get("queue_display_channel_id", 0))
        queue_display_channel = guild.get_channel(queue_display_channel_id)
        if not queue_display_channel or not isinstance(queue_display_channel, discord.TextChannel):
            return

        current_queue = config.get("current_queue", [])
        current_queue.sort(key=lambda x: x["join_time"])

        embed = discord.Embed(title="🎧 Current Queue", color=discord.Color.blurple())
        if current_queue:
            lines = []
            for i, entry in enumerate(current_queue):
                user = guild.get_member(entry["user_id"])
                if user:
                    join_time = datetime.datetime.fromisoformat(entry["join_time"]).strftime('%H:%M:%S')
                    lines.append(f"{i+1}. {user.mention} (Joined at `{join_time}`)")
            embed.description = "\n".join(lines)
        else:
            embed.description = "The queue is currently empty."

        view = QueueDisplayView()
        await view.add_buttons(guild, current_queue)

        message_id = config.get("queue_message_id")
        try:
            if message_id:
                message = await queue_display_channel.fetch_message(int(message_id))
                await message.edit(embed=embed, view=view)
            else:
                message = await queue_display_channel.send(embed=embed, view=view)
                await self.main_config_collection.update_one(
                    {"_id": guild.id},
                    {"$set": {"queue_message_id": message.id}}
                )
        except discord.NotFound:
            message = await queue_display_channel.send(embed=embed, view=view)
            await self.main_config_collection.update_one(
                {"_id": guild.id},
                {"$set": {"queue_message_id": message.id}}
            )
        except Exception as e:
            print(f"Error updating queue display for guild {guild.id}: {e}")
