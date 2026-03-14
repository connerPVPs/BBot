import discord
from discord import app_commands
from discord.ext import commands
from utils.config import ConfigManager
import asyncio
import aiohttp

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = ConfigManager()

    @app_commands.command(name="setup", description="Configure bot features for this server")
    @app_commands.describe(feature="Select the feature to setup")
    @app_commands.choices(feature=[
        app_commands.Choice(name="Welcome Message", value="welcome"),
        app_commands.Choice(name="Tickets", value="tickets"),
        app_commands.Choice(name="Music", value="music"),
        app_commands.Choice(name="Join to Create", value="jointocreate"),
        app_commands.Choice(name="Leveling", value="leveling"),
        app_commands.Choice(name="Minecraft Status", value="status"),
        app_commands.Choice(name="Server Branding (Name, Logo, etc)", value="branding")
    ])
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction, feature: str):
        if feature == "welcome":
            await self.setup_welcome(interaction)
        elif feature == "tickets":
            await self.setup_tickets(interaction)
        elif feature == "music":
            await self.setup_music(interaction)
        elif feature == "jointocreate":
            await self.setup_jointocreate(interaction)
        elif feature == "leveling":
            await self.setup_leveling(interaction)
        elif feature == "status":
            await self.setup_status(interaction)
        elif feature == "branding":
            await self.setup_branding(interaction)

    async def setup_welcome(self, interaction: discord.Interaction):
        await interaction.response.send_message("Welcome Setup started. Please reply to the following questions.")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            # 1. Welcome Channel
            await interaction.channel.send("Which channel should welcome messages be sent to? (Mention the channel)")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            if not msg.channel_mentions:
                 return await interaction.channel.send("Setup cancelled: No channel mentioned.")
            channel_id = msg.channel_mentions[0].id

            # 2. Auto Role
            await interaction.channel.send("Which role should be automatically assigned to new members? (Mention the role or type 'none')")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            auto_role_id = msg.role_mentions[0].id if msg.role_mentions else None

            # 3. Embed Title
            await interaction.channel.send("What should be the title of the welcome embed?")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            title = msg.content

            # 4. Embed Description
            await interaction.channel.send("What should be the description of the welcome embed? (Use {mention} for member mention)")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            description = msg.content

            # 5. Banner URL
            await interaction.channel.send("Provide a direct link to the welcome banner image (or type 'none')")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            banner_url = msg.content if msg.content.lower() != 'none' else None

            # 6. Thumbnail URL
            await interaction.channel.send("Provide a direct link to the welcome thumbnail image (or type 'user' for user avatar, 'none' for none)")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            thumbnail_url = msg.content

            # Save Config
            config = self.config_manager.load_config("welcome.json", guild_id=interaction.guild.id)
            config.update({
                "channel_id": str(channel_id),
                "auto_role_id": str(auto_role_id) if auto_role_id else None,
                "banner_url": banner_url,
                "embed": config.get("embed", {})
            })
            config["embed"].update({
                "title": title,
                "description": description,
                "thumbnail_url": thumbnail_url
            })

            self.config_manager.save_config("welcome.json", config, guild_id=interaction.guild.id)
            await interaction.channel.send("Welcome setup complete!")

        except asyncio.TimeoutError:
            await interaction.channel.send("Setup timed out.")

    async def setup_tickets(self, interaction: discord.Interaction):
        await interaction.response.send_message("Ticket Setup started.")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            # 1. Category
            await interaction.channel.send("Enter the Category ID where tickets should be created:")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            category_id = msg.content

            # 2. Staff Role
            await interaction.channel.send("Mention the Staff Role that can see tickets:")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            staff_role_id = msg.role_mentions[0].id if msg.role_mentions else None

            # 3. Transcript Channel
            await interaction.channel.send("Mention the channel for ticket transcripts:")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            transcript_channel_id = msg.channel_mentions[0].id if msg.channel_mentions else None

            # 4. Panel Embed
            await interaction.channel.send("What should be the title of the ticket panel?")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            panel_title = msg.content

            await interaction.channel.send("What should be the description of the ticket panel?")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            panel_description = msg.content

            # Save Config
            config = self.config_manager.load_config("tickets.json", guild_id=interaction.guild.id)
            config.update({
                "categories": {"general": category_id, "report": category_id, "appeal": category_id},
                "staff_role_id": str(staff_role_id) if staff_role_id else None,
                "transcript_channel_id": str(transcript_channel_id) if transcript_channel_id else None,
                "panel_embed": {
                    "title": panel_title,
                    "description": panel_description
                }
            })

            self.config_manager.save_config("tickets.json", config, guild_id=interaction.guild.id)
            await interaction.channel.send("Ticket setup complete! Use /setup_tickets to send the panel.")

        except asyncio.TimeoutError:
            await interaction.channel.send("Setup timed out.")

    async def setup_music(self, interaction: discord.Interaction):
        await interaction.response.send_message("Music Setup started.")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            await interaction.channel.send("Mention the voice channel where music is allowed (or ID):")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            channel_id = msg.channel_mentions[0].id if msg.channel_mentions else msg.content

            config = self.config_manager.load_config("music.json", guild_id=interaction.guild.id)
            config["voice_channel_id"] = str(channel_id)

            self.config_manager.save_config("music.json", config, guild_id=interaction.guild.id)
            await interaction.channel.send("Music setup complete!")

        except asyncio.TimeoutError:
            await interaction.channel.send("Setup timed out.")

    async def setup_jointocreate(self, interaction: discord.Interaction):
        await interaction.response.send_message("Join to Create Setup started.")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            await interaction.channel.send("Enter the ID of the 'Join to Create' voice channel:")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            channel_id = msg.content

            config = self.config_manager.load_config("jointocreate.json", guild_id=interaction.guild.id)
            config["trigger_channel_id"] = str(channel_id)

            self.config_manager.save_config("jointocreate.json", config, guild_id=interaction.guild.id)
            await interaction.channel.send("Join to Create setup complete!")

        except asyncio.TimeoutError:
            await interaction.channel.send("Setup timed out.")

    async def setup_leveling(self, interaction: discord.Interaction):
        await interaction.response.send_message("Leveling Setup started.")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            await interaction.channel.send("Mention the channel for level-up announcements:")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            channel_id = msg.channel_mentions[0].id if msg.channel_mentions else msg.content

            config = self.config_manager.load_config("leveling.json", guild_id=interaction.guild.id)
            config["announcement_channel_id"] = str(channel_id)

            self.config_manager.save_config("leveling.json", config, guild_id=interaction.guild.id)
            await interaction.channel.send("Leveling setup complete!")

        except asyncio.TimeoutError:
            await interaction.channel.send("Setup timed out.")

    async def setup_status(self, interaction: discord.Interaction):
        await interaction.response.send_message("Minecraft Status Setup started.")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            await interaction.channel.send("Enter the Minecraft Server IP:")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            ip = msg.content

            await interaction.channel.send("Mention the channel for the status message:")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            if not msg.channel_mentions:
                 return await interaction.channel.send("No channel mentioned.")
            channel = msg.channel_mentions[0]

            await interaction.channel.send("What should be the title of the status embed?")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            title = msg.content

            config = self.config_manager.load_config("status.json", guild_id=interaction.guild.id)
            config["embed"] = config.get("embed", {})
            config["embed"]["title"] = title
            self.config_manager.save_config("status.json", config, guild_id=interaction.guild.id)

            # Call the status command from Status cog
            status_cog = self.bot.get_cog("Status")
            if status_cog:
                 await status_cog.status_command.callback(status_cog, interaction, ip, channel)
            else:
                 await interaction.channel.send("Status cog not found, but settings saved.")

        except asyncio.TimeoutError:
            await interaction.channel.send("Setup timed out.")

    async def setup_branding(self, interaction: discord.Interaction):
        await interaction.response.send_message("Server Branding Setup started.")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            # 1. Nickname
            await interaction.channel.send("What should be the bot's name in this server?")
            msg = await self.bot.wait_for('message', check=check, timeout=120)
            new_nick = msg.content
            try:
                await interaction.guild.me.edit(nick=new_nick)
            except:
                await interaction.channel.send("Failed to update nickname (check permissions).")

            # 2. Avatar (Global)
            await interaction.channel.send("Provide a link to a new profile picture for the bot (or type 'skip'):")
            msg = await self.bot.wait_for('message', check=check, timeout=120)
            if msg.content.lower() != 'skip':
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(msg.content) as resp:
                            if resp.status == 200:
                                avatar_bytes = await resp.read()
                                await self.bot.user.edit(avatar=avatar_bytes)
                                await interaction.channel.send("Global avatar updated!")
                except Exception as e:
                    await interaction.channel.send(f"Failed to update avatar: {e}")

            # 3. Description
            await interaction.channel.send("What should be the bot's description/bio for this server?")
            msg = await self.bot.wait_for('message', check=check, timeout=120)
            description = msg.content

            # Save to branding.json
            config = self.config_manager.load_config("branding.json", guild_id=interaction.guild.id)
            config["description"] = description
            self.config_manager.save_config("branding.json", config, guild_id=interaction.guild.id)

            # Finalize
            summary = (
                f"**Branding Finalized!**\n"
                f"Nickname: {new_nick}\n"
                f"Description: {description}\n"
            )
            await interaction.channel.send(summary)

        except asyncio.TimeoutError:
            await interaction.channel.send("Setup timed out.")

    @app_commands.command(name="about", description="About this bot")
    async def about(self, interaction: discord.Interaction):
        config = self.config_manager.load_config("branding.json", guild_id=interaction.guild.id)
        description = config.get("description", "I am BrambleBot, your all-in-one Discord assistant!")

        embed = discord.Embed(
            title=f"About {interaction.guild.me.display_name}",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Setup(bot))
