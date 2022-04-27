from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from enum import Enum
from piccolo.columns.column_types import Integer
from piccolo.columns.column_types import JSONB
from piccolo.columns.column_types import Text
from piccolo.columns.indexes import IndexMethod


ID = "2022-04-27T14:07:48:709514"
VERSION = "0.74.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="banner",
        db_column_name="banner",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
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
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="description",
        db_column_name="description",
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
        column_name="extra_links",
        db_column_name="extra_links",
        column_class_name="JSONB",
        column_class=JSONB,
        params={
            "default": "{}",
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
        column_name="github",
        db_column_name="github",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
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
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="invite",
        db_column_name="invite",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
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
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="long_description",
        db_column_name="long_description",
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
        column_name="privacy_policy",
        db_column_name="privacy_policy",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
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
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="state",
        db_column_name="state",
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
                "State",
                {"PENDING": 0, "UNDER_REVIEW": 1, "APPROVED": 2, "DENIED": 3},
            ),
            "db_column_name": None,
            "secret": False,
        },
    )

    manager.add_column(
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="website",
        db_column_name="website",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
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
        params={"default": "_EZWlfg8LgsVBkF1Psg-2p_0z4jBS6rw9pPPminCLkM"},
        old_params={"default": "GJkdL5YM20bekQGO9YMEIwSvex9WEewAlz50rUSFmNQ"},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
