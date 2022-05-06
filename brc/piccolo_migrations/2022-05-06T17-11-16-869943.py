from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import BigInt
from piccolo.columns.indexes import IndexMethod


ID = "2022-05-06T17:11:16:869943"
VERSION = "0.74.3"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="reviewer",
        db_column_name="reviewer",
        column_class_name="BigInt",
        column_class=BigInt,
        params={
            "default": 0,
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

    return manager
