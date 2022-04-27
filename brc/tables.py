import secrets
import enum

from piccolo.table import Table
from piccolo.columns import Text, Timestamptz, Integer, ForeignKey, Serial, BigInt, JSONB
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

class BotList(Table, tablename="bot_list"):
    id = Serial(primary_key=True)
    name = Text(null=False)
    claim_bot_api = Text(null=False)
    unclaim_bot_api = Text(null=False)
    approve_bot_api = Text(null=False)
    deny_bot_api = Text(null=False)
    secret_key = Text(null=False, default=secrets.token_urlsafe())

class BotAction(Table, tablename="bot_action"):
    bot_id = BigInt(primary_key=True)
    action = Integer(choices=Action)
    reason = Text(null=False)
    reviewer = Text(null=False)
    action_time = Timestamptz(null=False, default=TimestamptzNow())
    list_source = ForeignKey(null=True, references=BotList, on_delete=OnDelete.cascade, on_update=OnUpdate.cascade)

class BotQueue(Table, tablename="bot_queue"):
    bot_id = BigInt(primary_key=True)
    username = Text(null=False)
    description = Text(null=False)
    invite = Text(null=True)
    added_at = Timestamptz(null=False, default=TimestamptzNow())
    state = Integer(choices=State, default=State.PENDING)
    list_source = ForeignKey(null=True, references=BotList, on_delete=OnDelete.cascade, on_update=OnUpdate.cascade)
    owner = BigInt(null=False)
