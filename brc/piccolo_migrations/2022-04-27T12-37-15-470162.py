from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text


ID = "2022-04-27T12:37:15:470162"
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
        params={"default": "VQkhKvt1FB-uLbNDU1pj1ATMk3TEaHJCXgRgjaprg5M"},
        old_params={"default": "GBru03B0FEXO6jMwvAWsSfpyLXV2MgqE_L_Ue_K_fJ4"},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
