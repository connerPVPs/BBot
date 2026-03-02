import os
import time
import subprocess
import discord
import socket
import sys
from discord.ext import commands
from dotenv import load_dotenv
from cogs.tickets import TicketLauncher, TicketControls
from utils.lavalink_setup import setup_lavalink

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Setup intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

class BrambleBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f"Loaded extension: {filename[:-3]}")

        # Add persistent views
        self.add_view(TicketLauncher())
        self.add_view(TicketControls())
        print("Registered persistent views for Tickets")

        # Sync application commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')

bot = BrambleBot()

def wait_for_lavalink(host='127.0.0.1', port=2333, timeout=60):
    """Wait for Lavalink server to accept connections."""
    start_time = time.time()
    print(f"Waiting for Lavalink on {host}:{port}...")
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                print("Lavalink is ready!")
                return True
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(1)
            continue
        except Exception as e:
            print(f"Error checking Lavalink: {e}")
            return False
            
    print("Timeout waiting for Lavalink.")
    return False

if __name__ == "__main__":
    if TOKEN:
        # Returns path to java executable or None
        java_path = setup_lavalink()
        
        if java_path:
            print(f"Starting Lavalink with {java_path}...")
            
            # Start Lavalink in background, logging to file
            log_file = open("lavalink.log", "w")
            try:
                lavalink_process = subprocess.Popen(
                    [java_path, "-jar", "Lavalink.jar"],
                    cwd="lavalink",
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
                
                # Check if Lavalink starts successfully
                if wait_for_lavalink(timeout=120):
                    try:
                        bot.run(TOKEN)
                    except Exception as e:
                        print(f"Bot runtime error: {e}")
                    finally:
                        print("Stopping Lavalink...")
                        lavalink_process.terminate()
                        try:
                            lavalink_process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            lavalink_process.kill()
                else:
                    print("Failed to connect to Lavalink. Check lavalink.log for details.")
                    # Print tail of log
                    log_file.flush()
                    with open("lavalink.log", "r") as f:
                        print("--- Lavalink Log (Tail) ---")
                        print("".join(f.readlines()[-20:]))
                        print("---------------------------")
                    lavalink_process.terminate()
            except Exception as e:
                 print(f"Failed to start Lavalink process: {e}")
            finally:
                log_file.close()

        else:
            print("Failed to setup Lavalink.")
    else:
        print("Error: DISCORD_TOKEN not found in environment variables.")