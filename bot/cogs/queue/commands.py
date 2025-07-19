import discord
from discord.ext import commands
from bot.database import (
    update_config_value,
    get_config,
    get_queue,
    get_queue_embed_message_id,
    update_queue_embed_message,
    remove_from_queue,
    clear_queue,
)
from discord import app_commands
from bot.cogs.queue.queue_listner import QueueListener


class QueueCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="set_waiting_channel", description="Set the Waiting Room Voice Channel"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_waiting_channel(
        self, interaction: discord.Interaction, channel: discord.VoiceChannel
    ):
        update_config_value(interaction.guild.id, "waiting_channel_id", channel.id)
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
        update_config_value(interaction.guild.id, "live_channel_id", channel.id)
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
        update_config_value(interaction.guild.id, "queue_log_channel", channel.id)
        await interaction.response.send_message(
            f"📓 Log channel set to:: {channel.mention}", ephemeral=True
        )

    @app_commands.command(
        name="set_queue_display_channel",
        description="Set the public queue display channel",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_queue_display_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        update_config_value(interaction.guild.id, "queue_text_channel_id", channel.id)
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

        update_config_value(interaction.guild.id, "max_guests", number)
        await interaction.response.send_message(
            f"👥 Guest limit set to {number}.", ephemeral=True
        )

    async def update_queue_display(self, guild: discord.Guild, config: dict):
        queue_data = get_queue()
        queue_text_channel = self.bot.get_channel(config["queue_text_channel_id"])
        is_auto_queue = bool(config["auto_fill_enabled"])

        display = (
            "\n".join([f"{i+1}. <@{uid}>" for i, (uid, _) in enumerate(queue_data)])
            or "*Queue is empty*"
        )

        embed = discord.Embed(
            title="🎮 Player Queue", description=display, color=discord.Color.green()
        )
        status = "enabled ✅" if is_auto_queue else "disabled ❌"
        embed.add_field(name="Status", value=f"{status.upper()}")

        message_id = config.get("queue_embed_message_id")
        if message_id:
            try:
                msg = await queue_text_channel.fetch_message(message_id)
                await msg.edit(embed=embed)
            except discord.NotFound:
                new_msg = await queue_text_channel.send(embed=embed)
                update_queue_embed_message(guild_id=guild.id, message_id=new_msg.id)

    @app_commands.command(
        name="show_queue", description="Show the current queue manualy"
    )
    async def show_queue(self, interaction: discord.Interaction):
        await interaction.response.defer()
        config = get_config(interaction.guild.id)

        if not config:
            await interaction.response.send_message(f"⚠️ Queue is not configured.")
            return

        await self.update_queue_display(interaction.guild, config=config)
        await interaction.followup.send(f"✅ Queue display updated.")

    @app_commands.command(name="reset_queue", description="Clear the entire queue")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_queue(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        config = get_config(interaction.guild.id)

        if not config:
            await interaction.response.send_message(f"⚠️ Queue is not configured")
            return

        clear_queue()
        await self.update_queue_display(guild=interaction.guild, config=config)
        await interaction.followup.send(f"🗑️ Queue has been reset.")

    @app_commands.command(
        name="skip_queue", description="Skip the next user in the waiting queue"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def skip_queue(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        config = get_config(interaction.guild.id)

        if not config:
            await interaction.response.send_message(f"⚠️ Queue is not configured")
            return

        queue_data = get_queue()

        if not queue_data:
            await interaction.response.send_message(f"ℹ️ No non is in the waiitng room.")
            return

        user_id, username = queue_data[0]

        member = interaction.guild.get_member(user_id)

        if (
            member
            and member.voice
            and member.voice.channel.id == config["waiting_channel_id"]
        ):
            try:
                await member.move_to(None)
            except discord.Forbidden:
                await interaction.response.send_message(
                    f"❌ Missing permission to move the user."
                )
                return

        remove_from_queue(user_id=user_id)

        await interaction.followup.send(
            f"⛔ Skipepd <@{user_id}> form the waiting queue."
        )

        listner = QueueListener(self.bot)

        await listner.move_next_user(guild=interaction.guild, config=config)
        await listner.update_queue_display(interaction.guild, config=config)

    @app_commands.command(
        name="toggle_queue_auto", description="Enable or disable automatic queue"
    )
    @app_commands.checks.has_permissions()
    async def toggle_queue_auto(self, interaction: discord.Interaction):
        config = get_config(interaction.guild.id)

        if not config:
            await interaction.response.send_message(
                "⚠️ Queue not configured.", ephemeral=True
            )
            return

        current = bool(config.get("auto_fill_enabled", 1))
        new_value = 0 if current else 1
        update_config_value(interaction.guild.id, "auto_fill_enabled", new_value)

        # ✅ Refresh config from DB
        new_config = get_config(interaction.guild.id)

        status = "disabled ❌" if current else "enabled ✅"
        await interaction.response.send_message(
            f"Auto queue filling has been **{status}**.", ephemeral=True
        )

        listner = QueueListener(self.bot)
        await self.update_queue_display(interaction.guild, config=new_config)

        if not current:  # Now enabled, start processing
            await listner.move_next_user(guild=interaction.guild, config=new_config)

