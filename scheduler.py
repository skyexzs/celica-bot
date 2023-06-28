from typing import List
from pytz import utc

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore

from discord import Guild

from pymongo import MongoClient

schdr = None
norman_schdr = None
global_schdr = None

def run_scheduler(mongo_conn, guilds: List[Guild]):
    global schdr
    global norman_schdr
    global global_schdr

    client = MongoClient(mongo_conn)

    jobstores = {}
    norman_jobstores = {}
    client['globalscheduler']['global']
    global_jobstores = {}
    global_jobstores['global'] = MongoDBJobStore(database='globalscheduler', collection='global', client=client)
    for g in guilds:
        client['serverdata'][str(g.id)]
        client['normanscheduler'][str(g.id)]
        jobstores[str(g.id)] = MongoDBJobStore(database='serverdata', collection=str(g.id), client=client)
        norman_jobstores[str(g.id)] = MongoDBJobStore(database='normanscheduler', collection=str(g.id), client=client)

    schdr = AsyncIOScheduler(jobstores=jobstores, timezone=utc)
    schdr.start()

    norman_schdr = AsyncIOScheduler(jobstores=norman_jobstores, timezone=utc)
    norman_schdr.start()

    global_schdr = AsyncIOScheduler(jobstores=global_jobstores, timezone=utc)
    global_schdr.start()