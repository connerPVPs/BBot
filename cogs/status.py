import os
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from datetime import datetime, timezone
from utils.config import ConfigManager

STATUS_FILE = "status_data.json"

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_messages = []
        self.config_manager = ConfigManager()
        self.load_status_data()
        self.update_server_status.start()

    def cog_unload(self):
        self.update_server_status.cancel()

    def load_status_data(self):
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r") as f:
                    self.status_messages = json.load(f)
            except json.JSONDecodeError:
                self.status_messages = []
        else:
            self.status_messages = []

    def save_status_data(self):
        with open(STATUS_FILE, "w") as f:
            json.dump(self.status_messages, f)

    async def fetch_server_data(self, ip):
        url = f"https://api.mcsrvstat.us/3/{ip}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None

    def create_status_embed(self, ip, data, guild_id=None):
        config = self.config_manager.load_config("status.json", guild_id=guild_id)
        embed_config = config.get("embed", {})

        embed = discord.Embed(
            title=embed_config.get("title", "Bramble SMP | Status"),
            color=discord.Color(embed_config.get("color", discord.Color.blue().value)),
            timestamp=datetime.now(timezone.utc)
        )

        is_online = data.get("online", False)

        # Players
        if is_online and "players" in data:
            players_online = data["players"]["online"]
            players_max = data["players"]["max"]
            embed.add_field(name="Players Online", value=f"{players_online}/{players_max}", inline=True)
        else:
            embed.add_field(name="Players Online", value="--", inline=True)

        # Version
        if is_online and "protocol" in data:
             version = data["protocol"].get("name", "Unknown")
             embed.add_field(name="Server Version", value=version, inline=True)
        elif is_online and "version" in data:
             version = data["version"]
             embed.add_field(name="Server Version", value=version, inline=True)
        else:
             embed.add_field(name="Server Version", value="--", inline=True)

        # Status
        status_text = "Online" if is_online else "Offline"
        embed.add_field(name="Server Status", value=status_text, inline=True)

        # Update text
        embed.description = embed_config.get("description", "Updates every 60 seconds.")

        # Images
        embed.set_thumbnail(url=f"https://api.mcsrvstat.us/icon/{ip}")
        # Use mcstatus.io for the banner image
        embed.set_image(url=f"https://api.mcstatus.io/v2/widget/java/{ip}")

        return embed

    @app_commands.command(name="status", description="Setup a live Minecraft server status message")
    @app_commands.describe(server_ip="The IP of the Minecraft server", channel="The channel to send the status embed")
    @app_commands.default_permissions(administrator=True)
    async def status_command(self, interaction: discord.Interaction, server_ip: str, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        data = await self.fetch_server_data(server_ip)
        if not data:
            await interaction.followup.send("Failed to fetch server data. Check the IP and try again.", ephemeral=True)
            return

        embed = self.create_status_embed(server_ip, data, guild_id=interaction.guild.id)

        try:
            message = await channel.send(embed=embed)

            # Track message
            self.status_messages.append({
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "message_id": message.id,
                "server_ip": server_ip
            })
            self.save_status_data()

            await interaction.followup.send(f"Status message created in {channel.mention} for `{server_ip}`.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"I don't have permission to send messages in {channel.mention}.", ephemeral=True)

    @tasks.loop(seconds=60)
    async def update_server_status(self):
        messages_to_remove = []

        for entry in self.status_messages:
            guild_id = entry.get("guild_id")
            channel_id = entry["channel_id"]
            message_id = entry["message_id"]
            server_ip = entry["server_ip"]

            try:
                channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
                if not channel:
                    messages_to_remove.append(entry)
                    continue

                message = await channel.fetch_message(message_id)
                data = await self.fetch_server_data(server_ip)

                if data:
                    embed = self.create_status_embed(server_ip, data, guild_id=guild_id)
                    await message.edit(embed=embed)
                else:
                    # Could not fetch data, maybe API down, skip edit
                    pass

            except discord.NotFound:
                # Message or channel deleted
                messages_to_remove.append(entry)
            except discord.Forbidden:
                # Permission lost
                messages_to_remove.append(entry)
            except Exception as e:
                print(f"Error updating status message for {server_ip}: {e}")

        if messages_to_remove:
            for entry in messages_to_remove:
                if entry in self.status_messages:
                    self.status_messages.remove(entry)
            self.save_status_data()

    @update_server_status.before_loop
    async def before_update_server_status(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Status(bot))
