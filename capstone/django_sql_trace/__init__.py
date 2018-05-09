from django.conf import settings
from django.utils.module_loading import import_string
import django.db.backends.base.base

WrapperClass = import_string(getattr(settings, 'SQL_TRACE_WRAPPER_CLASS', 'django_sql_trace.wrapper.TracingDebugWrapper'))
django.db.backends.base.base.BaseDatabaseWrapper.make_debug_cursor = lambda self, cursor: WrapperClass(cursor, self)