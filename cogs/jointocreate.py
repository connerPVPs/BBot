import os
import json
import discord
from discord.ext import commands
from utils.config import ConfigManager

DATA_FILE = "jointocreate_data.json"

class JoinToCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = ConfigManager()
        self.active_channels = []
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    self.active_channels = json.load(f)
            except json.JSONDecodeError:
                self.active_channels = []
        else:
            self.active_channels = []

    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.active_channels, f)

    @commands.Cog.listener()
    async def on_ready(self):
        # Validate active channels on startup
        valid_channels = []
        for channel_id in self.active_channels:
            channel = self.bot.get_channel(channel_id)
            if channel:
                valid_channels.append(channel_id)

        if len(valid_channels) != len(self.active_channels):
            self.active_channels = valid_channels
            self.save_data()
            print(f"Cleaned up JoinToCreate data. Active channels: {len(self.active_channels)}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        config = self.config_manager.load_config("jointocreate.json")
        trigger_id_str = config.get("trigger_channel_id")

        if not trigger_id_str:
            return

        try:
            trigger_id = int(trigger_id_str)
        except ValueError:
            print("Invalid trigger_channel_id in config")
            return

        # Handle Cleanup (User left a voice channel)
        # Check if before.channel exists and is in active_channels
        if before.channel and before.channel.id in self.active_channels:
            if len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                except discord.NotFound:
                    pass # Already deleted
                except Exception as e:
                    print(f"Failed to delete dynamic channel {before.channel.id}: {e}")

                # Double check before removing to avoid race conditions
                if before.channel.id in self.active_channels:
                    self.active_channels.remove(before.channel.id)
                    self.save_data()

        # Handle Creation (User joined the trigger channel)
        if after.channel and after.channel.id == trigger_id:
            # Check limit
            max_channels = config.get("max_channels", 7)
            if len(self.active_channels) >= max_channels:
                # Limit reached
                try:
                    await member.move_to(None) # Kick from voice
                except discord.Forbidden:
                    pass # Can't kick

                embed_config = config.get("error_embed", {})
                embed = discord.Embed(
                    title=embed_config.get("title", "Limit Reached"),
                    description=embed_config.get("description", "Limit reached."),
                    color=discord.Color(embed_config.get("color", discord.Color.blue().value))
                )

                try:
                    await member.send(embed=embed)
                except discord.Forbidden:
                    pass # DMs closed
                return

            # Create Channel
            category = after.channel.category
            channel_name = config.get("channel_name_format", "{user}'s-VC").replace("{user}", member.display_name)
            user_limit = config.get("user_limit", 25)

            try:
                new_channel = await after.channel.guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    user_limit=user_limit
                )

                # Move user
                await member.move_to(new_channel)

                self.active_channels.append(new_channel.id)
                self.save_data()

            except Exception as e:
                print(f"Failed to create join-to-create channel: {e}")

async def setup(bot):
    await bot.add_cog(JoinToCreate(bot))
