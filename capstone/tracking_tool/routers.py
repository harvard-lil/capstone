from config.routers import SeparateDatabaseRouter


class TrackingToolDatabaseRouter(SeparateDatabaseRouter):
    db_name = 'tracking_tool'
    app_label = 'tracking_tool'
