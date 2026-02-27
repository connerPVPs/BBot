import json
import os

class ConfigManager:
    def __init__(self, config_dir="./configs"):
        self.config_dir = config_dir
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

    def load_config(self, filename):
        path = os.path.join(self.config_dir, filename)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding {filename}. Returning empty config.")
            return {}

    def get(self, filename, key, default=None):
        config = self.load_config(filename)
        return config.get(key, default)
