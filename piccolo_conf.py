from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

# Change this on main VPS
# See https://piccolo-orm.readthedocs.io/en/stable/piccolo/projects_and_apps/piccolo_projects.html#example
DB = PostgresEngine(config={
    "database": "brc",
    "host": "localhost",
})


# A list of paths to piccolo apps
# e.g. ['blog.piccolo_app']
APP_REGISTRY = AppRegistry(apps=["brc.piccolo_app", "piccolo_admin.piccolo_app"])
