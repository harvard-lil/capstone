from config.routers import SeparateDatabaseRouter


class UserDataRouter(SeparateDatabaseRouter):
    db_name = 'user_data'
    app_label = 'user_data'
