from config.routers import SeparateDatabaseRouter


class CapWebRouter(SeparateDatabaseRouter):
    db_name = 'capweb'
    app_label = 'capweb'
