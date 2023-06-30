import os
import datetime
from gspread import Client
from xlsxwriter.utility import xl_col_to_name

import discord

import utils.utils as utl
from cogs.utilities import Utilities
from cogs.ppc import PPC
import scheduler

gc : Client
UI : Utilities
PI = PPC

async def run_schedulers(gclient: Client, Utilities_Instance: Utilities, PPC_Instance: PPC):
    global gc
    global UI
    global PI
    gc = gclient
    UI = Utilities_Instance
    PI = PPC_Instance

    # Add Dates
    add_dates_jobid = 'gb_add_dates'
    if scheduler.global_schdr.get_job(job_id=add_dates_jobid, jobstore='global') is None:
        url = os.getenv('EXALTAIR_SPREADSHEET')
        scheduler.global_schdr.add_job(gb_add_dates_scheduler, 'cron', day_of_week='mon', hour='7', args=[url], jobstore='global', misfire_grace_time=172800, id=add_dates_jobid, replace_existing=True, max_instances=1000)
        await UI.send_logs_to_test_server('Successfully created add_dates scheduler.')
    
    # EXPPC SQLite Populate
    exppc_sqlite_populate_jobid = 'exppc_sqlite_populate'
    if scheduler.global_schdr.get_job(job_id=exppc_sqlite_populate_jobid, jobstore='global') is None:
        scheduler.global_schdr.add_job(exppc_sqlite_populate_scheduler, 'cron', day_of_week='mon', hour='5', jobstore='global', misfire_grace_time=172800, id=exppc_sqlite_populate_jobid, replace_existing=True, max_instances=1000)
        await UI.send_logs_to_test_server('Successfully created exppc_sqlite_populate scheduler.')

async def gb_add_dates_scheduler(url: str):
    sh = gc.open_by_url(url)
    main_ws = sh.worksheet('Main')
    sub_ws = sh.worksheet('Sub')

     # Get the start of this week's date in string
    today = datetime.date.today()
    start_of_week = (today - datetime.timedelta(days=today.weekday())).strftime("%d/%m/%Y")

    exist = True
    ws = [main_ws, sub_ws]

    for s in ws:
        # Get available gb dates
        headers = s.row_values(1)
        gb_dates = headers[5:]
    
        if start_of_week in gb_dates:
            continue
        else:
            exist = False
            s.update_cell(1, 6+len(gb_dates), "'" + start_of_week)
            s.format(f"{xl_col_to_name(5+len(gb_dates))}1", {
                "textFormat": {"bold": True},
                "horizontalAlignment": "LEFT",
                "borders": {
                    "top": {
                        "style": "SOLID"
                    },
                    "bottom": {
                        "style": "SOLID"
                    },
                    "left": {
                        "style": "SOLID"
                    },
                    "right": {
                        "style": "SOLID"
                    }
                }
            })
            requests = {"requests": [
                {
                    "repeatCell": {
                        "cell": {"dataValidation": {"condition": {"type": "BOOLEAN"}}, "userEnteredValue": {"boolValue": False}},
                        "range": {"sheetId": s.id, "startRowIndex": 1, "endRowIndex": 81, "startColumnIndex": 5+len(gb_dates), "endColumnIndex": 6+len(gb_dates)},
                        "fields": "*"
                    }
                }
            ]}
            sh.batch_update(requests)
            emb = utl.make_embed(desc=f"Added a new guild battle date entry for '{start_of_week}'.", color=discord.Colour.green())

    if exist is True:
        emb = utl.make_embed(desc=f"The guild battle date '{start_of_week}' already exist.", color=discord.Colour.red())

    await UI.send_logs_to_test_server(emb=emb)

async def exppc_sqlite_populate_scheduler():
    emb = utl.make_embed(desc='Populating data from spreadsheet...', color=discord.Colour.yellow())
    await UI.send_logs_to_test_server(emb=emb)

    success = await PI.exppc_sqlite_populate_scheduler()

    if success:
        emb = utl.make_embed(desc='Successfully added records to database!', color=discord.Colour.green())
        await UI.send_logs_to_test_server(emb=emb)
    else:
        emb = utl.make_embed(desc='Error during EX-PPC SQLite population!', color=discord.Colour.red())
        await UI.send_logs_to_test_server(emb=emb)