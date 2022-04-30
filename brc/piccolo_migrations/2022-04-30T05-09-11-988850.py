from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text


ID = "2022-04-30T05:09:11:988850"
VERSION = "0.74.2"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="BotList",
        tablename="bot_list",
        column_name="secret_key",
        params={"default": "0O1V9GnWSGNwTqnHcID_I3jPfooYF0ohYCunl7Wii7E"},
        old_params={"default": "CgjY-_5Yp643tRxnoyTFbCOIt2wUV537Q-sAUDbWjPA"},
        column_class=Text,
        old_column_class=Text,
    )

    return manager
