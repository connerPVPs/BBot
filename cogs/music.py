import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from utils.config import ConfigManager
import asyncio
import traceback
from typing import cast

class MusicControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @property
    def player(self) -> wavelink.Player | None:
        """Dynamically retrieve the player from the interaction context if possible, 
        but View doesn't store context easily. 
        Instead, we will rely on the fact that the view is attached to a message in a guild."""
        return None

    async def get_player(self, interaction: discord.Interaction) -> wavelink.Player | None:
        if not interaction.guild:
            return None
        return cast(wavelink.Player, interaction.guild.voice_client)

    @discord.ui.button(label="⏸️/▶️", style=discord.ButtonStyle.blurple, custom_id="music_pause")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self.get_player(interaction)
        if not player:
            await interaction.response.send_message("No active player found.", ephemeral=True)
            return
            
        await interaction.response.defer()
        try:
            await player.pause(not player.paused)
        except Exception as e:
            await interaction.followup.send(f"Error toggling pause: {e}", ephemeral=True)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.blurple, custom_id="music_skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self.get_player(interaction)
        if not player:
            await interaction.response.send_message("No active player found.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            await player.skip(force=True)
            await interaction.followup.send("Skipped!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error skipping: {e}", ephemeral=True)

    @discord.ui.button(label="🔊+", style=discord.ButtonStyle.green, custom_id="music_vol_up")
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self.get_player(interaction)
        if not player:
            await interaction.response.send_message("No active player found.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            new_vol = min(player.volume + 10, 1000)
            await player.set_volume(new_vol)
            await interaction.followup.send(f"Volume: {new_vol}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error setting volume: {e}", ephemeral=True)

    @discord.ui.button(label="🔊-", style=discord.ButtonStyle.green, custom_id="music_vol_down")
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self.get_player(interaction)
        if not player:
            await interaction.response.send_message("No active player found.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            new_vol = max(player.volume - 10, 0)
            await player.set_volume(new_vol)
            await interaction.followup.send(f"Volume: {new_vol}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error setting volume: {e}", ephemeral=True)

    @discord.ui.button(label="🎸 Bass", style=discord.ButtonStyle.primary, custom_id="music_bass")
    async def toggle_bass(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self.get_player(interaction)
        if not player:
            await interaction.response.send_message("No active player found.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            filters: wavelink.Filters = player.filters
            # Simplified equalizer check for Wavelink 3.x
            # We check if any band has a non-zero gain
            is_boosted = any(band.get('gain', 0) > 0 for band in filters.equalizer.payload) if filters.equalizer.payload else False

            if is_boosted:
                 filters.equalizer.reset()
                 await interaction.followup.send("Bass boost disabled.", ephemeral=True)
            else:
                 filters.equalizer.set(bands=[{'band': 0, 'gain': 0.25}, {'band': 1, 'gain': 0.25}])
                 await interaction.followup.send("Bass boost enabled.", ephemeral=True)

            await player.set_filters(filters)
        except Exception as e:
            await interaction.followup.send(f"Error toggling bass: {e}", ephemeral=True)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config("music.json")

    async def cog_load(self):
        lavalink_conf = self.config.get("lavalink", {})
        if not lavalink_conf:
            print("Lavalink config missing in music.json")
            return

        host = lavalink_conf.get('host')
        port = lavalink_conf.get('port')
        password = lavalink_conf.get("password")
        is_secure = lavalink_conf.get("secure", False)
        
        protocol = "https" if is_secure else "http"
        uri = f"{protocol}://{host}:{port}"
        
        try:
            node = wavelink.Node(
                identifier="Main",
                uri=uri,
                password=password
            )

            await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)
            print(f"Connecting to Lavalink node: {uri}")
        except Exception as e:
            print(f"Failed to initiate Lavalink connection: {e}")

        # Add persistent view
        self.bot.add_view(MusicControls())
        print("Registered persistent view for MusicControls")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Lavalink Node connected: {payload.node.identifier} | Resumed: {payload.resumed}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        print(f"Track started: {payload.track.title} in {payload.player.guild.name}")
        # Force volume set on start to ensure audio is heard
        await payload.player.set_volume(100)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        print(f"Track ended: {payload.track.title} - Reason: {payload.reason}")

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        print(f"Track exception: {payload.exception}")

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload: wavelink.TrackStuckEventPayload):
        print(f"Track stuck: {payload.track.title}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.id == self.bot.user.id:
            return

        # Check if the bot is in a voice channel
        voice_client: wavelink.Player = cast(wavelink.Player, member.guild.voice_client)
        if not voice_client:
            return

        # If the channel the bot is in was left
        if before.channel and before.channel.id == voice_client.channel.id:
            # If the bot is the only one left in the channel
            if len(before.channel.members) == 1:
                await voice_client.disconnect()
                print(f"Left empty voice channel in {member.guild.name}")

    @app_commands.command(name="music", description="Play music from YouTube or Spotify")
    @app_commands.describe(query="Name or URL of the song")
    async def play_music(self, interaction: discord.Interaction, query: str):
        allowed_channel_id = self.config.get("voice_channel_id")

        if not interaction.user.voice:
            await interaction.response.send_message("You must be in a voice channel!", ephemeral=True)
            return

        user_channel = interaction.user.voice.channel

        if allowed_channel_id and str(user_channel.id) != str(allowed_channel_id):
             await interaction.response.send_message(f"Music can only be played in <#{allowed_channel_id}>", ephemeral=True)
             return

        await interaction.response.defer()

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            try:
                # Explicitly self_deaf=True as per best practices
                player = await user_channel.connect(cls=wavelink.Player, self_deaf=True, self_mute=False)
            except Exception as e:
                await interaction.followup.send(f"Failed to join voice channel: {e}")
                return
        
        # Ensure we are in the same channel as the user
        if player.channel.id != user_channel.id:
             await player.move_to(user_channel)

        player.autoplay = wavelink.AutoPlayMode.enabled

        try:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
        except Exception as e:
             await interaction.followup.send(f"Error searching track: {e}")
             return

        if not tracks:
            await interaction.followup.send("No tracks found.")
            return

        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)

        if not player.playing:
            await player.play(player.queue.get(), volume=100)

        embed_config = self.config.get("embed", {})
        embed = discord.Embed(
            title=embed_config.get("title", "Now Playing"),
            description=f"[{track.title}]({track.uri}) by {track.author}",
            color=discord.Color(embed_config.get("color", discord.Color.blue().value))
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        # Do not pass player to view, it will fetch it dynamically
        await interaction.followup.send(embed=embed, view=MusicControls())

async def setup(bot):
    await bot.add_cog(Music(bot))
