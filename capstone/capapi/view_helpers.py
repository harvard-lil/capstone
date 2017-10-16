import logging
import operator

from django.db.models import Q
from functools import reduce

from capapi import constants

logger = logging.getLogger(__name__)


def format_query(params, args_dict=dict()):
    """
    format all query params except those native to Django Rest
    (such as page, and offset)
    and max and type, which we handle in a special way later on
    """
    if not len(params):
        return args_dict

    blacklisted_keys = ['type', 'page', 'offset', 'max']
    for key, val in list(params.items()):
        if key == 'min_year':
            args_dict['decision_date__gte'] = val
        elif key == 'max_year':
            args_dict['decision_date__lte'] = val
        elif '_' in key and key != 'docket_number':
            splitkey = key.split('_')
            args_dict[splitkey[0] + '__' + splitkey[1]] = val
        else:
            if key not in blacklisted_keys:
                args_dict[key] = val
    return args_dict


def make_query(query_pair):
    (key, val) = query_pair
    if val:
        qwarg = {}
        if ('_id' not in key) and ('decision_date' not in key):
            key = key + '__iexact'
        qwarg[key] = val
        return Q(**qwarg)


def merge_filters(q_list, operation):
    reducer_operation = operator.or_ if operation == 'OR' else operator.and_
    return reduce(reducer_operation, q_list)


def generate_filters_from_query_params(query_params):
    # format queries
    query_dict = format_query(query_params, dict())
    # create Q object query dict
    queries = list(map(make_query, query_dict.items()))
    logger.info("query %s" % queries)
    if len(queries):
        filters = merge_filters(queries, 'AND')
        return filters
    return


def get_whitelisted_case_filters():
    """
    Get query filters for only whitelisted cases
    will look something like:
    [<Q: (AND: ('jurisdiction__name__iexact', 'Illinois'))>, <Q: (AND: ('jurisdiction__name__iexact', 'Arkansas'))>]

    We can use this to filter out for only whitelisted cases
    or exclude whitelisted entirely
    """
    whitelisted_tuples = map(lambda jurisdiction: ("jurisdiction__name", jurisdiction), constants.OPEN_CASE_JURISDICTIONS)
    whitelisted_queries = map(make_query, whitelisted_tuples)
    return merge_filters(whitelisted_queries, 'AND')

