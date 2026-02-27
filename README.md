# BrambleSMP Core

A Discord bot for the BrambleSMP Minecraft server. This bot welcomes new members, assigns roles, manages tickets, displays live server status, plays music, manages dynamic voice channels, and tracks user chat levels.

## Features

- **Auto Welcome Embed**: Sends a welcome message with server details and a timestamp when a new user joins.
- **Auto Role Assignment**: Automatically assigns a specified role to new members upon joining.
- **Advanced Ticket System**:
    - **Panel Setup**: Easily deploy a ticket panel using `/setup_tickets`.
    - **Categorized Tickets**: General Support, Bug/User Report, Punishment Appeal.
    - **Private Channels**: Creates a private channel for the user and staff.
    - **Transcripts**: Automatically generates and saves a transcript when a ticket is closed.
- **Live Server Status**:
    - **Status Embed**: Displays real-time player count, version, and online status.
    - **Auto-Update**: Updates the embed every 60 seconds.
- **Advanced Music System**:
    - **Playback**: Plays music from YouTube and Spotify via `/music <name/link>`.
    - **Control Panel**: Buttons for Volume, Pause/Resume, Skip, Previous, and Bass Boost.
    - **AutoPlay**: Automatically queues similar songs.
    - **Voice Channel Lock**: Restricts music commands to a specific voice channel.
- **Join to Create VC**:
    - **Dynamic Creation**: Users joining a specific "Trigger" channel are moved to a new, temporary Voice Channel.
    - **Auto Cleanup**: Temporary channels are deleted when they become empty.
    - **Limits**: Enforces a maximum number of active temporary channels (Default: 7) and user limit per channel (Default: 25).
- **Chat Leveling System**:
    - **XP System**: Users earn XP by chatting. Scaling difficulty ensures early levels are easier.
    - **Level Up Announcements**: Sends a congratulatory embed every 5 levels.
    - **Role Rewards**: Automatically assigns custom roles at levels 25, 50, 75, and 100.
    - **Rank Command**: `/rank` to check current level and progress.

## Prerequisites

- Python 3.8+
- A Discord Bot Token (with Message Content, Server Members, Manage Roles, Manage Channels, and Voice States Intents enabled)
- A **Lavalink Server** (Required for music)

## Installation

1.  Clone the repository or upload files to your server.
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

### Environment Variables (.env)
Create a `.env` file for sensitive tokens:
```env
DISCORD_TOKEN=your_token_here
```

### Feature Configuration (configs/*.json)
All features are configured via simple JSON files in the `configs/` directory.

#### `configs/welcome.json`
Configure the welcome message, channel, and auto-role.
```json
{
    "channel_id": "123456789012345678",
    "auto_role_id": "1472473308459958376",
    "banner_url": "https://example.com/banner.png",
    "embed": { ... }
}
```

#### `configs/tickets.json`
Configure ticket categories, staff roles, and transcripts.
```json
{
    "staff_role_id": "1234567890",
    "transcript_channel_id": "1234567890",
    "categories": { ... },
    "panel_embed": { ... }
}
```

#### `configs/status.json`
Configure the server status embed appearance.
```json
{
    "embed": { ... }
}
```

#### `configs/music.json`
Configure the music system and Lavalink connection.
```json
{
    "voice_channel_id": "1234567890",
    "lavalink": { ... },
    "embed": { ... }
}
```

#### `configs/jointocreate.json`
Configure the dynamic voice channel system.
```json
{
    "trigger_channel_id": "1234567890",
    "max_channels": 7,
    "user_limit": 25,
    "channel_name_format": "{user}'s-VC",
    "error_embed": { ... }
}
```

#### `configs/leveling.json`
Configure the chat leveling system.
```json
{
    "announcement_channel_id": "1234567890",
    "role_rewards": {
        "25": "role_id_25",
        "50": "role_id_50",
        "75": "role_id_75",
        "100": "role_id_100"
    },
    "embed": { ... }
}
```

## Usage

1.  Run the bot:
    ```bash
    python bot.py
    ```
2.  **Commands**:
    -   `/setup_tickets #channel`: Deploy the ticket panel.
    -   `/status <server_ip> #channel`: Create a live server status message.
    -   `/music <query>`: Play a song from YouTube or Spotify.
    -   `/rank [user]`: Check level and XP.

## Deployment

### Pterodactyl Panel

1.  **Upload Files**: Upload all files (excluding `tests/` and `__pycache__`) to your Pterodactyl server file manager.
2.  **Startup Command**: Set the startup command to `python bot.py`.
3.  **Requirements**: Ensure `requirements.txt` is present.
4.  **Lavalink**: You must have a Lavalink server running. Update `configs/music.json` with your node details.

### General Hosting (VPS/Local)

1.  Ensure Python 3.8+ is installed.
2.  Install requirements: `pip install -r requirements.txt`.
3.  Run the bot: `python bot.py`.
