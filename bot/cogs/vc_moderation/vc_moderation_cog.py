import asyncio
import math
from collections import defaultdict

import discord
from discord.ext import commands
from typing_extensions import override


class KickReasonModal(discord.ui.Modal, title='Kick Reason'):
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.short)

    def __init__(self, cog, target_user, channel):
        super().__init__()
        self.cog = cog
        self.target_user = target_user
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        vote_view = KickVoteView(self.cog, interaction.guild, self.channel, self.target_user, self.reason.value)
        self.cog.active_votes[self.channel.id] = vote_view

        vote_embed = discord.Embed(
            title=f"Vote to kick {self.target_user.display_name}",
            description=f"A vote has been started to kick {self.target_user.mention}. You have 30 seconds to vote.",
            color=discord.Color.orange()
        )
        vote_embed.add_field(name="Reason", value=self.reason.value)
        vote_embed.add_field(name="Yes Votes", value=0, inline=True)
        vote_embed.add_field(name="No Votes", value=0, inline=True)
        message = await self.channel.send(embed=vote_embed, view=vote_view)
        vote_view.message = message
        channel = await self.cog.log_kick_vote(interaction.guild)
        await channel.send(f"Vote to kick {self.target_user.mention} started by {interaction.user.mention}.")
        await interaction.response.send_message("Vote started!", ephemeral=True)


class KickVoteView(discord.ui.View):
    def __init__(self, cog, guild, channel, target_user, reason):
        super().__init__(timeout=30)
        self.cog = cog
        self.guild : discord.Guild = guild
        self.channel: discord.VoiceChannel = channel
        self.target_user = target_user
        self.reason = reason
        self.votes = defaultdict(lambda: None)
        self.message = None

    async def required_votes(self):
        return math.ceil(len(await self._get_eligible_voters()) * 0.6)

    async def _get_eligible_voters(self):
        updated_channel = await self.guild.fetch_channel(self.channel.id)
        return [member.id for member in updated_channel.members if
                not member.bot and member.id != self.target_user.id and member.id != self.guild.owner_id]

    async def on_timeout(self):
        if self.message:
            await self.finalize_vote()

    async def finalize_vote(self):
        if not self.message:
            return

        yes_votes = sum(1 for vote in self.votes.values() if vote is True)
        no_votes = sum(1 for vote in self.votes.values() if vote is False)
        channel = await self.cog.log_kick_vote(self.guild)

        result_embed = discord.Embed(title="Vote Failed")

        if yes_votes >= await self.required_votes():
            result_embed.title = "Vote Passed"
            result_embed.color = discord.Color.green()
            result_embed.description = f"✅ Vote passed. {self.target_user.mention} will be acted upon."

            result_embed.add_field(name="🧾 Reason", value= f">>> {self.reason}")

            try:
                user_id = self.target_user.id

                # Update VC block list
                await self.cog.vc_blocks.update_one(
                    {"voice_channel_id": self.channel.id},
                    {"$addToSet": {"banned_user_ids": user_id}},
                    upsert=True
                )

                banned_user = self.guild.get_member(user_id)
                overrides = self.channel.overwrites
                overrides[banned_user] = discord.PermissionOverwrite(connect = False, view_channel = False)

                await  self.channel.edit(overwrites= overrides)

                # Increment kick count
                await self.cog.user_collection.update_one(
                    {"_id": user_id},
                    {
                        "$inc": {"kick_counts.count": 1},
                        "$set": {"kick_counts.last_kicked_at": discord.utils.utcnow()}
                    },
                    upsert=True
                )

                # Fetch updated user data
                user_doc = await self.cog.user_collection.find_one({"_id": user_id})
                kick_data = user_doc.get("kick_counts", {})
                kick_count = kick_data.get("count", 0)

                # 1st kick → move to AFK (if exists), else disconnect
                if kick_count == 1:
                    afk_channel = self.guild.afk_channel
                    if afk_channel:
                        await self.target_user.move_to(afk_channel, reason="First VC kick – moved to AFK")
                        result_embed.description += f"\n➡️ {self.target_user.mention} has been moved to AFK."
                    else:
                        await self.target_user.move_to(None, reason="First VC kick – disconnected (no AFK channel)")
                        result_embed.description += f"\n➡️ {self.target_user.mention} has been disconnected (no AFK channel)."

                # 2nd+ kick → mute, remove roles, etc.
                elif kick_count >= 2:

                    try:
                        await self.target_user.move_to(None, reason="Second VC kick – disconnected & muted")
                        result_embed.description += f"\n➡️ {self.target_user.mention} has been disconnected from VC."
                    except discord.HTTPException as e:
                        result_embed.description += f"\n⚠️ Failed to disconnect user: {e}"

                    muted_role = discord.utils.get(self.guild.roles, name="Muted")
                    if not muted_role:
                        muted_role = await self.guild.create_role(name="Muted", reason="Auto-mute for excessive kicks")
                        for vc in self.guild.voice_channels + self.guild.stage_channels:
                            overwrite = discord.PermissionOverwrite(view_channel=True, connect=False, speak=False)
                            await vc.set_permissions(muted_role, overwrite=overwrite)

                    try:
                        # Filter roles
                        protected_roles = ["Server Booster", "Twitch Subscribers", "Owner"]
                        roles_to_remove = [
                            role for role in self.target_user.roles
                            if role.name not in protected_roles
                               and role != self.guild.default_role
                               and role != muted_role
                        ]

                        role_ids = [role.id for role in roles_to_remove]

                        if roles_to_remove:
                            await self.target_user.remove_roles(*roles_to_remove, reason="VC auto-mute (2 kicks)")

                        await self.target_user.add_roles(muted_role, reason="Muted after 2 VC kicks")

                        # Reset kick count & save old roles
                        await self.cog.user_collection.update_one(
                            {"_id": user_id},
                            {
                                "$set": {
                                    "kick_counts.count": 0,
                                    "kick_counts.previous_roles": role_ids
                                }
                            }
                        )

                        result_embed.description += f"\n🚫 {self.target_user.mention} has been muted and roles removed."

                    except discord.HTTPException as e:
                        result_embed.description += f"\n⚠️ Failed to assign mute role: {e}"

                await channel.send(f"{self.guild.owner.mention} <@&1304100217091653642>", embed=result_embed)

            except discord.HTTPException as e:
                result_embed.description += f"\n⚠️ Failed to move user: {e}"
                await channel.send(embed=result_embed)

        else:
            # Vote failed
            result_embed.title = "Vote Failed"
            result_embed.color = discord.Color.red()
            result_embed.description = f"The vote to kick {self.target_user.mention} failed."
            await channel.send(embed=result_embed)

        # Add votes count fields
        result_embed.add_field(name="👍 Yes Votes", value=yes_votes)
        result_embed.add_field(name="👎 No Votes", value=no_votes)

        # Edit original message
        await self.message.edit(embed=result_embed, view=None)
        self.cog.active_votes.pop(self.channel.id, None)

        # Cleanup message after delay
        await asyncio.sleep(10)
        try:
            await self.message.delete()
        except discord.NotFound:
            pass

    async def update_vote_embed(self):
        yes_votes = sum(1 for vote in self.votes.values() if vote is True)
        no_votes = sum(1 for vote in self.votes.values() if vote is False)

        embed = self.message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "Yes Votes":
                embed.set_field_at(i, name="Yes Votes", value=yes_votes, inline=True)
            elif field.name == "No Votes":
                embed.set_field_at(i, name="No Votes", value=no_votes, inline=True)
        await self.message.edit(embed=embed)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, True)

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, False)

    async def _handle_vote(self, interaction, vote_value):
        if interaction.user.voice is None or interaction.user.voice.channel != self.channel:
            await interaction.response.send_message("You must be in the voice channel to vote.", ephemeral=True)
            return

        if interaction.user.id == self.target_user.id:
            await interaction.response.send_message("You cannot vote to kick yourself.", ephemeral=True)
            return

        if interaction.user.id in self.votes:
            await interaction.response.send_message("You have already voted.", ephemeral=True)
            return

        self.votes[interaction.user.id] = vote_value
        await interaction.response.send_message(f"You voted {'Yes' if vote_value else 'No'}.", ephemeral=True)
        await self.update_vote_embed()

        eligible = await self._get_eligible_voters()
        if all(uid in self.votes for uid in eligible):
            await self.finalize_vote()
            self.stop()


class VCModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc_blocks = self.bot.db.vc_blocks
        self.vc_embeds = self.bot.db.vc_embeds
        self.guild_collection = self.bot.db.guild_config
        self.user_collection = self.bot.db.users
        self.active_votes = {}
        self._creating_embed_for_channel = set()
        self.bot.scheduler.add_job(
            self.delete_chanel,
            "interval",
            hours=5
        )

    async def delete_chanel(self):
        asyncio.create_task(self.check_channel_exist(collection=self.vc_embeds))
        asyncio.create_task(self.check_channel_exist(collection=self.vc_blocks))

    async def check_channel_exist(self, collection):
        # Fetch all VC block entries
        vc_block_channels = await collection.find({}).to_list(length=None)

        for entry in vc_block_channels:
            channel_id = entry.get("voice_channel_id")
            guild = self.bot.get_guild(1304100216944853013)

            if not guild:
                continue

            # Check if the voice channel exists in the guild
            channel = guild.get_channel(channel_id)
            if not channel:
                # Voice channel no longer exists — remove the document from DB
                result = await collection.delete_one({"_id": entry["_id"]})
                if result.deleted_count > 0:
                    print(f"✅ Deleted DB entry for missing VC: {channel_id}")

    async def log_kick_vote(self, guild):
        doc = await self.guild_collection.find_one({"guild_id": guild.id})
        channel_id = doc.get("mod_log_channel_id", 1395972057635749958)
        log_channel = guild.get_channel(channel_id)
        if isinstance(log_channel, discord.TextChannel):
            return log_channel
        return None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        async def disconnect_bots_if_alone(channel: discord.VoiceChannel):
            if not any(not m.bot for m in channel.members):
                for m in channel.members:
                    if m.bot:
                        try:
                            await m.move_to(None, reason="No human users left in the voice channel.")
                        except discord.HTTPException:
                            pass

        # User left VC
        if before.channel and not after.channel:
            await disconnect_bots_if_alone(before.channel)
            if not before.channel.members:
                await self.cleanup_vc_embed(before.channel)
            else:
                await self.update_vc_embed(before.channel)

        # User switched VC
        elif before.channel and after.channel and before.channel != after.channel:
            if await self.is_user_banned(member, after.channel):
                try:
                    channel_name = after.channel.name if after.channel else "an unknown voice channel"
                    await member.move_to(None, reason="Banned from this voice channel.")
                    await member.send(f"You are banned from the voice channel: {channel_name}")
                except discord.HTTPException:
                    pass
                return

            await disconnect_bots_if_alone(before.channel)

            if not before.channel.members:
                await self.cleanup_vc_embed(before.channel)
            else:
                await self.update_vc_embed(before.channel)

            await self.update_vc_embed(after.channel)

        # User joined a VC directly
        elif not before.channel and after.channel:
            await asyncio.sleep(2)
            try:
                member = await member.guild.fetch_member(member.id)
                final_channel = member.voice.channel
            except (discord.NotFound, AttributeError):
                return

            if not final_channel:
                return

            if await self.is_user_banned(member, final_channel):
                try:
                    await member.move_to(None, reason="Banned from this voice channel.")
                    await member.send(f"You are banned from the voice channel: {final_channel.name}")
                except discord.HTTPException:
                    pass
                return

            await self.update_vc_embed(final_channel)

    async def is_user_banned(self, member, channel):
        if channel is None:
            return False
        block_info = await self.vc_blocks.find_one({"voice_channel_id": channel.id})
        return block_info and member.id in block_info.get("banned_user_ids", [])

    async def update_vc_embed(self, channel: discord.VoiceChannel):

        guild_afk = channel.guild.afk_channel
        exclude_channel_ids = {guild_afk.id} if guild_afk else  set()

        # exclude_channel_ids.update({})

        if channel.id in exclude_channel_ids:
            return

        if channel.id in self._creating_embed_for_channel:
            return

        self._creating_embed_for_channel.add(channel.id)
        try:
            if not channel.members:
                await self.cleanup_vc_embed(channel)
                return

            embed = discord.Embed(title=f"Members in {channel.name}", color=discord.Color.blue())
            view = discord.ui.View(timeout=None)

            for member in channel.members:
                if not member.bot and member.id != channel.guild.owner_id:
                    embed.add_field(name=member.display_name, value="\u200b", inline=False)
                    kick_button = discord.ui.Button(
                        label=f"Kick {member.display_name}",
                        style=discord.ButtonStyle.red,
                        custom_id=f"kick_{member.id}"
                    )
                    kick_button.callback = self.kick_button_callback
                    view.add_item(kick_button)

            embed_info = await self.vc_embeds.find_one({"voice_channel_id": channel.id})
            if embed_info and embed_info.get("message_id"):
                try:
                    message = await channel.fetch_message(embed_info["message_id"])
                    await message.edit(embed=embed, view=view)
                except discord.NotFound:
                    message = await channel.send(embed=embed, view=view)
                    await self.vc_embeds.update_one({"voice_channel_id": channel.id},
                                                    {"$set": {"message_id": message.id}}, upsert=True)
            else:
                message = await channel.send(embed=embed, view=view)
                await self.vc_embeds.update_one({"voice_channel_id": channel.id}, {"$set": {"message_id": message.id}},
                                                upsert=True)
        finally:
            self._creating_embed_for_channel.discard(channel.id)

    async def cleanup_vc_embed(self, channel):
        embed_info = await self.vc_embeds.find_one_and_delete({"voice_channel_id": channel.id})
        if embed_info and embed_info.get("message_id"):
            try:
                message = await channel.fetch_message(embed_info["message_id"])
                await message.delete()
            except discord.NotFound:
                pass

    async def kick_button_callback(self, interaction: discord.Interaction):
        target_user_id = int(interaction.data["custom_id"].split("_")[1])
        target_user = interaction.guild.get_member(target_user_id)

        if not target_user or not target_user.voice or not target_user.voice.channel:
            await interaction.response.send_message("User is no longer in a voice channel.", ephemeral=True)
            return

        channel = target_user.voice.channel

        if target_user.id == interaction.user.id:
            await interaction.response.send_message("Why would you want to kick yourself? That's not very nice.",
                                                    ephemeral=True)
            return

        if target_user.id == interaction.guild.owner_id:
            await interaction.response.send_message("You cannot kick the server owner.", ephemeral=True)
            return

        if interaction.user.voice is None or interaction.user.voice.channel != channel:
            await interaction.response.send_message("You must be in the same voice channel to start a vote.",
                                                    ephemeral=True)
            return

        if channel.id in self.active_votes:
            await interaction.response.send_message("A vote is already in progress in this channel.", ephemeral=True)
            return

        await interaction.response.send_modal(KickReasonModal(self, target_user, channel))
