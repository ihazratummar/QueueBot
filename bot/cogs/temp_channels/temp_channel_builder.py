import asyncio

import discord
from discord.ext import commands


class TempChannelBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_collection = self.bot.db.temp_collection
        self.created_channels = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild = member.guild
        category_name = "┌──── TEMP CHANNELS────┐"
        category = discord.utils.get(guild.categories, name=category_name)

        # Create category only once if it doesn't exist
        if not category:
            bot_member = guild.me
            overwrites = {
                bot_member: discord.PermissionOverwrite(
                    manage_channels=True,
                    move_members=True,
                    view_channel=True,
                    connect=True,
                    speak=True
                )
            }
            category = await guild.create_category(category_name, overwrites=overwrites)

        # User joined a voice channel
        if after.channel and not before.channel:
            doc = await self.temp_collection.find_one({"_id": guild.id})
            if doc and after.channel.id in doc.get("channel_ids", []):
                overwrites = after.channel.overwrites
                name = f"{member.name}'s channel"
                user_limit = after.channel.user_limit if after.channel.user_limit != 0 else None

                new_channel = await category.create_voice_channel(
                    name=name,
                    overwrites=overwrites,
                    user_limit=user_limit
                )
                self.created_channels[new_channel.id] = after.channel.id
                await asyncio.sleep(1)
                await member.move_to(new_channel)

        # User left a channel
        if before.channel and not after.channel:
            if before.channel.id in self.created_channels:
                if len(before.channel.members) == 0:
                    await before.channel.delete()
                    del self.created_channels[before.channel.id]

        # User moved between channels
        if before.channel and after.channel and before.channel.id != after.channel.id:
            if before.channel.id in self.created_channels:
                if len(before.channel.members) == 0:
                    await before.channel.delete()
                    del self.created_channels[before.channel.id]

            doc = await self.temp_collection.find_one({"_id": guild.id})
            if doc and after.channel.id in doc.get("channel_ids", []):
                overwrites = after.channel.overwrites
                name = f"{member.name}'s channel"
                user_limit = after.channel.user_limit if after.channel.user_limit != 0 else None

                new_channel = await category.create_voice_channel(
                    name=name,
                    overwrites=overwrites,
                    user_limit=user_limit
                )
                self.created_channels[new_channel.id] = after.channel.id
                await asyncio.sleep(1)
                await member.move_to(new_channel)
