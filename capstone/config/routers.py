class SeparateDatabaseRouter(object):
    """
        Determine how to route database calls for your app and your database.
        All other models will be routed to the next router in the DATABASE_ROUTERS setting if applicable,
        or otherwise to the default database.

        Based on https://strongarm.io/blog/multiple-databases-in-django/
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return self.db_name
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return self.db_name
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """ Allow relations between the models on your specified db. """
        return self.check_permission(obj1._meta.app_label, obj2._meta.app_label)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """ Allow migrations for your app on your db. """
        return self.check_permission(app_label, db)

    def check_permission(self, label1, label2):
        """
            If *both* labels are your specified app, permission is allowed.
            Otherwise if one label is the specified app but not the other, permission is denied.
            This allows relationships within your app and database, but no relationships to other apps/databases.
        """
        if label1 == self.app_label and label2 == self.app_label:
            return True
        if label1 == self.app_label or label2 == self.app_label:
            return False
        return None
