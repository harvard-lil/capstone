import operator

from django.db.models import Q


def merge_filters(q_list, operation):
    reducer_operation = operator.or_ if operation == 'OR' else operator.and_
    return reduce(reducer_operation, q_list)


def make_query((key, val)):
    if val:
        qwarg = {}
        if ('_id' not in key) and ('decisiondate' not in key):
            key = key + '__icontains'
        qwarg[key] = val
        return Q(**qwarg)


def format_query(params, args_dict):
    blacklisted_keys = ['type', 'page', 'offset']
    if not len(params):
        return args_dict

    for key, val in params.items():
        if key == 'min_year':
            args_dict['decisiondate__gte'] = val
        elif key == 'max_year':
            args_dict['decisiondate__lte'] = val
        elif '_' in key:
            splitkey = key.split('_')
            args_dict[splitkey[0] + '__' + splitkey[1]] = val
        else:
            if key not in blacklisted_keys:
                args_dict[key] = val
    return args_dict


def format_url_from_case(case):
    return "%s/%s/%s/%s/%s" % (
        case.jurisdiction,
        case.reporter,
        case.volume,
        case.firstpage,
        case.name_abbreviation
    )
