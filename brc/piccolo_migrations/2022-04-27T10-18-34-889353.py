from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text


ID = "2022-04-27T10:18:34:889353"
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
        params={"default": "_5GOaCc07pvAhxOjTu2YChps8e46iIW8-Qz854IhXqU"},
        old_params={"default": "yHEFSi3faAFnnTfibI-yep_8eJNm6na5_pEt3Jlpw64"},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
