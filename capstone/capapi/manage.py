#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "capapi.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        try:
            import django
            django.setup()

        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise

    from django.core.management.commands.runserver import Command as runserver
    runserver.default_port = "8080"

    execute_from_command_line(sys.argv)
