from typing import List

from discord import Guild

from pymongo import MongoClient

class MongoDB():
    def __init__(self, mongo_conn):
        self.client = MongoClient(mongo_conn)
        self.db = self.client['serverdata']
        self.resources = self.client['resources']

    def setup(self, guilds: List[Guild]):
        collist = self.db.list_collection_names()
        for g in guilds:
            if str(g.id) not in collist:
                col = self.db[str(g.id)]
                g_info = {
                    '_id': 'main_info',
                    'guild_name': g.name,
                    'guild_owner': g.owner_id,
                    'created_at': g.created_at,
                    'member_count': g.member_count }
                col.insert_one(g_info)
            else:
                col = self.db[str(g.id)]
                query = { '_id': 'main_info' }
                newvalue = { '$set': { 'member_count': g.member_count, 'guild_name' : g.name } }
                col.update_one(query, newvalue)
    
    async def get_data(self, guild: Guild, query, database: str = None):
        col = self.db[str(guild.id)]

        try:
            if database != None:
                col = self.client[database][str(guild.id)]
            data = col.find(query)[0]
        except:
            data = None

        return data
    
    async def get_multi_data(self, guild: Guild, query, database: str = None) -> list:
        col = self.db[str(guild.id)]

        try:
            if database != None:
                col = self.client[database][str(guild.id)]
            cursor = col.find(query)

            data = []
            for result in cursor:
                data.append(result)
        except:
            data = None

        return data
    
    async def insert_data(self, guild: Guild, query, data, database: str = None):
        col = self.db[str(guild.id)]

        if database != None:
            col = self.client[database][str(guild.id)]
            
        col.update_one(query, data, upsert=True)

    async def insert_many(self, guild: Guild, data, database: str = None):
        col = self.db[str(guild.id)]

        if database != None:
            col = self.client[database][str(guild.id)]
            
        col.insert_many(data, ordered=False, bypass_document_validation=True)

    async def delete_data(self, guild: Guild, query, database: str = None):
        col = self.db[str(guild.id)]

        if database != None:
            col = self.client[database][str(guild.id)]

        col.delete_many(query)
    
    def get_resources(self, collection, query):
        col = self.resources[collection]
        try:
            data = list(col.find(query))
        except:
            data = None
        return data

Mongo_Instance : MongoDB