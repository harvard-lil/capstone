from config.routers import SeparateDatabaseRouter


class CAPAPIRouter(SeparateDatabaseRouter):
    db_name = 'capapi'
    app_label = 'capapi'
