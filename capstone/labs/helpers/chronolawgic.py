class TimelineValidationException(Exception):
    pass


def validate_and_normalize_timeline(timeline):
    root_fields = [
        {'name': 'title', 'type': str, 'required': True, 'default': 'Untitled Timeline'},
        {'name': 'author', 'type': str, 'required': True, 'default': 'CAP user'},
        {'name': 'description', 'type': str, 'required': False},
        {'name': 'cases', 'type': list, 'required': False},
        {'name': 'events', 'type': list, 'required': False},
        {'name': 'categories', 'type': list, 'required': False},
    ]

    event_fields = [
        {'name': 'id', 'type': str, 'required': True},
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
        {'name': 'id', 'type': str, 'required': True},
        {'name': 'name', 'type': str, 'required': True},
        {'name': 'short_description', 'type': str, 'required': False},
        {'name': 'long_description', 'type': str, 'required': False},
        {'name': 'jurisdiction', 'type': str, 'required': False},
        {'name': 'decision_date', 'type': str, 'required': True},
        {'name': 'reporter', 'type': str, 'required': False},
        {'name': 'court', 'type': str, 'required': False},
        {'name': 'url', 'type': str, 'required': False},
        {'name': 'citation', 'type': str, 'required': False},
        {'name': 'categories', 'type': list, 'required': False},
        {'name': 'color', 'type': str, 'required': False},
    ]

    category_fields = [
        {'name': 'id', 'type': str, 'required': True},
        {'name': 'name', 'type': str, 'required': True},
        {'name': 'color', 'type': str, 'required': True},
        {'name': 'shape', 'type': str, 'required': True},
    ]

    def validate_list_entry(fields, input_list, name):
        local_bad = []

        # is this even the right thing?
        if type(input_list) != dict:
            return [input_list, ["Wrong Data Type for {} entry: {} instead of dict".format( name, type(input_list))]]

        # do we have extra fields?
        known_field_names = [field['name'] for field in fields]
        extraneous = set(input_list.keys()) - set(known_field_names)
        for extraneous_field in extraneous:
            if not input_list[extraneous_field]:  # if the field is empty, just remove it
                del input_list[extraneous_field]
                input_list.remove(extraneous_field)

        if extraneous:
            local_bad.append("Unexpected {} field(s): {}. Expecting {}".format(
                name,
                extraneous,
                known_field_names
            ))

        # do we have every field, and are they the correct data type?
        for field in fields:
            if field['name'] not in input_list:
                if 'default' in field:
                    input_list[field['name']] = field['default']
                elif not field['required']:
                    input_list[field['name']] = field['type']()
                else: # definitely need this
                    local_bad.append("Missing {} field {}".format(name, field['name']))
            elif type(input_list[field['name']]) != field['type']:
                if 'default' in field:
                    input_list[field['name']] = field['default']
                elif not field['required'] or not input_list[field['name']]:
                    input_list[field['name']] = field['type']()
                else:  # definitely need this
                    local_bad.append("Wrong Data Type for {}. Should be {}. Value: {}".format(
                    field['name'], field['type'], input_list[field['name']]))
            elif input_list[field['name']] == '' and 'default' in field:
                    input_list[field['name']] = field['default']
        return [input_list, local_bad]

    timeline, timeline_bad = validate_list_entry(root_fields, timeline, 'timeline')

    events_bad = []
    for index, event in enumerate(timeline['events']):
        timeline['events'][index], event_bad = validate_list_entry(event_fields, event, 'event')
        events_bad = events_bad + event_bad

    cases_bad = []
    for index, case in enumerate(timeline['cases']):
        timeline['cases'][index], case_bad = validate_list_entry(case_fields, case, 'case')
        cases_bad = cases_bad + case_bad

    categories_bad = []
    for index, category in enumerate(timeline['categories']):
        timeline['categories'][index], category_bad = validate_list_entry(category_fields, category, 'category')
        categories_bad = categories_bad + category_bad

    bad = timeline_bad + events_bad + cases_bad + categories_bad

    if bad:
        raise TimelineValidationException(bad)
    
    return timeline
