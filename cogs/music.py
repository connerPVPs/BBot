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

    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self.get_player(interaction)
        if not player:
            await interaction.response.send_message("No active player found.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            await player.stop()
            player.queue.clear()
            await interaction.followup.send("Stopped and queue cleared!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error stopping: {e}", ephemeral=True)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config("music.json")
        self.now_playing_msg: dict[int, discord.Message] = {}

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

        guild_id = payload.player.guild.id
        track = payload.track

        embed_config = self.config.get("embed", {})
        embed = discord.Embed(
            title=embed_config.get("title", "Now Playing"),
            description=f"[{track.title}]({track.uri}) by {track.author}",
            color=discord.Color(embed_config.get("color", discord.Color.blue().value))
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        view = MusicControls()

        # Try to update the old message
        old_msg = self.now_playing_msg.get(guild_id)
        if old_msg:
            try:
                await old_msg.edit(embed=embed, view=view)
                return
            except discord.HTTPException:
                # If editing fails (e.g., message deleted), send a new one
                pass

        # If no old message or editing failed, send a new one
        # Note: we need the context or channel to send the message.
        # We'll store the home channel in the player for this purpose.
        channel = getattr(payload.player, "home_channel", None)
        if channel:
            new_msg = await channel.send(embed=embed, view=view)
            self.now_playing_msg[guild_id] = new_msg

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        print(f"Track ended: {payload.track.title} - Reason: {payload.reason}")
        if not payload.player.queue.is_empty:
            next_track = payload.player.queue.get()
            await payload.player.play(next_track)

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
                # Clear tracking message
                self.now_playing_msg.pop(member.guild.id, None)

    @app_commands.command(name="play", description="Play music from YouTube or Spotify")
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

        # Store interaction channel to send now playing updates later
        player.home_channel = interaction.channel

        if not player.playing:
            await player.play(player.queue.get(), volume=100)
            await interaction.followup.send(f"Now playing: {track.title}", ephemeral=True)
        else:
            await interaction.followup.send(f"Added to queue: {track.title}")

    @app_commands.command(name="join", description="Join your voice channel")
    async def join_vc(self, interaction: discord.Interaction):
        if not interaction.user.voice:
             return await interaction.response.send_message("You must be in a voice channel!", ephemeral=True)

        channel = interaction.user.voice.channel
        player = cast(wavelink.Player, interaction.guild.voice_client)

        if player:
            if player.channel.id == channel.id:
                 return await interaction.response.send_message("Already in your channel!", ephemeral=True)
            await player.move_to(channel)
            return await interaction.response.send_message(f"Moved to {channel.name}")

        await channel.connect(cls=wavelink.Player, self_deaf=True)
        await interaction.response.send_message(f"Joined {channel.name}")

    @app_commands.command(name="leave", description="Disconnect from voice channel")
    async def leave_vc(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
             return await interaction.response.send_message("Not in a voice channel!", ephemeral=True)

        await player.disconnect()
        self.now_playing_msg.pop(interaction.guild.id, None)
        await interaction.response.send_message("Disconnected!")

    @app_commands.command(name="pause", description="Pause the current song")
    async def pause_song(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player or not player.playing:
             return await interaction.response.send_message("Nothing is playing!", ephemeral=True)

        await player.pause(True)
        await interaction.response.send_message("Paused!")

    @app_commands.command(name="resume", description="Resume the current song")
    async def resume_song(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player or not player.paused:
             return await interaction.response.send_message("Not paused!", ephemeral=True)

        await player.pause(False)
        await interaction.response.send_message("Resumed!")

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip_song(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player or not player.playing:
             return await interaction.response.send_message("Nothing is playing!", ephemeral=True)

        await player.skip(force=True)
        await interaction.response.send_message("Skipped!")

    @app_commands.command(name="stop", description="Stop music and clear queue")
    async def stop_music(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
             return await interaction.response.send_message("Not in a voice channel!", ephemeral=True)

        await player.stop()
        player.queue.clear()
        await interaction.response.send_message("Stopped and queue cleared!")

    @app_commands.command(name="queue", description="Show the current queue")
    async def show_queue(self, interaction: discord.Interaction):
        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
             return await interaction.response.send_message("Not in a voice channel!", ephemeral=True)

        if player.queue.is_empty:
             return await interaction.response.send_message("Queue is empty.")

        queue_list = "\n".join([f"{i+1}. {track.title}" for i, track in enumerate(player.queue)])
        await interaction.response.send_message(f"**Current Queue:**\n{queue_list}")

async def setup(bot):
    await bot.add_cog(Music(bot))
