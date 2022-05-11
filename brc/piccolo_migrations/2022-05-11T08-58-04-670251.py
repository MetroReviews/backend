from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Boolean
from piccolo.columns.indexes import IndexMethod


ID = "2022-05-11T08:58:04:670251"
VERSION = "0.74.3"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="BotQueue",
        tablename="bot_queue",
        column_name="cross_add",
        db_column_name="cross_add",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": True,
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
