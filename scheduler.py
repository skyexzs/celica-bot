from typing import List
from pytz import utc

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore

from discord import Guild

from pymongo import MongoClient

schdr = None

def run_scheduler(mongo_conn, guilds: List[Guild]):
    global schdr

    client = MongoClient(mongo_conn)

    jobstores = {}
    for g in guilds:
        client['serverdata'][str(g.id)]
        jobstores[str(g.id)] = MongoDBJobStore(database='serverdata', collection=str(g.id), client=client)

    schdr = AsyncIOScheduler(jobstores=jobstores, timezone=utc)
    schdr.start()