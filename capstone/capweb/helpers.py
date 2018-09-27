import json
import requests
import django_hosts
from django.urls import NoReverseMatch
from django_hosts.resolvers import get_host_patterns


def get_data_from_lil_site(section="news"):
    response = requests.get("https://lil.law.harvard.edu/api/%s/caselaw-access-project/" % section)
    content = response.content.decode()
    start_index = content.index('(')
    if section == "contributors":
        # account for strangely formatted response
        end_index = content.index(']}') + 2
    else:
        end_index = -1
    data = json.loads(content.strip()[start_index + 1:end_index])
    return data[section]

def reverse(*args, **kwargs):
    """
        Wrap django_hosts.reverse() to try all known hosts.
    """
    # if host is provided, just use that
    if 'host' in kwargs:
        return django_hosts.reverse(*args, **kwargs)

    # try each host
    hosts = get_host_patterns()
    for i, host in enumerate(reversed(hosts)):
        kwargs['host'] = host.name
        try:
            return django_hosts.reverse(*args, **kwargs)
        except NoReverseMatch:
            # raise NoReverseMatch only after testing final host
            if i == len(hosts)-1:
                raise

