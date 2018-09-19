import json
import requests
from django_hosts import reverse as django_hosts_reverse


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
        This is a direct passthrough to django_hosts.reverse for now, but kept as a wrapper so we can tweak as needed.
    """
    return django_hosts_reverse(*args, **kwargs)