import discord
from discord.ext import commands
from discord import app_commands
from bot.cogs.twitch_ward_queue.queue_listner import QueueListener


class QueueCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.twitch_ward_config_collection = self.bot.db.twitch_ward_config_collection

    @app_commands.command(
        name="set_waiting_channel", description="Set the Waiting Room Voice Channel"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_waiting_channel(
        self, interaction: discord.Interaction, channel: discord.VoiceChannel
    ):
        await self.twitch_ward_config_collection.update_one(
            {"_id": interaction.guild.id},
            {"$set": {"waiting_channel_id": channel.id}},
            upsert=True
        )
        await interaction.response.send_message(
            f"✅ Waiting Room set to: {channel.mention}", ephemeral=True
        )

    @app_commands.command(
        name="set_live_channel", description="Set the live voice channel"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_live_channel(
        self, interaction: discord.Interaction, channel: discord.VoiceChannel
    ):
        await self.twitch_ward_config_collection.update_one(
            {"_id": interaction.guild.id},
            {"$set": {"live_channel_id": channel.id}},
            upsert=True
        )
        await interaction.response.send_message(
            f"✅ Live Room set to: {channel.mention}", ephemeral=True
        )

    @app_commands.command(
        name="set_queue_log_channel", description="Sett  he Queue Log text channel"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        await self.twitch_ward_config_collection.update_one(
            {"_id": interaction.guild.id},
            {"$set": {"queue_log_channel": channel.id}},
            upsert=True
        )
        await interaction.response.send_message(
            f"📓 Log channel set to:: {channel.mention}", ephemeral=True
        )

    @app_commands.command(
        name="set_queue_display_channel",
        description="Set the public twitch_ward_queue display channel",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_queue_display_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        await self.twitch_ward_config_collection.update_one(
            {"_id": interaction.guild.id},
            {"$set": {"queue_text_channel_id": channel.id}},
            upsert=True
        )
        await interaction.response.send_message(
            f"📋 Queue display channel set to: {channel.mention}", ephemeral=True
        )

    @app_commands.command(
        name="set_guests_limit",
        description="Set the max number of guests (excluding owner)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_guest_limit(self, interaction: discord.Interaction, number: int):
        if number < 1 or number > 10:
            await interaction.response.send_message(
                f"❌ Please provide a number between 1 and 10.", ephemeral=True
            )
            return

        await self.twitch_ward_config_collection.update_one(
            {"_id": interaction.guild.id},
            {"$set": {"max_guests": number}},
            upsert=True
        )
        await interaction.response.send_message(
            f"👥 Guest limit set to {number}.", ephemeral=True
        )

    @app_commands.command(
        name="show_queue", description="Show the current twitch_ward_queue manualy"
    )
    async def show_queue(self, interaction: discord.Interaction):
        await interaction.response.defer()
        config = await self.twitch_ward_config_collection.find_one({"_id": interaction.guild.id})

        if not config:
            await interaction.response.send_message(f"⚠️ Queue is not configured.")
            return

        listner = QueueListener(self.bot)
        await listner.update_queue_display(interaction.guild, config=config)

        # await self.update_queue_display(interaction.guild, config=config)
        await interaction.followup.send(f"✅ Queue display updated.")

    @app_commands.command(name="reset_queue", description="Clear the entire twitch_ward_queue")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_queue(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        config = await self.twitch_ward_config_collection.find_one({"_id": interaction.guild.id})

        if not config:
            await interaction.response.send_message(f"⚠️ Queue is not configured")
            return

        await self.twitch_ward_config_collection.update_one(
            {"_id": interaction.guild.id},
            {"$set": {"twitch_ward_queue": []}}
        )
        listner = QueueListener(self.bot)
        await listner.update_queue_display(interaction.guild, config=config)
        await interaction.followup.send(f"🗑️ Queue has been reset.")

    @app_commands.command(
        name="skip_queue", description="Skip the next user in the waiting twitch_ward_queue"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def skip_queue(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        config = await self.twitch_ward_config_collection.find_one({"_id": interaction.guild.id})

        if not config:
            await interaction.followup.send(f"⚠️ Queue is not configured")
            return

        queue_data = config.get("twitch_ward_queue", [])

        if not queue_data:
            await interaction.followup.send(f"ℹ️ No one is in the waiting room.")
            return

        first_user_entry = queue_data[0]

        # ✅ FIXED: use int directly
        user_id = int(first_user_entry["user_id"])
        username = first_user_entry["name"]

        member = interaction.guild.get_member(user_id)

        if (
                member
                and member.voice
                and member.voice.channel
                and member.voice.channel.id == config["waiting_channel_id"]
        ):
            try:
                await member.move_to(None)
            except discord.Forbidden:
                await interaction.followup.send(
                    f"❌ Missing permission to move the user."
                )
                return

        # ✅ FIXED: match by int, not $numberLong
        await self.twitch_ward_config_collection.update_one(
            {"_id": interaction.guild.id},
            {"$pull": {"twitch_ward_queue": {"user_id": user_id}}}
        )

        # Refresh config after update
        new_config = await self.twitch_ward_config_collection.find_one({"_id": interaction.guild.id})

        await interaction.followup.send(
            f"⛔ Skipped <@{user_id}> from the waiting twitch_ward_queue."
        )

        listner = QueueListener(self.bot)
        await listner.move_next_user(guild=interaction.guild, config=new_config)
        await listner.update_queue_display(interaction.guild, config=new_config)

    @app_commands.command(
        name="toggle_queue_auto", description="Enable or disable automatic twitch_ward_queue"
    )
    @app_commands.checks.has_permissions()
    async def toggle_queue_auto(self, interaction: discord.Interaction):
        config = await self.twitch_ward_config_collection.find_one({"_id": interaction.guild.id})

        if not config:
            await interaction.response.send_message(
                "⚠️ Queue not configured.", ephemeral=True
            )
            return

        await  interaction.response.defer(ephemeral=True, thinking= True)

        current = config.get("auto_fill_enabled", False) # Default to False if not set
        new_value = not current
        await self.twitch_ward_config_collection.update_one(
            {"_id": interaction.guild.id},
            {"$set": {"auto_fill_enabled": new_value}},
            upsert=True
        )

        # ✅ Refresh config from DB
        new_config = await self.twitch_ward_config_collection.find_one({"_id": interaction.guild.id})

        status = "disabled ❌" if not new_config.get("auto_fill_enabled", False) else "enabled ✅"


        listner = QueueListener(self.bot)
        await listner.update_queue_display(interaction.guild, config=new_config)

        if new_value:  # Now enabled, start processing
            await listner.move_next_user(guild=interaction.guild, config=new_config)

        await interaction.followup.send(
            f"Auto twitch_ward_queue filling has been **{status}**.", ephemeral=True
        )

    @app_commands.command(
        name="twitch_ward", description="Display all configured Twitch Ward channels"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def twitch_ward(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        config = await self.twitch_ward_config_collection.find_one({"_id": interaction.guild.id})

        if not config:
            await interaction.followup.send("⚠️ Twitch Ward is not configured for this server.")
            return

        waiting_channel = self.bot.get_channel(config.get("waiting_channel_id"))
        live_channel = self.bot.get_channel(config.get("live_channel_id"))
        queue_log_channel = self.bot.get_channel(config.get("queue_log_channel"))
        queue_display_channel = self.bot.get_channel(config.get("queue_text_channel_id"))

        description = ""
        description += f"**Waiting Room:** {waiting_channel.mention if waiting_channel else 'Not set'}\n"
        description += f"**Live Channel:** {live_channel.mention if live_channel else 'Not set'}\n"
        description += f"**Queue Log Channel:** {queue_log_channel.mention if queue_log_channel else 'Not set'}\n"
        description += f"**Queue Display Channel:** {queue_display_channel.mention if queue_display_channel else 'Not set'}\n"

        embed = discord.Embed(
            title="Twitch Ward Configuration",
            description=description,
            color=discord.Color.blue()
        )

        await interaction.followup.send(embed=embed)

