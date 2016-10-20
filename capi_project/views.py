from django.db.models import Q

from rest_framework import routers, serializers, viewsets
from rest_framework import mixins
from rest_framework.decorators import api_view, detail_route, list_route
from rest_framework.response import Response

from capi_project.models import Case
from capi_project.url_helpers import *

class CaseSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        many = kwargs.pop('many', True)
        print 'many', kwargs
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
        result = self.queryset
        query = Q()
        if len(self.kwargs.items()):
            query = map(make_query, self.kwargs.items())
            query = merge_filters(query, 'AND')

        return self.queryset.filter(query)
