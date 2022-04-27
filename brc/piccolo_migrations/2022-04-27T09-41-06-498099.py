from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text


ID = "2022-04-27T09:41:06:498099"
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
        params={"default": "lQGT_50AozkUXq9vVC24Ed7KZxHvmz-oI90ui3Fqs4g"},
        old_params={"default": "Ga6rGaSZiwCAdyCqyseLjblqzla874r6CjbOUH7Gq-g"},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
