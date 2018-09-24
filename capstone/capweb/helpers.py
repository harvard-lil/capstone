import json
import requests
import django_hosts


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

# These functions are a direct passthrough to django_hosts.reverse for now, but kept as a wrapper so we can tweak as needed.
reverse = django_hosts.reverse
reverse_lazy = django_hosts.reverse_lazy
