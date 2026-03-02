import os
import discord
from discord.ext import commands
from datetime import datetime, timezone
from utils.config import ConfigManager

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config("welcome.json")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Reload config to support dynamic updates per guild
        guild_id = member.guild.id
        config = self.config_manager.load_config("welcome.json", guild_id=guild_id)

        auto_role_id = config.get("auto_role_id")
        welcome_channel_id = config.get("channel_id")
        banner_url = config.get("banner_url")
        embed_config = config.get("embed", {})

        # Assign Auto Role
        if auto_role_id:
            try:
                role_id = int(auto_role_id)
                role = member.guild.get_role(role_id)
                if role:
                    try:
                        await member.add_roles(role)
                        print(f"Assigned role {role.name} to {member.name}")
                    except discord.Forbidden:
                        print(f"Failed to assign role: Missing permissions to assign role {role_id}")
                    except discord.HTTPException as e:
                        print(f"Failed to assign role: HTTP Exception {e}")
                else:
                    print(f"Role with ID {role_id} not found in guild {member.guild.name}")
            except ValueError:
                print(f"Invalid auto_role_id: {auto_role_id}")

        # Create the embed
        description = embed_config.get("description", "{mention} We are very glad to have you in our minecraft server!").replace("{mention}", member.mention)
        color = embed_config.get("color", discord.Color.blue().value)

        embed = discord.Embed(
            title=embed_config.get("title", ""),
            description=description,
            color=discord.Color(color),
            timestamp=datetime.now(timezone.utc)
        )

        # Set user avatar as thumbnail (Right Side Top)
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        elif member.display_avatar:
             embed.set_thumbnail(url=member.display_avatar.url)

        # Set custom banner as image (Bottom)
        if banner_url:
            embed.set_image(url=banner_url)

        # Add server connections info
        for field in embed_config.get("fields", []):
            embed.add_field(
                name=field.get("name", ""),
                value=field.get("value", ""),
                inline=field.get("inline", False)
            )

        # Add footer
        footer_text = embed_config.get("footer", "Have fun, and welcome to the BrambleSMP journey!")
        embed.set_footer(text=footer_text)

        # Determine the channel to send the message to
        channel = None
        if welcome_channel_id:
            try:
                channel = self.bot.get_channel(int(welcome_channel_id))
            except ValueError:
                print(f"Invalid channel_id: {welcome_channel_id}")

        if not channel:
            if member.guild.system_channel:
                channel = member.guild.system_channel
            else:
                # Fallback to the first text channel where the bot can send messages
                for guild_channel in member.guild.text_channels:
                    if guild_channel.permissions_for(member.guild.me).send_messages:
                        channel = guild_channel
                        break

        if channel:
            await channel.send(embed=embed)
        else:
            print(f"Could not find a channel to send welcome message for {member.name}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
