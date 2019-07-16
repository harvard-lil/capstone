from config.routers import SeparateDatabaseRouter


class CapDBRouter(SeparateDatabaseRouter):
    db_name = 'capweb'
    app_label = 'capweb'
