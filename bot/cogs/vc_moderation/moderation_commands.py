import discord
from discord import app_commands
from discord.ext import commands
from idna import check_nfc
from typing_extensions import override


class ModerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_collection = self.bot.db.users
        self.guild_collection = self.bot.db.guild_config
        self.vc_blocks = self.bot.db.vc_blocks

    @app_commands.command(name="remove_quarantine", description="Remove quarantine from a user who got banned twice in a voice channel.")
    @app_commands.checks.has_permissions(administrator = True)
    async def remove_quarantine(self, interaction: discord.Interaction, member : discord.Member):
        if not member:
            await interaction.response.send_message("Mention a user to remove quarantine", ephemeral= True)
            return

        # Defer the interaction to prevent timeout
        await interaction.response.defer(thinking=True, ephemeral=True)

        user_data = await self.user_collection.find_one({"_id": member.id})

        print(f"User data {user_data}")

        kick_object = user_data.get("kick_counts", {})
        print(f"Kick Object : {kick_object}")
        roles_id = kick_object.get("previous_roles", [])
        print(f"Roles id {roles_id}")

        roles = [ discord.utils.get(interaction.guild.roles, id = rid) for rid in roles_id]
        roles = [r for r in roles if r is not None]

        print(f"Roles {roles}")

        muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role, reason="Mute Lifted")

        if roles:
            await  member.add_roles(*roles, reason="Restoring roles after VC mute lifted")

        # 🧠 Get all documents where user is banned in voice channel
        banned_channels = await self.vc_blocks.find({"banned_user_ids": member.id}).to_list(length=None)

        for doc in banned_channels:
            channel_id = doc["voice_channel_id"]
            channel= interaction.guild.get_channel(channel_id)

            if channel:
                overrides = channel.overwrites
                if member in overrides:
                    del overrides[member]
                    await  channel.edit(overwrites=overrides)

        # --- Remove user from all banned_user_ids arrays ---
        await self.vc_blocks.update_many(
            {"banned_user_ids": member.id},  # Match any doc where this user is banned
            {"$pull": {"banned_user_ids": member.id}}  # Remove user ID from array
        )

        await self.user_collection.update_one(
            {"_id": member.id},
            {"$unset": {f"kick_counts.previous_role": ""}}
        )

        await interaction.followup.send(f"✅ Quarantine removed from {member.mention}", ephemeral=True)

    @app_commands.command(name="moderation_log_channel",description="Set a moderation log channel.")
    @app_commands.checks.has_permissions(administrator = True)
    async def moderation_log_channel(self, interaction : discord.Interaction, channel: discord.TextChannel =None):
        if not channel:
            channel = interaction.channel

        await self.guild_collection.update_one(
            {"guild_id": interaction.guild.id},
            {"$set":{"mod_log_channel_id": channel.id}},
            upsert= True
        )

        await  interaction.response.send_message(f"{channel.mention} has been set for Moderation Logs", ephemeral= True)


    # @app_commands.command(name="remove_channel_ban", description="Remove a user's ban from a voice channel")
    # @app_commands.checks.has_permissions(administrator = True)
    # async def remove_channel_ban(self, interaction : discord.Interaction, channel: discord.VoiceChannel, member: discord.Member):
    #
    #     await interaction.response.defer(thinking=True, ephemeral=True)
    #     docs = await self.vc_blocks.find_one({"voice_channel_id":channel.id})
    #     if not docs:
    #         await interaction.followup.send(f"Channel not found in the user's ban list", ephemeral= True)
    #         return
    #
    #     banned_list = docs.get("banned_user_ids",[])
    #
    #
    #
    #     if member.id in banned_list:
    #         update = await self.vc_blocks.update_one(
    #             {"voice_channel_id": channel.id},
    #             {
    #                 "$pull" :{
    #                     "banned_user_ids" : member.id
    #                 }
    #             },
    #             upsert= True
    #         )
    #
    #         if update.modified_count > 0:
    #             await interaction.followup.send(f"Remove {member.mention}'s ban from {channel.mention}")
    #
    #     else:
    #         await interaction.followup.send(f"{member.mention}  not found in {channel.mention}'s banned list")

    @app_commands.command(name="reset_ban", description="Reset ban count for a user who got kicked once from voice channel")
    @app_commands.checks.has_permissions(administrator = True)
    async def reset_ban(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True, thinking= True)

        docs = await  self.user_collection.find_one({"_id": member.id})

        if not docs:
            await interaction.followup.send(f"{member.mention} not found in banned list")
            return

        reset = await self.user_collection.update_one(
            {"_id": member.id},
            {"$set":{"kick_counts.count":0}},
            upsert= True
        )



        channel_doc = await  self.vc_blocks.find_one(
            {"banned_user_ids": member.id}
        )

        channel_id = channel_doc["voice_channel_id"]
        channel = interaction.guild.get_channel(channel_id)

        overrides = channel.overwrites
        if member in overrides:
            del overrides[member]
            await channel.edit(overwrites=overrides)

        # --- Remove user from all banned_user_ids arrays ---
        remove_channel_ban = await self.vc_blocks.update_many(
            {"banned_user_ids": member.id},  # Match any doc where this user is banned
            {"$pull": {"banned_user_ids": member.id}}  # Remove user ID from array
        )

        # --- Send feedback ---
        if reset.modified_count > 0 or reset.upserted_id is not None:
            msg = f"✅ Reset ban count for {member.mention}."
            if remove_channel_ban.modified_count > 0:
                msg += f" Also removed from {remove_channel_ban.modified_count} voice channel ban list(s)."
            else:
                msg += " No VC ban entries were found."
            await interaction.followup.send(msg)
        else:
            await interaction.followup.send(f"⚠️ Failed to reset ban count for {member.mention}.")






