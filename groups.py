import os
import json
from discord import Guild
from pathlib import Path
from datetime import datetime

MAIN_PATH = ""
GROUPS_FOLDER = "groups"

default_groups = {
    "created_on": "",
    "groups": [],
    "leftovers": []
}

class Groups():
    @staticmethod
    def read_groups(guild: Guild, date: str):
        Groups.check_groups_folder(guild)
        groups_file = os.path.join(MAIN_PATH, GROUPS_FOLDER, str(guild.id), date + ".json")

        if (not(os.path.isfile(groups_file))):
            return None
        else:
            with open(groups_file, 'r') as f:
                data = json.load(f)
                return data
    
    @staticmethod
    def insert_groups(guild: Guild, date: str, key: str, val):
        Groups.check_groups_folder(guild)
        data = Groups.read_groups(guild, date)
        data[key] = val
        Groups.write_groups(guild, date, data)

    @staticmethod
    def write_groups(guild: Guild, date: str, data):
        Groups.check_groups_folder(guild)
        groups_file = os.path.join(MAIN_PATH, GROUPS_FOLDER, str(guild.id), date + ".json")
        with open(groups_file, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def write_default(guild: Guild, date: str):
        Groups.check_groups_folder(guild)
        groups_file = os.path.join(MAIN_PATH, GROUPS_FOLDER, str(guild.id), date + ".json")

        # datetime object containing current date and time
        now = datetime.now()
        # dd/mm/YY H:M:S
        dt_string = now.strftime("%a, %d/%m/%Y %H:%M:%S UTC+11")

        groups_copy = default_groups.copy()
        groups_copy["created_on"] = dt_string

        with open(groups_file, 'w') as f:
            json.dump(groups_copy, f, indent=2)
    
    @staticmethod
    def list_groups(guild: Guild):
        Groups.check_groups_folder(guild)
        return os.listdir(os.path.join(MAIN_PATH, GROUPS_FOLDER, str(guild.id)))

    @staticmethod
    def check_folder():
        p = Path(os.path.join(MAIN_PATH, GROUPS_FOLDER))
        p.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def check_groups_folder(guild: Guild):
        p = Path(os.path.join(MAIN_PATH, GROUPS_FOLDER, str(guild.id)))
        p.mkdir(parents=True, exist_ok=True)
