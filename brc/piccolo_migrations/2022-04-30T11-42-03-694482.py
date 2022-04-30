from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Array
from piccolo.columns.column_types import BigInt
from piccolo.columns.column_types import Text
from piccolo.columns.indexes import IndexMethod


ID = "2022-04-30T11:42:03:694482"
VERSION = "0.74.2"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="extra_owners",
        db_column_name="extra_owners",
        column_class_name="Array",
        column_class=Array,
        params={
            "base_column": BigInt(
                default=0,
                null=False,
                primary_key=False,
                unique=False,
                index=False,
                index_method=IndexMethod.btree,
                choices=None,
                db_column_name=None,
                secret=False,
            ),
            "default": [],
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
        params={"default": "J_HhPVKDC-5ici-zc-SIoIrmgEN0vcUmup9uxo0Y7gs"},
        old_params={"default": "cNM6gWOc6lO1jWXm_na8MQWB7fRSjvVqMj7ekOTqN8M"},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
