from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns.column_types import ForeignKey
from piccolo.columns.column_types import Integer
from piccolo.columns.column_types import Serial
from piccolo.columns.column_types import Text
from piccolo.columns.column_types import Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class BotList(Table, tablename="bot_list"):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name=None,
        secret=False,
    )


ID = "2022-04-27T12:36:53:502755"
VERSION = "0.74.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.add_table("BotAction", tablename="bot_action")

    manager.add_table("BotList", tablename="bot_list")

    manager.add_column(
        table_class_name="BotAction",
        tablename="bot_action",
        column_name="bot_id",
        db_column_name="bot_id",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": True,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotAction",
        tablename="bot_action",
        column_name="action",
        db_column_name="action",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": Enum(
                "Action", {"CLAIM": 0, "UNCLAIM": 1, "APPROVE": 2, "DENY": 3}
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotAction",
        tablename="bot_action",
        column_name="reason",
        db_column_name="reason",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotAction",
        tablename="bot_action",
        column_name="reviewer",
        db_column_name="reviewer",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotAction",
        tablename="bot_action",
        column_name="action_time",
        db_column_name="action_time",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotAction",
        tablename="bot_action",
        column_name="list_source",
        db_column_name="list_source",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": BotList,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="id",
        db_column_name="id",
        column_class_name="Serial",
        column_class=Serial,
        params={
            "null": False,
            "primary_key": True,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="name",
        db_column_name="name",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="claim_bot_api",
        db_column_name="claim_bot_api",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="unclaim_bot_api",
        db_column_name="unclaim_bot_api",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="approve_bot_api",
        db_column_name="approve_bot_api",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="deny_bot_api",
        db_column_name="deny_bot_api",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="secret_key",
        db_column_name="secret_key",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "GBru03B0FEXO6jMwvAWsSfpyLXV2MgqE_L_Ue_K_fJ4",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
    )

    return manager
