from django.contrib.postgres.search import SearchQuery, SearchQueryField
from django.db.models.expressions import Value

class SearchQueryTemp(SearchQuery, Value):
    output_field = SearchQueryField()
    SEARCH_TYPES = {
        'plain': 'plainto_tsquery',
        'phrase': 'phraseto_tsquery',
        'raw': 'to_tsquery',
    }

    def __init__(self, value, output_field=None, *, config=None, invert=False, search_type='plain'):
        self.config = config
        self.invert = invert
        if search_type not in self.SEARCH_TYPES:
            raise ValueError("Unknown search_type argument '%s'." % search_type)
        self.search_type = search_type
        super().__init__(value, output_field=output_field)

    def as_sql(self, compiler, connection):
        params = [self.value]
        function = self.SEARCH_TYPES[self.search_type]
        if self.config:
            config_sql, config_params = compiler.compile(self.config)
            template = '{}({}::regconfig, %s)'.format(function, config_sql)
            params = config_params + [self.value]
        else:
            template = '{}(%s)'.format(function)
        if self.invert:
            template = '!!({})'.format(template)
        return template, params
