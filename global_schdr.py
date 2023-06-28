import os
import datetime
import gspread
from gspread import Client
from xlsxwriter.utility import xl_col_to_name
from cogs.utilities import Utilities

import discord

import utils.utils as utl
import scheduler

UI : Utilities

async def run_schedulers(gc: Client, Utilities_Instance: Utilities):
    UI = Utilities_Instance
    add_dates_jobid = 'gb_add_dates'
    if scheduler.global_schdr.get_job(job_id=add_dates_jobid) is None:
        now = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=8)))
        next_time = now + datetime.timedelta(days=1)
        end_time = now + datetime.timedelta(days=2, hours=1)
        scheduler.global_schdr.add_job(gb_add_dates_scheduler, 'cron', day_of_week='mon', hour='7', args=[gc], misfire_grace_time=172800, id=add_dates_jobid, replace_existing=True, max_instances=1000)
        await UI.send_logs_to_test_server('Successfully created add_dates scheduler.')

async def gb_add_dates_scheduler(gc: Client):
    sh = gc.open_by_url(os.getenv('EXALTAIR_SPREADSHEET'))
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

