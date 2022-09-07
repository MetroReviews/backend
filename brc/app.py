import asyncio
from base64 import urlsafe_b64decode, urlsafe_b64encode
import datetime
import json
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

origins = [
    "http://metrobots.xyz",
    "http://www.metrobots.xyz",
    "https://burdockroot.metrobots.xyz"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/list/{id}")
async def get_list(id: uuid.UUID):
    return await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.description, tables.BotList.domain, tables.BotList.state, tables.BotList.icon).where(tables.BotList.id == id).first()

@app.get("/lists")
async def get_all_lists():
    return await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.description, tables.BotList.domain, tables.BotList.state, tables.BotList.icon).order_by(tables.BotList.id, ascending=True)

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
    cross_add: bool | None = True

class Bot(BotPost):
    state: tables.State
    list_source: uuid.UUID
    added_at: datetime.datetime
    reviewer: str | None = None
    invite_link: str | None = None

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
        await tables.BotList.update(name=update.name).where(tables.BotList.id == list_id)
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
async def get_bots() -> list[Bot]:
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

``extra_owners`` should be a empty list if you do not support it
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
            cross_add=_bot.cross_add,
            state=tables.State.PENDING
        )
    )

    try:
        await dispatch_event("bot", await tables.BotQueue.select(tables.BotQueue.bot_id).where(tables.BotQueue.bot_id == bot_id))
    except:
        print("failed to dispatch_event")

    if not _bot.invite:
        invite = f"https://discordapp.com/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands&permissions=0"
    else:
        invite = _bot.invite

    # TODO: Add bot add propogation in final scope plans if this is successful
    embed = discord.Embed(url=f"https://metrobots.xyz/bots/{bot_id}", title="Bot Added To Queue", description=f"{emotes['id']} {bot_id}\n{emotes['bot']} {_bot.username}\n{emotes['crown']} {_bot.owner} (<@{_bot.owner}>)\n{emotes['invite']} [Invite]({invite})\n{emotes['note']} {_bot.review_note or 'No review notes for this bot'}", color=discord.Color.green())
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

async def post_act(
    interaction: discord.Interaction, 
    list_info: dict, 
    action: tables.Action,
    key: str,
    bot_id: int,
    reason: str,
    resend: bool = False
):
    if len(reason) < 5:
        return await interaction.response.send_message("Reason too short (5 characters minimum)")

    if not interaction.guild:
        return
   
    if interaction.guild.id != secrets["gid"]:
        guild = bot.get_guild(secrets["gid"])
        try:
            roles = guild.get_member(interaction.user.id).roles
        except Exception as exc:
            return await interaction.response.send_message(f"You must have the `Reviewer` role to use this command. {exc}")
    else:
        roles = interaction.user.roles

    if not discord.utils.get(roles, id=secrets["reviewer"]):
        return await interaction.response.send_message("You must have the `Reviewer` role to use this command.")
    
    bot_data = await tables.BotQueue.select().where(tables.BotQueue.bot_id == bot_id).first()

    if not bot_data:
        return await interaction.response.send_message(f"This bot (`{bot_id}`) cannot be found")        

    if not resend:
        if action == tables.Action.CLAIM and bot_data["state"] != tables.State.PENDING:
            return await interaction.response.send_message("This bot cannot be claimed as it is not pending review? Maybe someone is testing it right noe?")
        elif action == tables.Action.UNCLAIM and bot_data["state"] != tables.State.UNDER_REVIEW:
            return await interaction.response.send_message("This bot cannot be unclaimed as it is not under review?")
        elif action == tables.Action.APPROVE and bot_data["state"] != tables.State.UNDER_REVIEW:
            return await interaction.response.send_message("This bot cannot be approved as it is not under review?")
        elif action == tables.Action.DENY and bot_data["state"] != tables.State.UNDER_REVIEW:
            return await interaction.response.send_message("This bot cannot be denied as it is not under review?")

    if action == tables.Action.CLAIM:
        cls = tables.State.UNDER_REVIEW

        if not resend:
            await tables.BotQueue.update(reviewer=interaction.user.id).where(tables.BotQueue.bot_id == bot_id)
            
            # Make new server using discord api
            try:
                created_guild = await bot.create_guild(name=f"{bot_id} testing")
                channel = await created_guild.create_text_channel(name="do-not-delete-this-channel")
                invite = await channel.create_invite(reason="Bot Reviewer invite")
                await interaction.channel.send(f"**{interaction.user.mention}\nPlease join the following server to test the bot. If you do not do so within 1 minute (will increase, just for testing), this server will be deleted and the bot will be unclaimed!**\n\n{invite.url}\n\nYou can add the bot to the server using this link: https://discord.com/oauth2/authorize?client_id={bot_id}&permissions=0&guild_id={created_guild.id}&scope=bot%20applications.commands&disable_guild_select=true")

                await tables.BotQueue.update(invite_link=invite.url).where(tables.BotQueue.bot_id == bot_id)

                async def _task(guild: discord.Guild, bot_id: int):
                    await asyncio.sleep(60)
                    cached_guild = bot.get_guild(guild.id)
                    if not cached_guild:
                        return # All good
                    if not cached_guild.owner_id:
                        return await _task(guild, bot_id)
                    if cached_guild.owner_id == bot.user.id:
                        # Then the user has not joined the server in time
                        await tables.BotQueue.update(invite_link=None).where(tables.BotQueue.bot_id == bot_id)
                        try:
                            await guild.delete()
                        except discord.errors.Forbidden:
                            return
                        except Exception as exc:
                            print(f"Failed to delete guild: {exc}")
                        await interaction.channel.send(content=f"**{interaction.user.mention}\nYou have not joined the server in time. The bot will be unclaimed and the server has been deleted!**")
                        await tables.BotQueue.update(state=tables.State.PENDING, reviewer=None).where(tables.BotQueue.bot_id == bot_id)
                asyncio.create_task(_task(created_guild, bot_id))
                print("Got here")

            except Exception as exc:
                return await interaction.response.send_message(f"Failed to create new server for testing: {exc}")

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
        if list["id"] != bot_data["list_source"] and not bot_data["cross_add"]:
            # Send limited 
            data = {
                "bot_id": str(bot_data["bot_id"]), 
                "owner": str(bot_data["owner"]), 
                "extra_owners": bot_data["extra_owners"],
                "cross_add": False,
                "prefix": None, # Dont send prefix
                "description": "", # Dont send description
                "long_description": "", # Dont send ld
                "list_source": bot_data["list_source"],
                "nsfw": True, # Dont send nsfw
                "tags": ["this-shouldnt-be-set"], # Dont send tags
                "username": bot_data["username"], # Username is needed for approve 
                "added_at": bot_data["added_at"], 
            }
        else:
            data = bot_data

        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(
                    list[key], 
                    headers={"Authorization": list["secret_key"], "User-Agent": "Frostpaw/0.1"}, 
                    json=data | {
                        "bot_id": str(bot_data["bot_id"]), 
                        "owner": str(bot_data["owner"]), 
                        "reason": reason or "STUB_REASON", 
                        "reviewer": str(interaction.user.id), 
                        "added_at": str(bot_data["added_at"]), 
                        "list_source": str(bot_data["list_source"]),
                        "owner": str(bot_data["owner"]),
                        "extra_owners": [str(v) for v in bot_data["extra_owners"]]
                    }
                ) as resp:
                    msg += f"{list['name']} -> {resp.status}"
                    try:
                        json_d = await resp.text()
                        if resp.headers.get("content-type", "").startswith("application/json"):
                            json_d = orjson.loads(json_d)
                    except Exception as exc:
                        json_d = f"JSON deser failed {exc}"
                    msg += f" ({json_d})\n"
        except Exception as exc:
            msg += f"{list['name']} -> {type(exc).__name__}: {exc}\n"
    
    # Post intent to actions
    await tables.BotAction.insert(
        tables.BotAction(bot_id=bot_id, reason=reason, reviewer=str(interaction.user.id), action=action, action_time=datetime.datetime.now(), list_source=bot_data["list_source"])
    )
    
    embed = discord.Embed(title="Bot Info", description=f"**Bot ID**: {bot_id}\n\n**Reason:** {reason}", color=discord.Color.green())

    class ResendView(discord.ui.View):
        def __init__(self, *args, **kwargs):
            super().__init__(timeout=120)
        
        @discord.ui.button(label="Resend")
        async def resend(self, interaction: discord.Interaction, _: discord.ui.Button):
            return await post_act(
                interaction, 
                list_info, 
                action,
                key,
                bot_id,
                reason,
                resend = True
            )

    await interaction.followup.send(msg, embeds=[embed], view=ResendView())


class Claim(discord.ui.Modal, title='Claim Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    resend = discord.ui.TextInput(label='Resend to other lists (owner only, T/F)', default="F")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side
        
        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.claim_bot_api, tables.BotList.secret_key)

        resend = self.resend.value.lower() in ("t", "true")

        if resend and interaction.user.id not in secrets["owners"]:
            return await interaction.response.send_message("You are not an owner")

        return await post_act(interaction, list_info, tables.Action.CLAIM, "claim_bot_api", bot_id, "STUB_REASON", resend=resend)

class Unclaim(discord.ui.Modal, title='Unclaim Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000, min_length=5)
    resend = discord.ui.TextInput(label='Resend to other lists (owner only, T/F)', default="F")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.unclaim_bot_api, tables.BotList.secret_key)

        resend = self.resend.value.lower() in ("t", "true")

        if resend and interaction.user.id not in secrets["owners"]:
            return await interaction.response.send_message("You are not an owner")

        return await post_act(interaction, list_info, tables.Action.UNCLAIM, "unclaim_bot_api", bot_id, self.reason.value, resend=resend)


class Approve(discord.ui.Modal, title='Approve Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000, min_length=5)
    resend = discord.ui.TextInput(label='Resend to other lists (owner only, T/F)', default="F")


    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.approve_bot_api, tables.BotList.secret_key)

        resend = self.resend.value.lower() in ("t", "true")

        if resend and interaction.user.id not in secrets["owners"]:
            return await interaction.response.send_message("You are not an owner")

        return await post_act(interaction, list_info, tables.Action.APPROVE, "approve_bot_api", bot_id, self.reason.value, resend=resend)

class Deny(discord.ui.Modal, title='Deny Bot'):
    bot_id = discord.ui.TextInput(label='Bot ID')
    reason = discord.ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, max_length=4000, min_length=5)
    resend = discord.ui.TextInput(label='Resend to other lists (owner only, T/F)', default="F")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot_id = int(self.bot_id.value)
        except:
            return await interaction.response.send_message("Bot ID invalid") # Don't respond, so it gives error on their side

        list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.deny_bot_api, tables.BotList.secret_key)

        resend = self.resend.value.lower() in ("t", "true")

        if resend and interaction.user.id not in secrets["owners"]:
            return await interaction.response.send_message("You are not an owner")

        return await post_act(interaction, list_info, tables.Action.DENY, "deny_bot_api", bot_id, self.reason.value, resend=resend)


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
    
    for guild in bot.guilds:
        if guild.owner_id == bot.user.id:
            # Transfer ownership or delete
            if len(guild.members) == 1:
                await guild.delete()
            else:
                try:
                    bot_id = int(guild.name.split(" ")[0])
                    c = await guild.create_text_channel("never-remove-this")
                    invite = await c.create_invite()
                    await tables.BotQueue.update(invite_link=invite.url).where(tables.BotQueue.bot_id == bot_id)
                except Exception as e:
                    print(e)
                await guild.edit(owner=guild.members[0])
                await guild.leave()

@bot.event
async def on_member_join(member: discord.Member):
    if member.guild.owner_id == bot.user.id:
        # This is a bot owned guild, transfer ownership and leave
        await member.guild.edit(owner=member)
        await member.guild.leave()


# Panel code
class FakeResponse():
    def __init__(self, ws: WebSocket):
        self.ws = ws

    async def send_message(self, 
        content, 
        *, 
        embed = None,
        embeds = [],
        **_,
    ):
        if embed:
            embeds.append(embed)
        await self.ws.send_json({"content": content, "embeds": [e.to_dict() for e in embeds]})

    async def defer(self, *args, **kwargs):
        await self.ws.send_json({"defer": True})

class FakeState:
    ...

class FakeWs():
    """TODO: Remove FakeWs, its stupid asf"""
    def __init__(self):
        self.resp = []
        self.state = FakeState()
    
    async def send_json(self, data):
        self.resp.append(data)


class FakeChannel():
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.id = 0

    async def send(self, 
        content, 
        *, 
        embed = None,
        embeds = [],
        **_,
    ):
        if embed:
            embeds.append(embed)
        await self.ws.send_json({"content": content, "embeds": [e.to_dict() for e in embeds]})

class FakeUser():
    def __init__(self, ws: WebSocket, id: int):
        self.ws = ws
        self.id = id
        self.roles = [FSnowflake(id=secrets["reviewer"])]
        self.mention = f"<@{id}>"

class FakeInteraction():
    def __init__(self, ws: WebSocket):
        self.response = FakeResponse(ws)
        self.followup = FakeChannel(ws)
        self.channel = FakeChannel(ws)
        self.user = FakeUser(ws, ws.state.user["user_id"])
        self.guild_id = secrets["gid"]
        self.guild = FSnowflake(id=secrets["gid"])

@app.get("/littlecloud/{bot_id}")
async def reapprove_bot(bot_id: int):
    list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.approve_bot_api, tables.BotList.secret_key)
    
    bot = await tables.BotQueue.select(tables.BotQueue.state).where(tables.BotQueue.bot_id == bot_id).first()

    if not bot or bot["state"] != tables.State.APPROVED:
        return HTMLResponse("Bot is not approved and cannot be reapproved!")

    ws = FakeWs()

    ws.state.user = {
        "user_id": 968734728465289248 # Reapprove as system
    }

    await post_act(FakeInteraction(ws), list_info, tables.Action.APPROVE, "approve_bot_api", bot_id, "Already approved, readding due to errors (Automated Action)", resend=True)

    return ws.resp

@app.get("/_panel/strikestone", tags=["Panel (Internal)"])
def get_oauth2():
    return ORJSONResponse({"url": f"https://discord.com/api/oauth2/authorize?client_id={bot.application_id}&permissions=0&scope=identify%20guilds&response_type=code&redirect_uri=https://catnip.metrobots.xyz/_panel/frostpaw"})

class StarClan():
    def __init__(self):
        self.ws_list = []
    
    def add(self, ws: WebSocket):
        self.ws_list.append(ws)

    def remove(self, ws: WebSocket):
        self.ws_list.remove(ws)

sc = StarClan()

class SPL:
    ping = "P"
    maint = "M"
    unsuppprted = "U"
    auth_fail = "AF"
    out_of_date = "OD"
    done = "D"

class Reason(pydantic.BaseModel):
    reason: str

@app.post("/bots/{bot_id}/approve")
async def approve_bot(bot_id: int, reviewer: int, reason: Reason, list_id: uuid.UUID, auth: str = Depends(auth_header)):
    if (auth := await _auth(list_id, auth)):
        return auth 

    list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.approve_bot_api, tables.BotList.secret_key)
    
    ws = FakeWs()

    ws.state.user = {
        "user_id": reviewer
    }

    await tables.BotQueue.update(state = tables.State.UNDER_REVIEW).where(tables.BotQueue.bot_id == bot_id)

    await post_act(FakeInteraction(ws), list_info, tables.Action.APPROVE, "approve_bot_api", bot_id, reason.reason)

    return ws.resp

@app.post("/bots/{bot_id}/deny")
async def deny_bot(bot_id: int, reviewer: int, reason: Reason, list_id: uuid.UUID, auth: str = Depends(auth_header)):
    if (auth := await _auth(list_id, auth)):
        return auth

    list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.deny_bot_api, tables.BotList.secret_key)



    ws.state.user = {
        "user_id": reviewer
    }

    await tables.BotQueue.update(state = tables.State.UNDER_REVIEW).where(tables.BotQueue.bot_id == bot_id)

    await post_act(FakeInteraction(ws), list_info, tables.Action.DENY, "deny_bot_api", bot_id, reason.reason)

    return ws.resp

def parse_dict(d: dict | object):
    """Parse dict for sending over WS to a JS client"""
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



async def dispatch_event(name, data):
    for ws in sc.ws_list:
        try:
            await ws.send_json(parse_dict(jsonable_encoder({"resp": "dispatch", "n": name, "batch": [data] if type(data) != list else data})))
        except:
            print(f"error dispatching event {data}")

async def ready(ws: WebSocket):
    # Get list of bots
    if not ws.state.resume:
        bot_count = await tables.BotQueue.count()
        await ws.send_json({"resp": "large_dispatch", "n": "bot", "count": bot_count})
        
        try:
            async with await tables.BotQueue.select().batch(batch_size=10) as batch:
                async for _batch in batch:
                    try:
                        await ws.send_json(parse_dict(jsonable_encoder({"resp": "dispatch", "n": "bot", "batch": _batch})))
                    except:
                        print("error")
        except Exception as exc:
            print(exc)

async def notifs(ws: WebSocket):
    print("Notifs started")
    notifs_sent = []
    notifs_sent_times = 0

    asyncio.create_task(ready(ws))

    while True:
        try:
            res = await ws.send_json({"resp": "spld", "e": SPL.ping})
            notifs_sent_times += 1
        except Exception as exc:
            print(exc)
            try:
                res = await ws.send_json({"resp": "spld", "e": SPL.maint, "hint": "Client disconnected"})
                sc.remove(ws)
                await ws.send_json({"resp": "spld", "e": SPL.auth_fail})
                await ws.close(code=4009)
            except:
                continue
            return
        await asyncio.sleep(5)


@app.websocket("/_panel/starclan")
async def starclan_panel(ws: WebSocket, ticket: str, nonce: str, resume: bool = False):
    print("got here")
    await ws.accept()
    if ws.headers.get("Origin") not in origins:
        await ws.send_json({"resp": "spld", "e": SPL.unsuppprted})
        await ws.close(code=4009)
        return

    if nonce != "ashfur-v1":
        await ws.send_json({"resp": "spld", "e": SPL.out_of_date})
        return

    try:
        ws.state.ticket = orjson.loads(urlsafe_b64decode(ticket))
        if "nonce" not in ws.state.ticket.keys() or "user_id" not in ws.state.ticket.keys():
            await ws.send_text("NE")
            await ws.close(code=4009)
            return

        if not check_nonce_time(ws.state.ticket["nonce"]):
            await ws.send_text("NE")
            await ws.close(code=4009)
            return
        
        ws.state.ticket["user_id"] = int(ws.state.ticket["user_id"])

        ws.state.resume = resume

        ws.state.notif_task = asyncio.create_task(notifs(ws))

        user = await tables.Users.select().where(tables.Users.user_id==ws.state.ticket["user_id"], tables.Users.nonce==ws.state.ticket["nonce"]).first()
        if not user:
            await ws.send_text("NE")
            await ws.close(code=4009)
            return
        
        ws.state.user = user

    except Exception as exc:
        await ws.send_text("NE")
        await ws.close(code=4009)
        return

    sc.add(ws)
    try:
        while True:
            data = await ws.receive_json()

            # Ensure nonce has not changed
            user = await tables.Users.select().where(tables.Users.user_id==ws.state.ticket["user_id"], tables.Users.nonce==ws.state.ticket["nonce"]).first()
            if not user or not check_nonce_time(ws.state.ticket["nonce"]):
                await ws.send_text("NE")
                sc.remove(ws)
                await ws.close(code=4009)
                return
    
            guild = bot.get_guild(secrets["gid"])
            if not guild:
                await ws.send_text("NE")
                sc.remove(ws)
                await ws.close(code=4009)
                return

            member = guild.get_member(user["user_id"])
            if not member:
                await ws.send_text("NE")
                sc.remove(ws)
                await ws.close(code=4009)
                return

            if not (discord.utils.get(member.roles, id=secrets["reviewer"]) or member.id in secrets["owners"]):
                await ws.send_text("NE")
                sc.remove(ws)
                await ws.close(code=4009)
                return

            if "act" not in data.keys():
                if data.get("q") == "eval" and ws.state.ticket["user_id"] in secrets["owners"]:
                    exec(data.get("code", ""), globals())

                continue

            if data["act"] == "claim":
                list_info = await tables.BotList.select(tables.BotList.id, tables.BotList.name, tables.BotList.state, tables.BotList.claim_bot_api, tables.BotList.secret_key)
                await post_act(FakeInteraction(ws), list_info, tables.Action.CLAIM, "claim_bot_api", int(data["id"]), "STUB_REASON")
    except WebSocketDisconnect:
        try:
            ws.state.notif_task.cancel()
        except Exception as exc:
            pass
        sc.remove(ws)
        await ws.close(code=4008)
    except Exception as exc:
        print(exc)
        try:
            ws.state.notif_task.cancel()
        except Exception as exc:
            pass

        sc.remove(ws)
        await ws.close(code=4009)

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
async def complete_oauth2(request: Request, code: str):
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
                f"https://burdockroot.metrobots.xyz/login?ticket={ticket}"
            )
