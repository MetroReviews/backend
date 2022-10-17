import asyncio
from base64 import urlsafe_b64decode, urlsafe_b64encode
import datetime
import json
import os
import uuid
import aiohttp
import discord
import secrets as _secrets
from discord.ext import commands
from fastapi.responses import HTMLResponse, ORJSONResponse, RedirectResponse
from fastapi.security.api_key import APIKeyHeader
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.routing import Mount
from fastapi.encoders import jsonable_encoder
import orjson
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin
from fastapi.middleware.cors import CORSMiddleware
import time
import piccolo
import pydantic
from .silverpelt import Silverpelt, SilverpeltRequest

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
                allowed_hosts=['catnip.metrobots.xyz']
            ),
        ),
    ],
)

@app.middleware("http")
async def cors(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin") or "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept"

    if request.method == "OPTIONS":
        response.status_code = 200
    return response

with open("site.html") as site:
    site_html = site.read()

class MetroBot(commands.Bot):
    async def is_owner(self, user: discord.User):
        if user.id in secrets["owners"]:
            return True

        return False

bot = MetroBot(intents=discord.Intents.all(), command_prefix="%")

def check_nonce_time(nonce):
    split = nonce.split("@")
    if len(split) != 2:
        return False
    try:
        t = float(split[1])
    except Exception as exc:
        return False
    if time.time() - t > 60 * 30:
        return False
    return True

with open("secrets.json") as f:
    secrets = json.load(f)
    secrets["gid"] = int(secrets["gid"])
    secrets["reviewer"] = int(secrets["reviewer"])
    secrets["queue_channel"] = int(secrets["queue_channel"])

silverpelt = Silverpelt(secrets)

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

class List(pydantic.BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    domain: str | None = None
    state: tables.ListState
    icon: str | None = None

@app.get("/list/{id}", response_model=List)
async def get_list(id: uuid.UUID):
    return await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.description, tables.BotList.domain, tables.BotList.state, tables.BotList.icon).where(tables.BotList.id == id).first()

@app.get("/lists", response_model=list[List])
async def get_all_lists():
    return await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.description, tables.BotList.domain, tables.BotList.state, tables.BotList.icon).order_by(tables.BotList.id, ascending=True)

class BotPost(pydantic.BaseModel):
    bot_id: str
    banner: str | None = None
    description: str 
    long_description: str
    website: str | None = None
    invite: str | None = None
    owner: str
    extra_owners: list[str] | None = []
    support: str | None = None
    donate: str | None = None
    library: str | None = None
    nsfw: bool | None = False
    prefix: str | None = None
    tags: list[str] | None = None
    review_note: str | None = None
    cross_add: bool | None = True

class Bot(BotPost):
    state: tables.State
    list_source: uuid.UUID
    added_at: datetime.datetime
    reviewer: str | None = None
    invite_link: str | None = None
    username: str | None = "Unknown"

class ListUpdate(pydantic.BaseModel):
    name: str | None = None
    description: str | None = None
    domain: str | None = None
    claim_bot_api: str | None = None
    unclaim_bot_api: str | None = None
    approve_bot_api: str | None = None
    deny_bot_api: str | None = None
    reset_secret_key: bool = False
    icon: str | None = None

auth_header = APIKeyHeader(name='Authorization')

@app.patch("/lists/{list_id}")
async def update_list(list_id: uuid.UUID, update: ListUpdate, auth: str = Depends(auth_header)):
    if (auth := await _auth(list_id, auth)):
        return auth 
    
    has_updated = []

    if update.name:
        await tables.BotList.update(name=update.name).where(tables.BotList.id == list_id)
        has_updated.append("name")
    if update.description:
        await tables.BotList.update(description=update.description).where(tables.BotList.id == list_id)
        has_updated.append("description")
    if update.icon:
        if update.icon.startswith("https://"):
            await tables.BotList.update(icon=update.icon).where(tables.BotList.id == list_id)
            has_updated.append("icon")
    if update.claim_bot_api:
        await tables.BotList.update(claim_bot_api=update.claim_bot_api).where(tables.BotList.id == list_id)
        has_updated.append("claim_bot_api")
    if update.unclaim_bot_api:
        await tables.BotList.update(unclaim_bot_api=update.unclaim_bot_api).where(tables.BotList.id == list_id)
        has_updated.append("unclaim_bot_api")
    if update.approve_bot_api:
        await tables.BotList.update(approve_bot_api=update.approve_bot_api).where(tables.BotList.id == list_id)
        has_updated.append("approve_bot_api")
    if update.deny_bot_api:
        await tables.BotList.update(deny_bot_api=update.deny_bot_api).where(tables.BotList.id == list_id)
        has_updated.append("deny_bot_api")
    if update.domain:
        # Remove trailing /
        if update.domain.endswith("/"):
            update.domain = update.domain[:-1]
        await tables.BotList.update(domain=update.domain).where(tables.BotList.id == list_id)
        has_updated.append("domain")
    
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
async def get_all_bots() -> list[Bot]:
    return await tables.BotQueue.select().order_by(tables.BotQueue.bot_id, ascending=True)

@app.get("/team")
async def our_team():
    guild = bot.get_guild(int(secrets["gid"]))
    if not guild:
        return {"detail": "Guild not found"}
    
    team = []

    for member in guild.members:
        if member.id in []:
            continue

        list_roles = []
        is_list_owner = False
        sudo = False
        is_reviewer = False
        for role in member.roles:
            if "list" in role.name.lower() and not role.name.lower().startswith("list"):
                list_roles.append(role.name)

            if role.id == int(secrets["list_owner"]):
                is_list_owner = True
            elif role.id == int(secrets["sudo"]):
                sudo = True
            elif role.id == int(secrets["reviewer"]):
                is_reviewer = True

        if is_reviewer:
            team.append({
                "username": member.name, 
                "id": str(member.id), 
                "avatar": member.avatar.url,
                "is_list_owner": is_list_owner,
                "sudo": sudo,
                "roles": list_roles
            })

    return team

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
    """
    if (auth := await _auth(list_id, auth)):
        return auth 
    
    rem = []
    
    try:
        bot_id = int(_bot.bot_id)
        owner = int(_bot.owner)
        try:
            extra_owners = [int(v) for v in _bot.extra_owners]
        except:
            extra_owners = []
            rem.append("extra_owners")
    except:
        return ORJSONResponse({"error": "Invalid bot fields"}, status_code=400)
   
    if owner in extra_owners:
        flag = True
        while flag:
            try:
                extra_owners.remove(owner)
            except:
                flag = False

    extra_owners = list(set(extra_owners))

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
    
    # Ensure add bot across lists *works*
    if _bot.tags:
        _bot.tags = [tag.lower() for tag in _bot.tags]
        if "utility" not in _bot.tags:
            _bot.tags.append("utility")
    else:
        _bot.tags = ["utility"]

    curr_bot = await tables.BotQueue.select(tables.BotQueue.bot_id).where(tables.BotQueue.bot_id == bot_id)

    if len(curr_bot) > 0:
        print("Bot already exists")
        return ORJSONResponse({"error": "Bot already in queue"}, status_code=409)

    if _bot.invite and not _bot.invite.startswith("https://"):
        # Just remove bad invite
        _bot.invite = None
        rem.append("invite")
   
    user = bot.get_user(bot_id)
    if not user:
        try:
            user = await bot.fetch_user(bot_id)
        except Exception as exc:
            print(exc)
            return ORJSONResponse({"error": "Bot does not exist?"}, status_code=400)

        if not user:
            return ORJSONResponse({"error": "Bot does not exist?"}, status_code=400)

    await tables.BotQueue.insert(
        tables.BotQueue(
            bot_id=bot_id, 
            username=user.name, 
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
            cross_add=_bot.cross_add,
            state=tables.State.PENDING
        )
    )

    if not _bot.invite:
        invite = f"https://discordapp.com/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands&permissions=0"
    else:
        invite = _bot.invite

    # TODO: Add bot add propogation in final scope plans if this is successful
    embed = discord.Embed(url=f"https://metrobots.xyz/bots/{bot_id}", title="Bot Added To Queue", description=f"{emotes['id']} {bot_id}\n{emotes['bot']} {user.name}\n{emotes['crown']} {_bot.owner} (<@{_bot.owner}>)\n{emotes['invite']} [Invite]({invite})\n{emotes['note']} {_bot.review_note or 'No review notes for this bot'}", color=discord.Color.green())
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

def is_reviewer(interaction: discord.Interaction):
    """Checks if the user is a reviewer"""
    if interaction.user.id in secrets["owners"]:
        return True

    if not interaction.guild or interaction.guild.id != secrets["gid"]:
        guild = bot.get_guild(secrets["gid"])
        try:
            roles = guild.get_member(interaction.user.id).roles
        except:
            return False
    else:
        roles = interaction.user.roles

    if not discord.utils.get(roles, id=secrets["reviewer"]):
        return False
    return True

class FSnowflake():
    """Blame discord"""
    def __init__(self, id):
        self.id: int = id

@bot.command()
async def delbot(ctx: commands.Context, bot: int):
    owner = await ctx.bot.is_owner(ctx.author)
    if not owner:
        return await ctx.send("You aren't a owner of Metro...")
    r = await tables.BotQueue.delete().where(tables.BotQueue.bot_id == bot)
    await ctx.send(f"Success with response: {r}")

@bot.command()
async def register_emojis(ctx: commands.Context):
    if ctx.author.id not in secrets["owners"]:
        return await ctx.send("You are not an owner")

    # Delete all emojis first
    for emoji in ctx.guild.emojis:
        if emoji.name.startswith("mr_"):
            await ctx.send(f"Deleting {emoji.name}")
            await emoji.delete()
    
    # Add all emojis from assets folder
    for emoji in os.listdir("assets"):
        if emoji.endswith(".webp"):
            await ctx.send(f"Adding {emoji}")
            await ctx.guild.create_custom_emoji(name="mr_"+emoji.replace(".webp", ""), image=open(f"assets/{emoji}", "rb").read())

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def invite(interaction: discord.Interaction, bot_id: str):
    if not bot_id.isdigit():
        return await interaction.response.send_message("Invalid bot id")
    return await interaction.response.send_message(f"https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands&permissions=0")

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def queue(interaction: discord.Interaction, show_all: bool = False):
    """Bot queue"""
    states = {}
    for state in list(tables.State):
        if not show_all and state not in (tables.State.PENDING, tables.State.UNDER_REVIEW):
            continue
        states[state] = await tables.BotQueue.select(tables.BotQueue.bot_id, tables.BotQueue.username).where(tables.BotQueue.state == state)
    msg = []
    msg_index = -1
    for key, bots in states.items():
        if not len(bots):
            continue
        msg.append(f"**{key.name} ({len(bots)})**\n\n")
        msg_index += 1
        for bot in bots:
            if len(msg) > 1900:
                msg.append("")
                msg_index += 1
            msg[msg_index] += f"{bot['bot_id']} ({bot['username']})\n"
    await interaction.response.send_message(msg[0])
    for msg in msg[1:]:
        await interaction.followup.send(msg)

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def sync(interaction: discord.Interaction):
    """Syncs all commands"""
    await bot.tree.sync(guild=FSnowflake(id=secrets["gid"]))
    return await interaction.response.send_message("Done syncing")

@bot.tree.command(guild=FSnowflake(id=secrets["gid"]))
async def support(interaction: discord.Interaction):
    """Show the link to support"""
    await interaction.response.send_message("https://github.com/MetroReviews/support")

class Claim(discord.ui.Modal, title='Claim Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    resend = discord.ui.TextInput(label='Resend to other lists (owner only, T/F)', default="F")

    async def on_submit(self, interaction: discord.Interaction):
        if not is_reviewer(interaction):
            return await interaction.response.send_message("You are not a reviewer", ephemeral=True)

        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side
        
        resend = self.resend.value.lower() in ("t", "true")

        if resend and interaction.user.id not in secrets["owners"]:
            return await interaction.response.send_message("You are not an owner")
        
        await interaction.response.defer()

        res = await silverpelt.request(
            SilverpeltRequest(
                bot_id=bot_id,
                reason="STUB_REASON",
                resend=resend,
                action=tables.Action.CLAIM,
                reviewer=interaction.user.id,
            )
        )

        await interaction.followup.send(res.to_msg()[:2000])

class Unclaim(discord.ui.Modal, title='Unclaim Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000, min_length=5)
    resend = discord.ui.TextInput(label='Resend to other lists (owner only, T/F)', default="F")

    async def on_submit(self, interaction: discord.Interaction):
        if not is_reviewer(interaction):
            return await interaction.response.send_message("You are not a reviewer", ephemeral=True)

        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        resend = self.resend.value.lower() in ("t", "true")

        if resend and interaction.user.id not in secrets["owners"]:
            return await interaction.response.send_message("You are not an owner")

        await interaction.response.defer()

        res = await silverpelt.request(
            SilverpeltRequest(
                bot_id=bot_id,
                reason=self.reason.value,
                resend=resend,
                action=tables.Action.UNCLAIM,
                reviewer=interaction.user.id,
            )
        )

        await interaction.followup.send(res.to_msg())

class Approve(discord.ui.Modal, title='Approve Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000, min_length=5)
    resend = discord.ui.TextInput(label='Resend to other lists (owner only, T/F)', default="F")


    async def on_submit(self, interaction: discord.Interaction):
        if not is_reviewer(interaction):
            return await interaction.response.send_message("You are not a reviewer", ephemeral=True)

        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        resend = self.resend.value.lower() in ("t", "true")

        if resend and interaction.user.id not in secrets["owners"]:
            return await interaction.response.send_message("You are not an owner")

        await interaction.response.defer()

        res = await silverpelt.request(
            SilverpeltRequest(
                bot_id=bot_id,
                reason=self.reason.value,
                resend=resend,
                action=tables.Action.APPROVE,
                reviewer=interaction.user.id,
            )
        )

        await interaction.followup.send(res.to_msg())

class Deny(discord.ui.Modal, title='Deny Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000, min_length=5)
    resend = discord.ui.TextInput(label='Resend to other lists (owner only, T/F)', default="F")

    async def on_submit(self, interaction: discord.Interaction):
        if not is_reviewer(interaction):
            return await interaction.response.send_message("You are not a reviewer", ephemeral=True)

        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        resend = self.resend.value.lower() in ("t", "true")

        if resend and interaction.user.id not in secrets["owners"]:
            return await interaction.response.send_message("You are not an owner")

        await interaction.response.defer()

        res = await silverpelt.request(
            SilverpeltRequest(
                bot_id=bot_id,
                reason=self.reason.value,
                resend=resend,
                action=tables.Action.DENY,
                reviewer=interaction.user.id,
            )
        )
        
        await interaction.followup.send(res.to_msg())


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
    
@bot.event
async def on_member_join(member: discord.Member):
    if member.guild.owner_id == bot.user.id:
        # This is a bot owned guild, transfer ownership and leave
        await member.guild.edit(owner=member)
        await member.guild.leave()

@app.get("/littlecloud/{bot_id}")
async def reapprove_bot(bot_id: int):    
    _bot = await tables.BotQueue.select(tables.BotQueue.state).where(tables.BotQueue.bot_id == bot_id).first()

    if not _bot or _bot["state"] != tables.State.APPROVED:
        return HTMLResponse("Bot is not approved and cannot be reapproved!")

    print("Calling silverpelt")

    res = await silverpelt.request(
        SilverpeltRequest(
            bot_id=bot_id,
            reason="Already approved, readding due to errors (Automated Action)",
            resend=True,
            action=tables.Action.APPROVE,
            reviewer=bot.user.id,
        )
    )

    return HTMLResponse(res.to_html())

@app.get("/_panel/strikestone", tags=["Panel (Internal)"])
def get_oauth2(request: Request):
    print(request.headers.get("Origin"))
    return ORJSONResponse({"url": f"https://discord.com/api/oauth2/authorize?client_id={bot.application_id}&permissions=0&scope=identify%20guilds&response_type=code&redirect_uri=https://catnip.metrobots.xyz/_panel/frostpaw&state={request.headers.get('Origin') or 'https://burdockroot.metrobots.xyz'}"})

class Reason(pydantic.BaseModel):
    reason: str

@app.post("/bots/{bot_id}/approve")
async def approve_bot(bot_id: int, reviewer: int, reason: Reason, list_id: uuid.UUID, auth: str = Depends(auth_header)):
    if (auth := await _auth(list_id, auth)):
        return auth 
    
    res = await silverpelt.request(
        SilverpeltRequest(
            bot_id=bot_id,
            reason=reason.reason,
            resend=True,
            action=tables.Action.APPROVE,
            reviewer=reviewer,
        )
    )

    return HTMLResponse(res.to_html())

@app.post("/bots/{bot_id}/deny")
async def deny_bot(bot_id: int, reviewer: int, reason: Reason, list_id: uuid.UUID, auth: str = Depends(auth_header)):
    if (auth := await _auth(list_id, auth)):
        return auth 
    
    res = await silverpelt.request(
        SilverpeltRequest(
            bot_id=bot_id,
            reason=reason.reason,
            resend=True,
            action=tables.Action.DENY,
            reviewer=reviewer,
        )
    )

    return HTMLResponse(res.to_html())

def parse_dict(d: dict | object):
    """Parse dict for sending over HTTP for a JS client"""
    if isinstance(d, int):
        if d > 9007199254740991:
            return str(d)
        return d
    elif isinstance(d, list):
        return [parse_dict(i) for i in d]
    elif isinstance(d, dict):
        nd = {} # New dict
        for k, v in d.items():
            nd[k] = parse_dict(v)
        return nd
    else:
        return d        

@app.get("/_panel/mapleshade", tags=["Panel (Internal)"])
async def get_panel_access(ticket: str):
    try:
        ticket = orjson.loads(urlsafe_b64decode(ticket))
    except:
        return {"access": False}
    if "nonce" not in ticket.keys() or "user_id" not in ticket.keys():
        return {"access": False}
    if not check_nonce_time(ticket["nonce"]):
        return {"access": False, "hint": "Nonce expiry"}
    ticket["user_id"] = int(ticket["user_id"])
    user = await tables.Users.select().where(tables.Users.user_id==ticket["user_id"], tables.Users.nonce==ticket["nonce"]).first()
    if not user:
        return {"access": False}
    guild = bot.get_guild(secrets["gid"])
    if not guild:
        return {"access": False}
    member = guild.get_member(user["user_id"])
    if not member:
        return {"access": False}
    if discord.utils.get(member.roles, id=secrets["reviewer"]) or member.id in secrets["owners"]:
        return {
            "access": True, 
            "member": {
                "id": str(member.id),
                "name": str(member.name)
            }
        }
    return {"access": False}


@app.get("/_panel/frostpaw", tags=["Panel (Internal)"])
async def complete_oauth2(request: Request, code: str, state: str):
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': bot.application_id,
        'redirect_uri': "https://catnip.metrobots.xyz/_panel/frostpaw",
        'client_secret': secrets["client_secret"],
    }

    async with aiohttp.ClientSession() as sess:
        async with sess.post("https://discord.com/api/v10/oauth2/token", data=payload) as resp:
            if resp.status != 200:
                return await resp.json()
            data = await resp.json()

            scope = data["scope"].split(" ")

            if "identify" not in scope or "guilds" not in scope:
                return {"error": f"Invalid scopes, got {data['scope']} but have {scope}"}
            
            if data["token_type"] != "Bearer":
                return {"error": f"Invalid token type, got {data['token_type']}"}
            

            # Fetch user info
            async with sess.get(f"https://discord.com/api/v10/users/@me", headers={"Authorization": f"Bearer {data['access_token']}"}) as resp:
                if resp.status != 200:
                    return await resp.json()
                user = await resp.json()

            # Save the token
            nonce = _secrets.token_urlsafe() + "@" + str(time.time())

            try:
                await tables.Users.insert(
                    tables.Users(
                        user_id=int(user["id"]),
                        nonce=nonce
                    )
                )
            except Exception:
                await tables.Users.update(nonce=nonce).where(tables.Users.user_id == int(user["id"]))

            ticket = {
                "nonce": nonce,
                "user_id": str(user["id"]),
                "username": user["username"], # Ignored during actual auth
                "disc": user["discriminator"],
                "avatar": user["avatar"],
            }

            ticket = urlsafe_b64encode(orjson.dumps(ticket)).decode()

            return RedirectResponse(
                f"{state}/login?ticket={ticket}"
            )
