from piccolo.apps.migrations.auto.migration_manager import MigrationManager


ID = "2022-05-14T07:53:07:314443"
VERSION = "0.74.3"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="brc", description=DESCRIPTION
    )

    manager.drop_column(
        table_class_name="Users",
        tablename="users",
        column_name="access_token",
        db_column_name="access_token",
    )

    manager.drop_column(
        table_class_name="Users",
        tablename="users",
        column_name="expires_at",
        db_column_name="expires_at",
    )

    manager.drop_column(
        table_class_name="Users",
        tablename="users",
        column_name="refresh_token",
        db_column_name="refresh_token",
    )

    return manager
