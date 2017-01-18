from django.db.models import Q
import operator

def merge_filters(q_list, operation):
    reducer_operation = operator.or_ if operation == 'OR' else operator.and_
    return reduce(reducer_operation, q_list)

def make_query((key,val)):
    if val:
        qwarg={}
        if ('_id' not in key) and ('decisiondate' not in key):
            key = key + '__icontains'
        qwarg[key]=val
        return Q(**qwarg)

def format_kwargs(params, args_dict):
    if not len(params):
        return args_dict
    for key,val in params.items():
        if key == 'year':
            args_dict['decisiondate__year'] = val
        elif key == 'month':
            args_dict['decisiondate__month'] = val
        elif key == 'day':
            args_dict['decisiondate__day'] = val
        else:
            if key != 'page' and key != 'offset':
                args_dict[key] = val
    return args_dict

def format_url_from_case(case):
    return "%s/%s/%s/%s/%s" % (case.jurisdiction, case.reporter, case.volume, case.firstpage, case.name_abbreviation)
