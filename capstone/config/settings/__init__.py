# This is the base module that will be imported by Django.

# Try to import the custom settings.py file, which will in turn import one of the deployment targets.
# If it doesn't exist we assume this is a vanilla development environment and import .deployments.settings_dev.
try:
    from .settings import *  # noqa
except ImportError as e:
    if e.msg == "No module named 'config.settings.settings'":
        from .settings_dev import *  # noqa
    else:
        raise