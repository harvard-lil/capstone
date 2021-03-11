
def validate_timeline(timeline):
    timeline_fields = [
        {'name': 'title', 'type': str, 'required': True},
        {'name': 'description', 'type': str, 'required': False},
        {'name': 'cases', 'type': list, 'required': False},
        {'name': 'events', 'type': list, 'required': False},
    ]

    event_fields = [
        {'name': 'name', 'type': str, 'required': True},
        {'name': 'short_description', 'type': str, 'required': False},
        {'name': 'long_description', 'type': str, 'required': False},
        {'name': 'start_date', 'type': str, 'required': True},
        {'name': 'end_date', 'type': str, 'required': True},
    ]

    case_fields = [
        {'name': 'name', 'type': str, 'required': True},
        {'name': 'short_description', 'type': str, 'required': False},
        {'name': 'long_description', 'type': str, 'required': False},
        {'name': 'jurisdiction', 'type': str, 'required': False},
        {'name': 'decision_date', 'type': str, 'required': True},
        {'name': 'reporter', 'type': str, 'required': False},
        {'name': 'url', 'type': str, 'required': False},
        {'name': 'citation', 'type': str, 'required': False},
    ]

    bad = []
    for field in timeline_fields:
        if field['name'] not in timeline:
            if field['required']:
                bad.append("Timeline Missing: {}".format(field['name']))
            break
        if type(timeline[field['name']]) != field['type']:
            bad.append("Wrong Data Type for {}. Should be {}. Value: {}".format(
                     field['name'], field['type'], timeline[field['name']]))

    if 'events' in timeline:
        for field in event_fields:
            for event in timeline['events']:
                if field['name'] not in event:
                    if field['required']:
                        bad.append("Event Missing: {}".format(field['name']))
                    break
                if type(event[field['name']]) != field['type']:
                    bad.append("Event Has Wrong Data Type for {}. Should be {}. Value: {}".format(
                             field['name'], field['type'], event[field['name']]))

    if 'cases' in timeline:
        for field in case_fields:
            for case in timeline['cases']:
                if field['name'] not in case:
                    if field['required']:
                        bad.append("Case Missing: {}".format(field['name']))
                    break
                if type(case[field['name']]) != field['type']:
                    bad.append("Case Has Wrong Data Type for {}. Should be {}. Value: {}".format(
                             field['name'], field['type'], case[field['name']]))

    return bad
