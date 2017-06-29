class TrackingToolDatabaseRouter(object):
    """
        Determine how to route database calls for the tracking_tool app and database.
        All other models will be routed to the next router in the DATABASE_ROUTERS setting if applicable,
        or otherwise to the default database.
        
        Based on https://strongarm.io/blog/multiple-databases-in-django/
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
        """ Allow relations between tracking_tool models on tracking_tool db. """
        return self.check_permission(obj1._meta.app_label, obj2._meta.app_label)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """ Allow migrations for tracking_tool app on tracking_tool db. """
        return self.check_permission(app_label, db)

    def check_permission(self, label1, label2):
        """
            If *both* labels are tracking_tool, permission is allowed.
            Otherwise if one label is tracking_tool but not the other, permission is denied.
            This allows relationships within tracking_tool app and database, but no relationships to other apps/databases.
        """
        if label1 == 'tracking_tool' and label2 == 'tracking_tool':
            return True
        if label1 == 'tracking_tool' or label2 == 'tracking_tool':
            return False
        return None
