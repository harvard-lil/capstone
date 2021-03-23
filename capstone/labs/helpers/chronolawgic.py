
def validate_timeline(timeline):
    timeline_fields = [
        {'name': 'title', 'type': str, 'required': True},
        {'name': 'description', 'type': str, 'required': False},
        {'name': 'cases', 'type': list, 'required': False},
        {'name': 'events', 'type': list, 'required': False},
    ]

    event_fields = [
        {'name': 'id', 'type': int, 'required': True},
        {'name': 'name', 'type': str, 'required': True},
        {'name': 'short_description', 'type': str, 'required': False},
        {'name': 'long_description', 'type': str, 'required': False},
        {'name': 'start_date', 'type': str, 'required': True},
        {'name': 'end_date', 'type': str, 'required': True},
        {'name': 'color', 'type': str, 'required': False},
        {'name': 'categories', 'type': list, 'required': False},
        {'name': 'url', 'type': str, 'required': False},
    ]

    case_fields = [
        {'name': 'id', 'type': int, 'required': True},
        {'name': 'name', 'type': str, 'required': True},
        {'name': 'short_description', 'type': str, 'required': False},
        {'name': 'long_description', 'type': str, 'required': False},
        {'name': 'jurisdiction', 'type': str, 'required': False},
        {'name': 'decision_date', 'type': str, 'required': True},
        {'name': 'reporter', 'type': str, 'required': False},
        {'name': 'url', 'type': str, 'required': False},
        {'name': 'citation', 'type': str, 'required': False},
        {'name': 'categories', 'type': list, 'required': False},
    ]

    bad = []

    # make sure there are no extraneous fields
    known_field_names = [field['name'] for field in timeline_fields]
    extraneous = set(timeline.keys()) - set(known_field_names)
    if extraneous:
        bad.append("Unexpected timeline field(s): {}. Expecting {}".format(
            extraneous,
            known_field_names
        ))

    for field in timeline_fields:
        if field['name'] not in timeline:
            if field['required']:
                bad.append("Timeline Missing: {}".format(field['name']))
            break
        if type(timeline[field['name']]) != field['type']:
            bad.append("Wrong Data Type for {}. Should be {}. Value: {}".format(
                     field['name'], field['type'], timeline[field['name']]))

    if 'events' in timeline:
        known_event_field_names = [field['name'] for field in event_fields]
        for field in event_fields:
            for event in timeline['events']:
                event_extraneous = set(event.keys()) - set(known_event_field_names)
                if event_extraneous:
                    bad.append("Unexpected event field(s): {}. Expecting {}".format(
                        event_extraneous,
                        known_event_field_names
                    ))
                if field['name'] not in event:
                    if field['required']:
                        bad.append("Event Missing: {}".format(field['name']))
                    break
                if type(event[field['name']]) != field['type']:
                    bad.append("Event Has Wrong Data Type for {}. Should be {}. Value: {}".format(
                             field['name'], field['type'], event[field['name']]))

    if 'cases' in timeline:
        known_case_field_names = [field['name'] for field in case_fields]
        for field in case_fields:
            for case in timeline['cases']:
                case_extraneous = set(case.keys()) - set(known_case_field_names)
                if case_extraneous:
                    bad.append("Unexpected case field(s): {}. Expecting {}".format(
                        case_extraneous,
                        known_case_field_names
                    ))
                if field['name'] not in case:
                    if field['required']:
                        bad.append("Case Missing: {}".format(field['name']))
                    break
                if type(case[field['name']]) != field['type']:
                    bad.append("Case Has Wrong Data Type for {}. Should be {}. Value: {}".format(
                             field['name'], field['type'], case[field['name']]))

    return bad
