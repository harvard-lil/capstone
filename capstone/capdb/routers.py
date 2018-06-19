from config.routers import SeparateDatabaseRouter


class CapDBRouter(SeparateDatabaseRouter):
    db_name = 'capdb'
    app_label = 'capdb'
