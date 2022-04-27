from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns.column_types import BigInt
from piccolo.columns.column_types import ForeignKey
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


ID = "2022-04-27T12:45:12:196002"
VERSION = "0.74.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.add_table("BotQueue", tablename="bot_queue")

    manager.add_column(
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="bot_id",
        db_column_name="bot_id",
        column_class_name="BigInt",
        column_class=BigInt,
        params={
            "default": 0,
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
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="username",
        db_column_name="username",
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
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="added_at",
        db_column_name="added_at",
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
        table_class_name="BotQueue",
        tablename="bot_queue",
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

    manager.alter_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="secret_key",
        params={"default": "GJkdL5YM20bekQGO9YMEIwSvex9WEewAlz50rUSFmNQ"},
        old_params={"default": "TOVhlkUB8vKz3-QvI24uQRohM9EUQWhVRh79lhq7aN8"},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
