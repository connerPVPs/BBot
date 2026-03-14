import json
import os

class ConfigManager:
    def __init__(self, config_dir="./configs"):
        self.config_dir = config_dir
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

    def load_config(self, filename, guild_id=None):
        if guild_id:
            guild_dir = os.path.join(self.config_dir, "guilds", str(guild_id))
            if not os.path.exists(guild_dir):
                os.makedirs(guild_dir)
            path = os.path.join(guild_dir, filename)

            # If guild config doesn't exist, try to load default
            if not os.path.exists(path):
                default_path = os.path.join(self.config_dir, filename)
                if not os.path.exists(default_path):
                    return {}
                try:
                    with open(default_path, "r") as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    return {}
        else:
            path = os.path.join(self.config_dir, filename)
            if not os.path.exists(path):
                return {}

        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding {filename}. Returning empty config.")
            return {}

    def save_config(self, filename, config, guild_id=None):
        if guild_id:
            guild_dir = os.path.join(self.config_dir, "guilds", str(guild_id))
            if not os.path.exists(guild_dir):
                os.makedirs(guild_dir)
            path = os.path.join(guild_dir, filename)
        else:
            path = os.path.join(self.config_dir, filename)

        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving {filename}: {e}")
            return False

    def get(self, filename, key, default=None, guild_id=None):
        config = self.load_config(filename, guild_id=guild_id)
        return config.get(key, default)
