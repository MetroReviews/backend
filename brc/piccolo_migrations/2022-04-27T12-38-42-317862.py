from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import BigInt
from piccolo.columns.column_types import Text


ID = "2022-04-27T12:38:42:317862"
VERSION = "0.74.1"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="secret_key",
        params={"default": "TOVhlkUB8vKz3-QvI24uQRohM9EUQWhVRh79lhq7aN8"},
        old_params={"default": "VQkhKvt1FB-uLbNDU1pj1ATMk3TEaHJCXgRgjaprg5M"},
        column_class=Text,
        old_column_class=Text,
    )

    manager.alter_column(
        table_class_name="BotAction",
        tablename="bot_action",
        column_name="bot_id",
        params={"default": 0},
        old_params={"default": ""},
        column_class=BigInt,
        old_column_class=Text,
    )

    return manager
