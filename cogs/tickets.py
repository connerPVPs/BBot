import os
import discord
from discord.ext import commands
from discord import app_commands
from utils.config import ConfigManager

class TicketModal(discord.ui.Modal, title='Ticket Setup'):
    name = discord.ui.TextInput(
        label='Minecraft Username',
        placeholder='e.g. ChristyPanda',
    )

    def __init__(self, category_id, staff_role_id, ticket_embed_config):
        super().__init__()
        self.category_id = int(category_id) if category_id else None
        self.staff_role_id = int(staff_role_id) if staff_role_id else None
        self.ticket_embed_config = ticket_embed_config

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not self.category_id:
             await interaction.followup.send("Error: Ticket category ID not configured.", ephemeral=True)
             return

        category = guild.get_channel(self.category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send(f"Error: Ticket category not found (ID: {self.category_id}).", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        staff_role = guild.get_role(self.staff_role_id) if self.staff_role_id else None
        if staff_role:
             overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        clean_name = "".join(c for c in self.name.value if c.isalnum() or c in "-_").lower()
        channel_name = f"ticket-{clean_name}"

        try:
            ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        except Exception as e:
            await interaction.followup.send(f"Failed to create ticket channel: {e}", ephemeral=True)
            return

        # Use config for embed
        description = self.ticket_embed_config.get("description", "Welcome {user_mention}!").replace("{user_mention}", interaction.user.mention)
        color = self.ticket_embed_config.get("color", discord.Color.blue().value)
        title = self.ticket_embed_config.get("title", "Ticket")

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color(color)
        )

        view = TicketControls()
        await ticket_channel.send(f"{interaction.user.mention} {staff_role.mention if staff_role else ''}", embed=embed, view=view)
        await interaction.followup.send(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

class TicketLauncher(discord.ui.View):
    def __init__(self, config_manager=None):
        super().__init__(timeout=None)
        # We need a way to access config inside the callback.
        # Since this view is persistent and re-created in setup_hook without args usually,
        # we should instantiate ConfigManager inside if not passed?
        # Or better, read fresh config on interaction.
        self.config_manager = config_manager or ConfigManager()

    @discord.ui.select(
        placeholder="Select a Ticket Category",
        options=[
            discord.SelectOption(label="General Support", description="Help regarding the server", value="general"),
            discord.SelectOption(label="Bug/User Report", description="Report players or bugs", value="report"),
            discord.SelectOption(label="Punishment Appeal", description="Appeal for punishments", value="appeal"),
        ],
        custom_id="ticket_launcher_select"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        config = self.config_manager.load_config("tickets.json", guild_id=interaction.guild.id)
        categories = config.get("categories", {})

        category_id = None
        selected = select.values[0]

        if selected in categories:
            category_id = categories[selected]

        staff_role_id = config.get("staff_role_id")

        if not category_id:
             await interaction.response.send_message(f"Error: Category not configured for ticket type '{selected}'. Check tickets.json", ephemeral=True)
             return

        await interaction.response.send_modal(TicketModal(category_id, staff_role_id, config.get("ticket_embed", {})))

class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.config_manager = ConfigManager()

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket_controls_close")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        config = self.config_manager.load_config("tickets.json", guild_id=interaction.guild.id)
        transcript_channel_id = config.get("transcript_channel_id")

        transcript_channel = None
        if transcript_channel_id:
            transcript_channel = interaction.guild.get_channel(int(transcript_channel_id))

        if transcript_channel:
            messages = [message async for message in interaction.channel.history(limit=None, oldest_first=True)]
            content = f"Transcript for {interaction.channel.name}\nGenerated at {discord.utils.utcnow()}\n\n"
            for msg in messages:
                timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
                content += f"[{timestamp}] {msg.author.name} ({msg.author.id}): {msg.content}\n"
                for attachment in msg.attachments:
                    content += f"[{timestamp}] {msg.author.name} (Attachment): {attachment.url}\n"

            file_path = f"{interaction.channel.name}-transcript.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            try:
                await transcript_channel.send(f"Transcript for {interaction.channel.name} (Closed by {interaction.user.name})", file=discord.File(file_path))
            except Exception as e:
                print(f"Failed to send transcript: {e}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        await interaction.channel.delete()

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = ConfigManager()

    @app_commands.command(name="setup_tickets", description="Setup the ticket panel")
    @app_commands.describe(channel="The channel to send the ticket panel to")
    @app_commands.default_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = self.config_manager.load_config("tickets.json", guild_id=interaction.guild.id)
        embed_config = config.get("panel_embed", {})

        embed = discord.Embed(
            title=embed_config.get("title", "Tickets"),
            description=embed_config.get("description", "Select a category below."),
            color=discord.Color(embed_config.get("color", discord.Color.blue().value))
        )
        embed.set_footer(text=embed_config.get("footer", ""))

        await channel.send(embed=embed, view=TicketLauncher(self.config_manager))
        await interaction.response.send_message(f"Ticket panel sent to {channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
