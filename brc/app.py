import asyncio
import datetime
import json
import uuid
import aiohttp
import discord
import secrets as _secrets
from discord.ext import commands
from fastapi.responses import HTMLResponse, ORJSONResponse
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
                production=True,
                # Required when running under HTTPS:
                allowed_hosts=['metrobots.xyz']
            ),
        ),
    ],
)

with open("site.html") as site:
    site_html = site.read()

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
    return HTMLResponse(site_html)

@app.get("/lists")
async def get_all_lists():
    return await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state).order_by(tables.BotList.id, ascending=True)

class BotPost(pydantic.BaseModel):
    bot_id: str
    username: str
    banner: str | None = None
    description: str 
    long_description: str
    website: str | None = None
    invite: str | None = None
    owner: str
    extra_owners: list[str]
    support: str | None = None
    donate: str | None = None
    library: str | None = None
    nsfw: bool | None = False
    prefix: str | None = None
    tags: list[str] | None = None
    review_note: str | None = None

class Bot(BotPost):
    state: tables.State
    list_source: uuid.UUID
    added_at: datetime.datetime

class ListUpdate(pydantic.BaseModel):
    name: str | None = None
    claim_bot_api: str | None = None
    unclaim_bot_api: str | None = None
    approve_bot_api: str | None = None
    deny_bot_api: str | None = None
    reset_secret_key: bool = False

auth_header = APIKeyHeader(name='Authorization')

@app.patch("/lists/{list_id}")
async def update_list(list_id: uuid.UUID, update: ListUpdate, auth: str = Depends(auth_header)):
    if (auth := await _auth(list_id, auth)):
        return auth 
    
    has_updated = 0

    if update.name:
        await tables.BotList.update(name=update.name).where(tables.BotList.id == list_id)
        has_updated += 1
    if update.claim_bot_api:
        await tables.BotList.update(claim_bot_api=update.claim_bot_api).where(tables.BotList.id == list_id)
        has_updated += 1
    if update.unclaim_bot_api:
        await tables.BotList.update(unclaim_bot_api=update.unclaim_bot_api).where(tables.BotList.id == list_id)
        has_updated += 1
    if update.approve_bot_api:
        await tables.BotList.update(approve_bot_api=update.approve_bot_api).where(tables.BotList.id == list_id)
        has_updated += 1
    if update.deny_bot_api:
        await tables.BotList.update(deny_bot_api=update.deny_bot_api).where(tables.BotList.id == list_id)
        has_updated += 1
    
    if has_updated and update.reset_secret_key:
        return ORJSONResponse({"error": "Cannot reset secret key while updating other fields"}, status_code=400)
    elif update.reset_secret_key:
        key = _secrets.token_urlsafe()
        await tables.BotList.update(secret_key=key).where(tables.BotList.id == list_id)
        return {"secret_key": key}
    return {"has_updated": has_updated}

@app.get("/bots/{id}", response_model=Bot)
async def get_bot(id: int) -> Bot:
    return await tables.BotQueue.select().where(tables.BotQueue.bot_id == id).first()

@app.get("/bots", response_model=list[Bot])
async def get_queue(list_id: uuid.UUID, auth: str = Depends(auth_header)) -> list[Bot]:
    if (auth := await _auth(list_id, auth)):
        return auth 

    return await tables.BotQueue.select().order_by(tables.BotQueue.bot_id, ascending=True)

class Action(pydantic.BaseModel):
    id: int
    bot_id: str
    action: tables.Action
    reason: str
    reviewer: str 
    action_time: datetime.datetime
    list_source: uuid.UUID

@app.get("/actions", response_model=list[Action])
async def get_actions(offset: int = 0, limit: int = 50) -> list[Action]:
    """
Returns a list of review action (such as claim bot, unclaim bot, approve bot and deny bot etc.)

``list_source`` will not be present in all cases.

**This is purely to allow Metro Review lists to debug their code**

Paginated using ``limit`` (how many rows to return at maximum) and ``offset`` (how many rows to skip). Maximum limit is 200
    """
    if limit > 200:
        return []
    return await tables.BotAction.select().limit(limit).offset(offset).order_by(tables.BotAction.action_time, ascending=False)
    
good_states = (tables.ListState.PENDING_API_SUPPORT, tables.ListState.SUPPORTED)

async def _auth(list_id: uuid.UUID, key: str) -> ORJSONResponse | None:
    list = await tables.BotList.select(tables.BotList.secret_key, tables.BotList.state).where(tables.BotList.id == list_id).first()
    if not list:
        return ORJSONResponse({"error": "List not found"}, status_code=404)
    if key != list["secret_key"]:
        return ORJSONResponse({"error": "Invalid secret key"}, status_code=401)
    
    if list["state"] not in good_states:
        return ORJSONResponse({"error": "List blacklisted, defunct or in an unknown state"}, status_code=401)

emotes = {
    "id": "<:idemote:912034927443320862>",
    "bot": "<:bot:970349895829561420>",
    "crown": "<:owner:912356178833596497>",
    "invite": "<:plus:912363980490702918>",
    "note": "<:activity:912031377422172160>" 
}

@app.post("/bots")
async def post_bots(request: Request, _bot: BotPost, list_id: uuid.UUID, auth: str = Depends(auth_header)):
    """
All optional fields are actually *optional* and does not need to be posted

``extra_owners`` should be a empty list if you do not support it
    """
    if (auth := await _auth(list_id, auth)):
        return auth 
    
    rem = []
    
    try:
        bot_id = int(_bot.bot_id)
        owner = int(_bot.owner)
        extra_owners = [int(v) for v in _bot.extra_owners]
    except:
        return ORJSONResponse({"error": "Invalid bot fields"}, status_code=400)
    
    if _bot.banner:
        if not _bot.banner.startswith("https://"):
            _bot.banner = bot.banner.replace("http://", "https://")
            if not _bot.banner.startswith("https://"):
                # We tried working around it, now we just remove the bad banner
                _bot.banner = None
                rem.append("banner")
    if _bot.website:
        if not _bot.website.startswith("https://"):
            _bot.website = _bot.website.replace("http://", "https://")
            if not _bot.website.startswith("https://"):
                # We tried working around it, now we just remove the bad website
                _bot.website = None
                rem.append("website")
    
    if _bot.support:
        if not _bot.support.startswith("https://"):
            _bot.support = _bot.support.replace("http://", "https://")
            if not _bot.support.startswith("https://"):
                # We tried working around it, now we just remove the bad support
                _bot.support = None
                rem.append("support")
    
    # Default
    if _bot.tags:
        _bot.tags.append("utility")
    else:
        _bot.tags = ["utility"]

    curr_bot = await tables.BotQueue.select(tables.BotQueue.bot_id).where(tables.BotQueue.bot_id == bot_id)

    if len(curr_bot) > 0:
        return ORJSONResponse({"error": "Bot already in queue"}, status_code=400)

    if _bot.invite and not _bot.invite.startswith("https://"):
        # Just remove bad invite
        _bot.invite = None
        rem.append("invite")

    await tables.BotQueue.insert(
        tables.BotQueue(
            bot_id=bot_id, 
            username=_bot.username, 
            banner=_bot.banner,
            list_source=list_id,
            description=_bot.description,
            long_description=_bot.long_description,
            website=_bot.website,
            invite=_bot.invite,
            owner=owner,
            support=_bot.support,
            donate=_bot.donate,
            library=_bot.library,
            nsfw=_bot.nsfw,
            prefix=_bot.prefix,
            tags=_bot.tags,
            review_note=_bot.review_note,
            extra_owners=extra_owners,
            state=tables.State.PENDING
        )
    )

    if not _bot.invite:
        invite = f"https://discordapp.com/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands&permissions=0"
    else:
        invite = _bot.invite

    # TODO: Add bot add propogation in final scope plans if this is successful
    embed = discord.Embed(title="Bot Added To Queue", description=f"{emotes['id']} {bot_id}\n{emotes['bot']} {_bot.username}\n{emotes['crown']} {_bot.owner} (<@{_bot.owner}>)\n{emotes['invite']} [Invite]({invite})\n{emotes['note']} {_bot.review_note or 'No review notes for this bot'}", color=discord.Color.green())
    c = bot.get_channel(secrets["queue_channel"])
    await c.send(f"<@&{secrets['test_ping_role'] or secrets['reviewer']}>", embed=embed)
    return {"removed": rem}

class PrefixSupport(discord.ui.View):
    def __init__(self, modal: discord.ui.Modal):
        self.modal = modal()
        super().__init__(timeout=180)

    @discord.ui.button(label="Click Here")
    async def click_here(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(self.modal)

# Decorator to auto add legacy prefix support
def mr_command(modal_class):
    def wrapper(f):
        @bot.command(name=f.__name__, help=f.__doc__)
        async def _(ctx: commands.Context):
            await ctx.send("To continue, click the below button", view=PrefixSupport(modal_class))
        return f
    return wrapper

class FSnowflake():
    """Blame discord"""
    def __init__(self, id):
        self.id: int = id

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def sync(interaction: discord.Interaction):
    """Syncs all commands"""
    await bot.tree.sync(guild=FSnowflake(id=secrets["gid"]))
    return await interaction.response.send_message("Done syncing")

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
    
    bot_data = await tables.BotQueue.select().where(tables.BotQueue.bot_id == bot_id).first()

    if not bot_data:
        return await interaction.response.send_message(f"This bot (`{bot_id}`) cannot be found")        

    if action == tables.Action.CLAIM and bot_data["state"] != tables.State.PENDING:
        return await interaction.response.send_message("This bot cannot be claimed as it is not pending review?")
    elif action == tables.Action.UNCLAIM and bot_data["state"] != tables.State.UNDER_REVIEW:
        return await interaction.response.send_message("This bot cannot be unclaimed as it is not under review?")

    if action == tables.Action.CLAIM:
        cls = tables.State.UNDER_REVIEW
    elif action == tables.Action.UNCLAIM:
        cls = tables.State.PENDING
    elif action == tables.Action.APPROVE:
        cls = tables.State.APPROVED
    elif action == tables.Action.DENY:
        cls = tables.State.DENIED
    
    await tables.BotQueue.update(state=cls).where(tables.BotQueue.bot_id == bot_id)

    msg = f"**{action.name.title()}!**\n"

    await interaction.response.defer()
    for list in list_info:
        if list["state"] not in good_states:
            continue
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(
                    list[key], 
                    headers={"Authorization": list["secret_key"], "User-Agent": "Frostpaw/0.1"}, 
                    json=bot_data | {"reason": reason or "STUB_REASON", "reviewer": str(interaction.user.id)} | {"added_at": str(bot_data["added_at"]), "list_source": str(bot_data["list_source"])}
                ) as resp:
                    msg += f"{list['name']} -> {resp.status}"
                    try:
                        json_d = await resp.json()
                    except Exception as exc:
                        json_d = f"JSON deser failed {exc}"
                    msg += f" ({json_d})\n"
        except Exception as exc:
            msg += f"{list['name']} -> {type(exc).__name__}: {exc}\n"
    
    # Post intent to actions
    await tables.BotAction.insert(
        tables.BotAction(bot_id=bot_id, action=action, action_time=datetime.datetime.now(), list_source=bot_data["list_source"])
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
        
        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.claim_bot_api, tables.BotList.secret_key)

        return await post_act(interaction, list_info, tables.Action.CLAIM, "claim_bot_api", bot_id, "STUB_REASON")

class Unclaim(discord.ui.Modal, title='Unclaim Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.unclaim_bot_api, tables.BotList.secret_key)

        return await post_act(interaction, list_info, tables.Action.UNCLAIM, "unclaim_bot_api", bot_id, self.reason.value)


class Approve(discord.ui.Modal, title='Approve Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.approve_bot_api, tables.BotList.secret_key)

        return await post_act(interaction, list_info, tables.Action.APPROVE, "approve_bot_api", bot_id, self.reason.value)

class Deny(discord.ui.Modal, title='Deny Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.deny_bot_api, tables.BotList.secret_key)

        return await post_act(interaction, list_info, tables.Action.DENY, "deny_bot_api", bot_id, self.reason.value)


@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
@mr_command(modal_class=Claim)
async def claim(interaction: discord.Interaction):
    """Claim a bot"""
    return await interaction.response.send_modal(Claim())

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
@mr_command(modal_class=Unclaim)
async def unclaim(interaction: discord.Interaction):
    """Unclaims a bot"""
    return await interaction.response.send_modal(Unclaim())

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
@mr_command(modal_class=Approve)
async def approve(interaction: discord.Interaction):
    """Approves a bot"""
    return await interaction.response.send_modal(Approve())

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
@mr_command(modal_class=Deny)
async def deny(interaction: discord.Interaction):
    """Denies a bot"""
    return await interaction.response.send_modal(Deny())

@bot.event
async def on_ready():
    print("Client is now ready and up")
    await bot.tree.sync()
    await bot.tree.sync(guild=FSnowflake(id=secrets["gid"]))
    for cmd in bot.tree.walk_commands():
        print(cmd.name)
        