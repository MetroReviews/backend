import asyncio
import json
import discord
from discord.ext import commands
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Request
from fastapi.routing import Mount
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin

import piccolo

from . import tables
import inspect

_tables = []

tables_dict = vars(tables)

for obj in tables_dict.values():
    if obj == tables.Table:
        continue
    if inspect.isclass(obj) and isinstance(obj, piccolo.table.TableMetaclass):
        _tables.append(obj)

app = FastAPI(
    routes=[
        Mount(
            "/admin/",
            create_admin(
                tables=_tables,
                site_name="BRC Admin",
                # Required when running under HTTPS:
                # allowed_hosts=['my_site.com']
            ),
        ),
    ],
)

client = commands.Bot(intents=discord.Intents.all(), command_prefix="%")

with open("secrets.json") as f:
    secrets = json.load(f)

@app.on_event("startup")
async def open_database_connection_pool():
    engine = engine_finder()
    asyncio.create_task(client.start(secrets["token"]))
    await engine.start_connnection_pool()


@app.on_event("shutdown")
async def close_database_connection_pool():
    engine = engine_finder()
    await engine.close_connnection_pool()

async def list_auth(list_id: str):
    ...

@app.get("/")
async def brc_index():
    return RedirectResponse("https://github.com/organizations/BotReviewerConsortium")

@app.get("/actions")
async def get_actions():
    """
``list_source`` will not be present if it is not relevant
    """
    return await tables.BotAction.select().order_by(tables.BotAction.action_time, ascending=False)

