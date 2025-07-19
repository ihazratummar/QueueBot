import discord
from discord.ext import commands


class QueueListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.twitch_ward_config_collection = self.bot.db.twitch_ward_config_collection

    def is_owner_in_game_room(self, game_channel: discord.VoiceChannel, owner_id: int):
        return any(member.id == owner_id for member in game_channel.members)

    def get_guest_count(self, game_channel: discord.VoiceChannel, owner_id: int):
        return len([m for m in game_channel.members if m.id != owner_id])

    async def update_queue_display(self, guild: discord.Guild, config: dict):
        queue_data = config.get("twitch_ward_queue", [])
        queue_text_channel = self.bot.get_channel(config["queue_text_channel_id"])
        is_auto_queue = bool(config.get("auto_fill_enabled", False))

        display = (
                "\n".join([
                    f"{i + 1}. <@{entry['user_id'] if isinstance(entry, dict) else entry[0]}>"
                    for i, entry in enumerate(queue_data)
                ]) or "*Queue is empty*"
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
                await self.twitch_ward_config_collection.update_one(
                    {"_id": guild.id},
                    {"$set": {"queue_embed_message_id": new_msg.id}},
                    upsert=True
                )
        else:
            msg = await queue_text_channel.send(embed=embed)
            await self.twitch_ward_config_collection.update_one(
                {"_id": guild.id},
                {"$set": {"queue_embed_message_id": msg.id}},
                upsert=True
            )

    async def move_next_user(self, guild: discord.Guild, config: dict):
        game_channel = self.bot.get_channel(config["live_channel_id"])
        queue_data = config.get("twitch_ward_queue", [])
        owner_id = guild.owner_id

        if not self.is_owner_in_game_room(game_channel=game_channel, owner_id=owner_id):
            print("[SKIP] Owner not in game channel. Skipping move.")
            return

        if not queue_data:
            return

        for entry in queue_data:
            member = guild.get_member(entry["user_id"])
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

            await self.twitch_ward_config_collection.update_one(
                {"_id": member.guild.id},
                {"$pull": {"twitch_ward_queue": {"user_id": member.id}}}
            )
            # Fetch the updated config after modifying the twitch_ward_queue
            updated_config = await self.twitch_ward_config_collection.find_one({"_id": guild.id})
            await self.update_queue_display(guild, updated_config)
            continue  # Only move one user at a time

    @commands.Cog.listener()
    async def on_voice_state_update(
            self,
            member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState,
    ):
        if member.bot:
            return

        config = await self.twitch_ward_config_collection.find_one({"_id": member.guild.id})
        if not config:
            return

        waiting_channel_id = config["waiting_channel_id"]
        game_channel_id = config["live_channel_id"]
        owner_id = member.guild.owner_id
        max_guests = config.get("max_guests", 3)
        auto_fill = config.get("auto_fill_enabled", False)

        game_channel = self.bot.get_channel(game_channel_id)

        # ➕ Joined waiting room
        if after.channel and after.channel.id == waiting_channel_id:
            print(f"[JOIN] {member.name} joined waiting room.")
            print(f"Queue before join: {config.get('twitch_ward_queue', [])}")
            await self.twitch_ward_config_collection.update_one(
                {"_id": member.guild.id},
                {"$push": {"twitch_ward_queue": {"user_id": member.id, "name": member.display_name}}},
                upsert=True
            )
            config = await self.twitch_ward_config_collection.find_one({"_id": member.guild.id})
            print(f"Queue after join: {config.get('twitch_ward_queue', [])}")
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
            print(f"Queue before leave: {config.get('twitch_ward_queue', [])}")
            await self.twitch_ward_config_collection.update_one(
                {"_id": member.guild.id},
                {"$pull": {"twitch_ward_queue": {"user_id": member.id}}}
            )
            config = await self.twitch_ward_config_collection.find_one({"_id": member.guild.id})
            print(f"Queue after leave: {config.get('twitch_ward_queue', [])}")
            await self.update_queue_display(member.guild, config)

        # 🧑‍💼 Owner joined game → try to fill
        elif (
                after.channel
                and after.channel.id == game_channel_id
                and member.id == owner_id
                and self.get_guest_count(game_channel, owner_id) < max_guests
        ):
            print(f"[Owner] Owner joined the game channel")
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
