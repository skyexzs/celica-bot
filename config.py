import os
import json
from discord import Guild
from pathlib import Path

MAIN_PATH = ""
CONFIG_FOLDER = "configs"

default_config = {
    "guild_id": "",
    "guild_name": "",
    "command_prefix": "."
}

class Config():
    @staticmethod
    def read_config(guild: Guild):
        config_file = os.path.join(MAIN_PATH, CONFIG_FOLDER, str(guild.id) + ".json")
        if (not(os.path.isfile(config_file))):
            Config.write_default(guild)

        with open(os.path.join(MAIN_PATH, CONFIG_FOLDER, str(guild.id) + ".json"), 'r') as f:
            data = json.load(f)
            return data

    @staticmethod
    def write_config(guild: Guild, data):
        config_file = os.path.join(MAIN_PATH, CONFIG_FOLDER, str(guild.id) + ".json")
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def write_default(guild: Guild):
        config_file = os.path.join(MAIN_PATH, CONFIG_FOLDER, str(guild.id) + ".json")

        config_copy = default_config.copy()
        config_copy["guild_id"] = guild.id
        config_copy["guild_name"] = guild.name

        with open(config_file, 'w') as f:
            json.dump(config_copy, f, indent=2)
    
    @staticmethod
    def check_folder():
        p = Path(os.path.join(MAIN_PATH, CONFIG_FOLDER))
        p.mkdir(parents=True, exist_ok=True)
