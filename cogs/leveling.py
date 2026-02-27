import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from utils.config import ConfigManager
import math
import time

DATA_FILE = "levels_data.json"

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = ConfigManager()
        self.users = {}
        self.cooldowns = {}
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    self.users = json.load(f)
            except json.JSONDecodeError:
                self.users = {}
        else:
            self.users = {}

    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.users, f)

    def calculate_level(self, xp):
        # Formula: "100 msgs the level upgrades it get's harder and harder"
        # Let's assume Level 1 = 100 XP.
        # We can use a quadratic formula: XP = 50 * L^2 + 50 * L (so L=1 -> 100)
        # Or simpler: Level = sqrt(XP / 100) -> NO, that makes high levels easier relative to total XP if we counted cumulative.
        # But if "100 msgs" means delta:
        # L1: 100
        # L2: 100 + X

        # Let's use: XP = 100 * Level + 10 * Level^2 (Cumulative)
        # If XP = 100, Level ~ 0.9 (approx 1)
        # We need an inverse function to get Level from XP.
        # 10L^2 + 100L - XP = 0
        # L = (-100 + sqrt(10000 - 4*10*(-XP))) / 20
        # L = (-100 + sqrt(10000 + 40XP)) / 20
        # L = (-10 + sqrt(100 + 0.4XP)) / 2

        if xp <= 0:
            return 0

        # Using a difficulty curve that starts linear-ish (100) and grows.
        # Let's say: XP required for next level N is 100 + (N * 20).
        # Total XP for Level L = Sum(100 + 20*i for i in 0..L-1)
        # = 100L + 20 * (L(L-1)/2)
        # = 100L + 10L^2 - 10L
        # = 10L^2 + 90L

        # Inverse: 10L^2 + 90L - XP = 0
        # L = (-90 + sqrt(8100 + 40XP)) / 20

        level = (-90 + math.sqrt(8100 + 40 * xp)) / 20
        return int(level)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Cooldown: 1 message per 2 seconds counts
        user_id = str(message.author.id)
        current_time = time.time()

        if user_id in self.cooldowns:
            if current_time - self.cooldowns[user_id] < 2:
                return

        self.cooldowns[user_id] = current_time

        if user_id not in self.users:
            self.users[user_id] = {"xp": 0, "level": 0}

        old_level = self.users[user_id]["level"]
        self.users[user_id]["xp"] += 1 # 1 XP per message

        new_level = self.calculate_level(self.users[user_id]["xp"])

        if new_level > old_level:
            self.users[user_id]["level"] = new_level
            await self.handle_level_up(message.author, new_level)

        self.save_data()

    async def handle_level_up(self, member, new_level):
        config = self.config_manager.load_config("leveling.json")

        # Announcement every 5 levels
        if new_level % 5 == 0:
            channel_id = config.get("announcement_channel_id")
            if channel_id:
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    embed_config = config.get("embed", {})
                    description = embed_config.get("description", "Congrats {user}! Level {level}").replace("{user}", member.mention).replace("{level}", str(new_level))

                    embed = discord.Embed(
                        title=embed_config.get("title", "Level Up!"),
                        description=description,
                        color=discord.Color(embed_config.get("color", discord.Color.blue().value))
                    )
                    await channel.send(embed=embed)

        # Role Rewards
        rewards = config.get("role_rewards", {})
        if str(new_level) in rewards:
            role_id = rewards[str(new_level)]
            try:
                role = member.guild.get_role(int(role_id))
                if role:
                    await member.add_roles(role)
                    print(f"Assigned level {new_level} role to {member.name}")
            except Exception as e:
                print(f"Failed to assign level role: {e}")

    @app_commands.command(name="rank", description="Check your current level and XP")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        user_id = str(member.id)

        data = self.users.get(user_id, {"xp": 0, "level": 0})
        xp = data["xp"]
        level = data["level"]

        # Calculate XP needed for next level
        # Total XP for Level L = 10L^2 + 90L
        next_level_xp = 10 * ((level + 1) ** 2) + 90 * (level + 1)
        prev_level_xp = 10 * (level ** 2) + 90 * level

        xp_progress = xp - prev_level_xp
        xp_needed = next_level_xp - prev_level_xp

        embed = discord.Embed(
            title=f"Rank - {member.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="Total XP", value=str(xp), inline=True)
        embed.add_field(name="Progress", value=f"{xp_progress}/{xp_needed} XP to Level {level+1}", inline=False)

        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
