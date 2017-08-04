


class CAPAPIRouter(object):
    """
    Determine how to route database calls for an app's models (in this case, for an app named capapi).
    All other models will be routed to the next router in the DATABASE_ROUTERS setting if applicable,
    or otherwise to the default database.
    """

    def db_for_read(self, model, **hints):
        """Send all read operations on capapi app models to `capapi`."""
        if model._meta.app_label == 'capapi':
            return 'capapi'
        return None

    def db_for_write(self, model, **hints):
        """Send all write operations on capapi app models to `capapi`."""
        if model._meta.app_label == 'capapi':
            return 'capapi'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Determine if relationship is allowed between two objects."""
        # Allow any relation between two models that are both in the capapi app.
        if obj1._meta.app_label == 'capapi' and obj2._meta.app_label == 'capapi':
            return True
        # No opinion if neither object is in the capapi app (defer to default or other routers).
        elif 'capapi' not in [obj1._meta.app_label, obj2._meta.app_label]:
            return None

        # Block relationship if one object is in the capapi app and the other isn't.
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that the capapi app's models get created on the right database."""
        if db == 'capapi' and app_label == 'capapi':
            return True
        if app_label == 'capapi':
            # The capapi app should be migrated only on the capapi database.
            return db == 'capapi'
        elif db == 'capapi':
            # Ensure that all other apps don't get migrated on the capapi database.
            return False

        # No opinion for all other scenarios
        return None