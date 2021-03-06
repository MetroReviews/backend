import secrets
import enum

from piccolo.table import Table
from piccolo.columns import Text, Timestamptz, Integer, ForeignKey, UUID, BigInt, Array, Boolean
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.base import OnDelete, OnUpdate

class Action(enum.IntEnum):
    """
Type of action
    """
    CLAIM = 0
    UNCLAIM = 1
    APPROVE = 2
    DENY = 3

class State(enum.IntEnum):
    """
Current bot state
    """
    PENDING = 0
    UNDER_REVIEW = 1
    APPROVED = 2
    DENIED = 3

class ListState(enum.IntEnum):
    """
A lists state
    """
    PENDING_API_SUPPORT = 0
    SUPPORTED = 1
    DEFUNCT = 2
    BLACKLISTED = 3
    UNCONFIRMED_ENROLLMENT = 4

class BotList(Table, tablename="bot_list"):
    id = UUID(primary_key=True)
    state = Integer(null=False, choices=ListState, default=ListState.PENDING_API_SUPPORT)
    name = Text(null=False)
    description = Text(null=True)
    icon = Text(null=True)
    claim_bot_api = Text(null=False)
    unclaim_bot_api = Text(null=False)
    approve_bot_api = Text(null=False)
    deny_bot_api = Text(null=False)
    domain = Text(null=False)
    secret_key = Text(null=False, default=secrets.token_urlsafe)

class BotAction(Table, tablename="bot_action"):
    id = UUID(primary_key=True)
    bot_id = BigInt(null=False)
    action = Integer(null=False, choices=Action)
    reason = Text(null=False)
    reviewer = Text(null=False)
    action_time = Timestamptz(null=False, default=TimestamptzNow())
    list_source = ForeignKey(null=False, references=BotList, on_delete=OnDelete.cascade, on_update=OnUpdate.cascade)

class BotQueue(Table, tablename="bot_queue"):
    bot_id = BigInt(primary_key=True)
    username = Text(null=False)
    banner = Text(null=True)
    description = Text(null=False)
    long_description = Text(null=False)
    website = Text(null=True)
    support = Text(null=True)
    donate = Text(null=True)
    library = Text(null=True)
    nsfw = Boolean(null=False, default=False)
    prefix = Text(null=True)
    tags = Array(base_column=Text(null=False), default=[])
    review_note = Text(null=True)
    invite = Text(null=True)
    added_at = Timestamptz(null=False, default=TimestamptzNow())
    state = Integer(choices=State, default=State.PENDING)
    list_source = ForeignKey(null=False, references=BotList, on_delete=OnDelete.cascade, on_update=OnUpdate.cascade)
    owner = BigInt(null=False)
    extra_owners = Array(base_column=BigInt(null=False), default=[])
    reviewer = BigInt(null=True)
    invite_link = Text(null=True)
    cross_add = Boolean(null=False, default=True)

class Users(Table, tablename="users"):
    user_id = BigInt(primary_key=True)
    nonce = Text(null=False)
