from django.db.models import Q
import operator

def merge_filters(q_list, operation):
    reducer_operation = operator.or_ if operation == 'OR' else operator.and_
    return reduce(reducer_operation, q_list)

def make_query((key,val)):
    qwarg={}
    qwarg[key]=val
    return Q(**qwarg)
