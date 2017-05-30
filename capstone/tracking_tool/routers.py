class TrackingToolDatabaseRouter(object):
    """
        Determine how to route database calls for the tracking_tool app and database.
        All other models will be routed to the next router in the DATABASE_ROUTERS setting if applicable,
        or otherwise to the default database.
        
        Via https://strongarm.io/blog/multiple-databases-in-django/
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'tracking_tool':
            return 'tracking_tool'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'tracking_tool':
            return 'tracking_tool'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Allow any relation between two models that are both in the Example app.
        if obj1._meta.app_label == 'tracking_tool' and obj2._meta.app_label == 'tracking_tool':
            return True
        # Block relationship if one object is in the Example app and the other isn't.
        elif 'tracking_tool' in [obj1._meta.app_label, obj2._meta.app_label]:
            return False
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """ No migrations for this app or db. """
        if app_label == 'tracking_tool' or db == 'tracking_tool':
            return False
        return None