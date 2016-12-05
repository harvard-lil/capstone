from django.db.models import Q
import operator

def merge_filters(q_list, operation):
    reducer_operation = operator.or_ if operation == 'OR' else operator.and_
    return reduce(reducer_operation, q_list)

def make_query((key,val)):
    qwarg={}

    if key == 'name_abbreviation':
        key = key + '__icontains'
    else:
        key = key + '__iexact'
    qwarg[key]=val
    return Q(**qwarg)

def format_date_queries(params, args_dict):
    if not len(params):
        return args_dict

    if 'year' in params:
        args_dict['decisiondate__year'] = params['year']

    if 'month' in params:
        args_dict['decisiondate__month'] = params['month']

    if 'day' in params:
        args_dict['decisiondate__day'] = params['day']
    return args_dict
