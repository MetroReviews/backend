import secrets
import enum

from piccolo.table import Table
from piccolo.columns import Text, Timestamptz, Integer, ForeignKey
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.base import OnDelete, OnUpdate

class Action(enum.IntEnum):
    """
    Enum for Action
    """
    CLAIM = 0
    UNCLAIM = 1
    APPROVE = 2
    DENY = 3

class BotList(Table, tablename="bot_list"):
    id = Text(primary_key=True)
    name = Text(null=False)
    claim_bot_api = Text(null=False)
    approve_bot_api = Text(null=False)
    deny_bot_api = Text(null=False)
    secret_key = Text(null=False, default=secrets.token_urlsafe())

class BotAction(Table, tablename="bot_action"):
    bot_id = Text(primary_key=True)
    action = Integer(choices=Action)
    action_time = Timestamptz(null=False, default=TimestamptzNow())
    list_source = ForeignKey(null=True, references=BotList, on_delete=OnDelete.cascade, on_update=OnUpdate.cascade)