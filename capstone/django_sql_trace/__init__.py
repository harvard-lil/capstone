import django.db.backends.utils

from .wrapper import TracingDebugWrapper

django.db.backends.utils.CursorDebugWrapper = TracingDebugWrapper
