import asyncio
import datetime
import json
import aiohttp
import discord
from discord.ext import commands
from fastapi.responses import RedirectResponse, ORJSONResponse
from fastapi.security.api_key import APIKeyHeader
from fastapi import Depends, FastAPI, Request
from fastapi.routing import Mount
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin

import piccolo
import pydantic

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

bot = commands.Bot(intents=discord.Intents.all(), command_prefix="%")

with open("secrets.json") as f:
    secrets = json.load(f)
    secrets["gid"] = int(secrets["gid"])
    secrets["reviewer"] = int(secrets["reviewer"])
    secrets["queue_channel"] = int(secrets["queue_channel"])

@app.on_event("startup")
async def open_database_connection_pool():
    engine = engine_finder()
    asyncio.create_task(bot.start(secrets["token"]))
    await bot.load_extension("jishaku")
    await engine.start_connnection_pool()


@app.on_event("shutdown")
async def close_database_connection_pool():
    engine = engine_finder()
    await engine.close_connnection_pool()

@app.get("/")
async def brc_index():
    return RedirectResponse("https://github.com/organizations/BotReviewerConsortium")

@app.get("/actions")
async def get_actions():
    """
``list_source`` will not be present if it is not relevant
    """
    actions = await tables.BotAction.select().order_by(tables.BotAction.action_time, ascending=False)

    for action in actions:
        action["bot_id"] = str(action["bot_id"])
    
    return actions

class BotPost(pydantic.BaseModel):
    bot_id: str
    list_id: int
    username: str
    description: str 
    long_description: str
    website: str | None = None
    github: str | None = None
    privacy_policy: str | None = None
    banner: str | None = None
    invite: str | None = None
    extra_links: dict[str, str] | None = {}

auth_header = APIKeyHeader(name='Authorization')

@app.get("/bots")
async def get_queue():
    """
``list_source`` will not be present if it is not relevant
    """
    bots = await tables.BotQueue.select().order_by(tables.BotQueue.bot_id, ascending=True)

    for bot in bots:
        bot["bot_id"] = str(bot["bot_id"])
    
    return bots

@app.post("/bots")
async def post_bots(request: Request, _bot: BotPost, auth: str = Depends(auth_header)):
    list = await tables.BotList.select(tables.BotList.secret_key).where(tables.BotList.id == _bot.list_id).first()
    if not list:
        return ORJSONResponse({"error": "List not found"}, status_code=404)
    if auth != list["secret_key"]:
        return ORJSONResponse({"error": "Invalid secret key"}, status_code=401)
    
    try:
        bot_id = int(_bot.bot_id)
    except:
        return ORJSONResponse({"error": "Invalid bot id"}, status_code=400)

    curr_bot = await tables.BotQueue.select(tables.BotQueue.bot_id).where(tables.BotQueue.bot_id == bot_id)

    if len(curr_bot) > 0:
        return ORJSONResponse({"error": "Bot already in queue"}, status_code=400)

    await tables.BotQueue.insert(
        tables.BotQueue(
            bot_id=bot_id, 
            username=_bot.username, 
            list_source=_bot.list_id,
            description=_bot.description,
            long_description=_bot.long_description,
            website=_bot.website,
            github=_bot.github,
            privacy_policy=_bot.privacy_policy,
            banner=_bot.banner,
            invite=_bot.invite,
            extra_links=_bot.extra_links,
            state=tables.State.PENDING
        )
    )

    # TODO: Add bot add propogation in final scope plans if this is successful
    embed = discord.Embed(title="Bot Added To Queue", description=f"**Bot ID**: {bot_id}\n**Username:** {_bot.username}", color=discord.Color.green())
    c = bot.get_channel(secrets["queue_channel"])
    await c.send(f"<@&{secrets['reviewer']}>", embed=embed)

class FSnowflake():
    """Blame discord"""
    def __init__(self, id):
        self.id: int = id

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def support(interaction: discord.Interaction):
    """Show the link to support"""
    await interaction.response.send_message("https://github.com/BotReviewerConsortium/support")

async def post_act(
    interaction: discord.Interaction, 
    list_info: dict, 
    action: tables.Action,
    key: str,
    bot_id: int,
    reason: str
):
    if not isinstance(interaction.user, discord.Member):
        return

    if not discord.utils.get(interaction.user.roles, id=secrets["reviewer"]) or interaction.guild_id != secrets["gid"]:
        return await interaction.response.send_message("You must have the `Reviewer` role to use this command.")

    msg = f"**{action.name.title()}!**\n"

    await interaction.response.defer()
    for list in list_info:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                list[key], 
                headers={"Authorization": list["secret_key"], "User-Agent": "Frostpaw/0.1"}, 
                json={"bot_id": str(bot_id), "reason": reason or "STUB_REASON", "reviewer": str(interaction.user.id)}
            ) as resp:
                msg += f"{list['name']} -> {resp.status}"
                try:
                    json_d = await resp.json()
                except Exception as exc:
                    json_d = f"JSON deser failed {exc}"
                msg += f" ({json_d})\n"
    
    # Post intent to actions
    await tables.BotAction.insert(
        tables.BotAction(bot_id=bot_id, action=action, action_time=datetime.datetime.now(), list_source=None)
    )
    
    embed = discord.Embed(title="Bot Info", description=f"**Bot ID**: {bot_id}\n\n**Reason:** {reason}", color=discord.Color.green())

    await interaction.followup.send(msg, embeds=[embed])

class Claim(discord.ui.Modal, title='Claim Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.claim_bot_api, tables.BotList.secret_key)

        return await post_act(interaction, list_info, tables.Action.CLAIM, "claim_bot_api", bot_id, "STUB_REASON")

class Unclaim(discord.ui.Modal, title='Unclaim Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.unclaim_bot_api, tables.BotList.secret_key)

        return await post_act(interaction, list_info, tables.Action.UNCLAIM, "unclaim_bot_api", bot_id, self.reason.value)


class Approve(discord.ui.Modal, title='Approve Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.approve_bot_api, tables.BotList.secret_key)

        return await post_act(interaction, list_info, tables.Action.APPROVE, "approve_bot_api", bot_id, self.reason.value)

class Deny(discord.ui.Modal, title='Deny Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.deny_bot_api, tables.BotList.secret_key)

        return await post_act(interaction, list_info, tables.Action.DENY, "deny_bot_api", bot_id, self.reason.value)


@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def claim(interaction: discord.Interaction):
    """Claim a bot"""
    return await interaction.response.send_modal(Claim())

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def unclaim(interaction: discord.Interaction):
    """Unclaims a bot"""
    return await interaction.response.send_modal(Unclaim())

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def approve(interaction: discord.Interaction):
    """Approves a bot"""
    return await interaction.response.send_modal(Approve())

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def deny(interaction: discord.Interaction):
    """Approves a bot"""
    return await interaction.response.send_modal(Deny())

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def sync(interaction: discord.Interaction):
    await bot.tree.sync(guild=FSnowflake(id=secrets["gid"]))

@bot.event
async def on_ready():
    print("Client is now ready and up")
    await bot.tree.sync()
    await bot.tree.sync(guild=FSnowflake(id=secrets["gid"]))
    for cmd in bot.tree.walk_commands():
        print(cmd.name)