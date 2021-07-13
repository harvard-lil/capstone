import hashlib
import json

import pandas
from flatten_json import flatten

from django.conf import settings
from django.http.response import HttpResponseBase, HttpResponse
from rest_framework import renderers

from capweb.helpers import cache_func


class BrowsableAPIRenderer(renderers.BrowsableAPIRenderer):
    @cache_func(
        key=lambda self, data, view, request: 'filter-form:' + hashlib.md5(
            (request.get_full_path()).encode('utf8')).hexdigest(),
        timeout=settings.CACHED_COUNT_TIMEOUT,
    )
    def get_filter_form(self, data, view, request):
        return super().get_filter_form(data, view, request)

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        if "Instance" in context['name'] and context['response'].status_code == 200:
            try:
                parsed_response = json.loads(context['content'].decode())
                context['page_url'] = parsed_response['url']

                if context['name'] == "Case Instance":
                    context['title'] = parsed_response['name_abbreviation']
                    context['meta_description'] = parsed_response['name']

                if context['name'] == "Jurisdiction Instance":
                    context['title'] = "Jurisdiction: {}".format(parsed_response['name'])
                    context['meta_description'] = "The CAPAPI Jurisdiction Entry for {}".format(parsed_response['name_long'])

                if context['name'] == "Court Instance":
                    context['title'] = parsed_response['name_abbreviation']
                    context['meta_description'] = "The CAPAPI Court Entry for {}".format(parsed_response['name'])

                if context['name'] == "Volume Instance":
                    context['title'] = "{} v.{} ({})".format(parsed_response['reporter'],
                                                             parsed_response['volume_number'],
                                                             parsed_response['publication_year'])
                    context['meta_description'] = "The CAPAPI Volume Entry for {} v. {} ({})".format(
                        parsed_response['reporter'], parsed_response['volume_number'],
                        parsed_response['publication_year'])

                if context['name'] == "Reporter Instance":
                    context['title'] = parsed_response['short_name']
                    context['meta_description'] = "The CAPAPI Court Entry for {}".format(parsed_response['full_name'])

            except Exception:
                return context
        else:
            context['title'] = context['name']
            context['meta_description'] = "CAPAPI: The Caselaw Access Project API"
        return context


class NgramBrowsableAPIRenderer(BrowsableAPIRenderer):
    def get_filter_form(self, data, view, request):
        # Passing in an empty list here makes the filter options show even though this endpoint returns a dictionary
        # instead of a list.
        return super().get_filter_form([], view, request)


class PassthroughRenderer(renderers.JSONRenderer):
    """
        Return data as-is. View should supply a Response.
    """
    media_type = 'application/json'  # used only if rendering errors
    format = ''
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, HttpResponseBase):
            return data
        return super().render(data, accepted_media_type, renderer_context)


class PdfRenderer(renderers.BaseRenderer):
    media_type = 'application/pdf'
    format = 'pdf'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, HttpResponseBase):
            return data
        return HttpResponse(data, content_type=accepted_media_type)


class CSVRenderer(renderers.JSONRenderer):
    media_type = 'text/csv'
    format = 'csv'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if 'results' in data:
            flattened_data = [flatten(case, '.', root_keys_to_ignore={'cites_to'}) for case in data['results']]
            json_normalize = pandas.json_normalize(flattened_data)
        else:
            json_normalize = pandas.json_normalize(flatten(data, '.', root_keys_to_ignore={'cites_to'}))
        return json_normalize.to_csv(index=False)
