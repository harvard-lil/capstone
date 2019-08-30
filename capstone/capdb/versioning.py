from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from simple_history.models import HistoricalRecords

class DefaultDateTimeRangeField(DateTimeRangeField):
    """ Postgres tstzrange field that defaults to (current_timestamp, null)"""
    def db_type(self, connection):
        return 'tstzrange DEFAULT tstzrange(current_timestamp, null)'


class TemporalHistoricalRecords(HistoricalRecords):
    """
        Our historical tables are based on django-simple-history's HistoricalRecords.
        This does the work of automatically generating historical tables from model definitions,
        keeping them in sync through migrations, and adding a Model.history attribute to look up
        historical versions.

        We populate the history table through postgres triggers rather than python code,
        so most other features of django-simple-history are disabled by this subclass.

        This class is designed to be compatible with the conventions of the popular temporal_tables
        Postgres plugin, meaning it uses tables called <table_name>_history with date range columns
        called sys_period.

        See https://pgxn.org/dist/temporal_tables/
    """

    def contribute_to_class(self, cls, name):
        """
            Add a read-only sys_period field to the model, which will be populated by database triggers and defaults.
        """
        super().contribute_to_class(cls, name)

        # add sys_period field:
        sys_period_field = DefaultDateTimeRangeField()
        cls.add_to_class('sys_period', sys_period_field)

        # filter out sys_period from updates:
        def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
            values = [v for v in values if v[0] != sys_period_field]
            if update_fields:
                update_fields = tuple(f for f in update_fields if f != sys_period_field)
            return super(cls, self)._do_update(base_qs, using, pk_val, values, update_fields, forced_update)
        cls.add_to_class('_do_update', _do_update)

        # filter out sys_period from inserts:
        def _do_insert(self, manager, using, fields, update_pk, raw):
            fields = tuple(f for f in fields if f != sys_period_field)
            return super(cls, self)._do_insert(manager, using, fields, update_pk, raw)
        cls.add_to_class('_do_insert', _do_insert)

    def create_history_model(self, model, inherited):
        """
            Set name of history table to original table name + '_history'
        """
        if not self.table_name:
            self.table_name = model._meta.db_table + '_history'
        return super().create_history_model(model, inherited)

    def get_extra_fields(self, model, fields):
        """
            Configure fields of the history table.
        """
        out = super().get_extra_fields(model, fields)

        # remove most of the extra fields added by django-simple-history.
        # keep history_id because we need a primary key for Django.
        out = {k: v for k, v in out.items() if k == 'history_id' or not isinstance(v, models.Field)}

        # override string representation of history model to use the date range
        out['__str__'] = lambda self: '%s as of %s' % (self.history_object, self.sys_period)
        out['history_date'] = lambda self: "%s to %s" % (
            self.sys_period.lower.strftime('%B %d, %Y %I:%M%p') if self.sys_period.lower else "-",
            self.sys_period.upper.strftime('%B %d, %Y %I:%M%p') if self.sys_period.upper else "-",
        )

        return out

    def get_meta_options(self, model):
        """ Use sys_period field for ordering. """
        out = super().get_meta_options(model)
        out['ordering'] = ('-sys_period', '-history_id')
        out['get_latest_by'] = 'history_date'
        return out

    # disable post_save and post_delete actions, as we do updating through postgres triggers
    def post_save(self, *args, **kwargs):
        pass
    def post_delete(self, *args, **kwargs):
        pass


class TemporalQuerySet(models.QuerySet):
    """
        Necessary for bulk_insert to work on history-tracked models.
    """
    def _batched_insert(self, objs, fields, *args, **kwargs):
        fields = [f for f in fields if f.name != 'sys_period']
        return super()._batched_insert(objs, fields, *args, **kwargs)