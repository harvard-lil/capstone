from django.db.models import Q

from rest_framework import routers, serializers, viewsets
from rest_framework import mixins
from rest_framework.decorators import api_view, detail_route, list_route
from rest_framework.response import Response

from capi_project.models import Case
from capi_project.view_helpers import *

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

class CaseSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        many = kwargs.pop('many', True)
        super(CaseSerializer, self).__init__(many=many, *args, **kwargs)
    class Meta:
        model = Case
        fields = '__all__'

class CaseViewSet(viewsets.GenericViewSet,mixins.ListModelMixin):
    http_method_names = ['get']
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    lookup_field='jurisdiction'

    def get_queryset(self):
        query = Q()
        kwargs = self.kwargs
        if len(self.request.query_params.items()):
            kwargs = format_date_queries(self.request.query_params, kwargs)

        if len(kwargs.items()):
            query = map(make_query, kwargs.items())
            query = merge_filters(query, 'AND')

        return self.queryset.filter(query)
