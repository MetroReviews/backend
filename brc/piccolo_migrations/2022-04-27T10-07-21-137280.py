from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns.column_types import ForeignKey
from piccolo.columns.column_types import Text
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class BotList(Table, tablename="bot_list"):
    id = Text(
        default="",
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name=None,
        secret=False,
    )


ID = "2022-04-27T10:07:21:137280"
VERSION = "0.74.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
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

    manager.alter_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="secret_key",
        params={"default": "yHEFSi3faAFnnTfibI-yep_8eJNm6na5_pEt3Jlpw64"},
        old_params={"default": "t0r40s23zPwuFT-oY3gk3yp9h_ye7PGZtkSzPLx60uw"},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
