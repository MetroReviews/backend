from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.column_types import Integer
from piccolo.columns.column_types import Text
from piccolo.columns.column_types import Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.indexes import IndexMethod


ID = "2022-04-27T10:01:13:708871"
VERSION = "0.74.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.add_table("BotAction", tablename="bot_action")

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

    manager.alter_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="secret_key",
        params={"default": "t0r40s23zPwuFT-oY3gk3yp9h_ye7PGZtkSzPLx60uw"},
        old_params={"default": "lQGT_50AozkUXq9vVC24Ed7KZxHvmz-oI90ui3Fqs4g"},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
