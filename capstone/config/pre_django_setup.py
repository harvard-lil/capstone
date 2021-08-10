# steps to run before importing django

# patch this here because we have to make sure we do it before any file imports the eyecite library
import scripts.patch_reporters_db  # noqa

# patch django's CursorDebugWrapper before any other file imports it
import django_sql_trace  # noqa
