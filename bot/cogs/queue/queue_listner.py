import discord
from discord.ext import commands
from bot.database import (
    add_to_queue,
    remove_from_queue,
    get_queue,
    get_config,
    get_queue_embed_message_id,
    update_queue_embed_message,
)


class QueueListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_owner_in_game_room(self, game_channel: discord.VoiceChannel, owner_id: int):
        return any(member.id == owner_id for member in game_channel.members)

    def get_guest_count(self, game_channel: discord.VoiceChannel, owner_id: int):
        return len([m for m in game_channel.members if m.id != owner_id])

    async def update_queue_display(self, guild: discord.Guild, config: dict):
        queue_data = get_queue()
        queue_text_channel = self.bot.get_channel(config["queue_text_channel_id"])
        is_auto_queue = config["auto_fill_enabled"]
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
                update_queue_embed_message(guild.id, new_msg.id)
        else:
            msg = await queue_text_channel.send(embed=embed)
            update_queue_embed_message(guild.id, msg.id)

    async def move_next_user(self, guild: discord.Guild, config: dict):
        game_channel = self.bot.get_channel(config["live_channel_id"])
        queue_data = get_queue()

        owner_id = guild.owner_id

        if not  self.is_owner_in_game_room(game_channel=game_channel, owner_id= owner_id):
            print("[SKIP] Owner not in game channel. Skipping move.")
            return

        if not queue_data:
            return

        for user_id, _ in queue_data:
            member = guild.get_member(user_id)
            if not member:
                continue

            try:
                await member.move_to(game_channel)
                print(f"[MOVE] Moved {member.name} to game room.")
            except discord.HTTPException as e:
                print(f"[ERROR] Couldn't move {member.name}: {e}")
                continue

            log_channel = self.bot.get_channel(config["queue_log_channel"])
            if log_channel:
                await log_channel.send(f"➡️ Moved <@{member.id}> to Live Room.")

            remove_from_queue(member.id)
            await self.update_queue_display(guild, config)
            continue

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        config = get_config(guild_id=member.guild.id)
        if not config:
            return

        waiting_channel_id = config["waiting_channel_id"]
        game_channel_id = config["live_channel_id"]
        owner_id = member.guild.owner_id
        max_guests = config.get("max_guests", 3)
        auto_fill = config.get("auto_fill_enabled", 1)

        game_channel = self.bot.get_channel(game_channel_id)

        # ➕ Joined waiting room
        if after.channel and after.channel.id == waiting_channel_id:
            print(f"[JOIN] {member.name} joined waiting room.")
            add_to_queue(user_id=member.id, username=member.display_name)
            await self.update_queue_display(member.guild, config)

            if (
                auto_fill
                and game_channel
                and self.is_owner_in_game_room(game_channel, owner_id)
                and self.get_guest_count(game_channel, owner_id) < max_guests
            ):
                await self.move_next_user(member.guild, config)

        # ➖ Left waiting room
        elif before.channel and before.channel.id == waiting_channel_id:
            print(f"[LEAVE] {member.name} left waiting room.")
            remove_from_queue(member.id)
            await self.update_queue_display(member.guild, config)

        # 🧑‍💼 Owner joined game → try to fill
        elif (
            after.channel
            and after.channel.id == game_channel_id
            and member.id == owner_id
            and self.get_guest_count(game_channel, owner_id) < max_guests
        ):
            print(f"[Owner] Owner join the game channel")
            if auto_fill and game_channel:
                await self.move_next_user(member.guild, config=config)

        # 🔁 Left game room → try to refill
        elif before.channel and before.channel.id == game_channel_id:
            print(f"[GAME LEFT] {member.name} left live room.")
            if (
                game_channel
                and self.is_owner_in_game_room(game_channel, owner_id)
                and self.get_guest_count(game_channel, owner_id) < max_guests
            ):
                await self.move_next_user(member.guild, config)
