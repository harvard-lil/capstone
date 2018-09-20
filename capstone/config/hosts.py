from django.conf import settings
from django_hosts import patterns, host

hosts = [host(config["subdomain"], config["urlconf"], name=name) for name, config in settings.HOSTS.items()]
host_patterns = patterns('', *hosts)