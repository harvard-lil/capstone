import hashlib
import json

from django.conf import settings
from django.http.response import HttpResponseBase
from django.template import loader
from rest_framework import renderers

from capweb.helpers import cache_func
from scripts.generate_case_html import generate_html


class XMLRenderer(renderers.BaseRenderer):
    media_type = 'application/xml'
    format = 'xml'

    def render(self, data, media_type=None, renderer_context=None):
        if 'detail' in data:
            if data['detail'] == "Not found.":
                return generate_xml_error("Case Not Found.", "The case specified by the URL does not exist in our database.")

            return generate_xml_error("Authentication Error", data['detail'])

        # if user requested format=xml without requesting full casebody
        if 'casebody' not in data:
            return generate_xml_error("Full Case Parameter Missing in Non-JSON Request", "To retrieve the full case body, you must specify full_case=true in the URL. If you only want metadata, you must specify format=json in the URL. We only serve standalone metadata in JSON format.")

        if data['casebody']['status'] != 'ok':
            if data['casebody']['status'] == 'error_auth_required':
                return generate_xml_error("Not Authenticated ({})".format(data['casebody']['status']), "You must be authenticated to view this case.")
            return generate_xml_error("Could Not Load Case Body", data['casebody']['status'])
        else:
            return data['casebody']['data']


class HTMLRenderer(renderers.StaticHTMLRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        if 'detail' in data:
            if data['detail'] == "Not found.":
                return generate_html_error("Case Not Found.", "The case specified by the URL does not exist in our database.")
            return generate_html_error("Authentication Error", data['detail'])

        # if user requested format=html without requesting full casebody
        if 'casebody' not in data:
            return generate_html_error("Full Case Parameter Missing in Non-JSON Request", "To retrieve the full case body, you must specify <span style='font-family: monospace; font-style: normal;'>full_case=true</span> in the URL. If you only want metadata you must specify <span style='font-family: monospace; font-style: normal;'>format=json</span> in the URL. We only serve standalone metadata in JSON format.")

        if data['casebody']['status'] != 'ok':
            if data['casebody']['status'] == 'error_auth_required':
                return generate_html_error("Not Authenticated <span style='font-family: monospace; font-style: normal;'>({})</span>".format(data['casebody']['status']), "You must be authenticated to view this case.")
            return generate_html_error("Could Not Load Case Body", data['casebody']['status'], data['first_page'], data['last_page'], data['name'])

        official_cit_entries = [ citation['cite'] for citation in data['citations'] if citation['type'] == 'official' ]
        official_citation = official_cit_entries[0] if len(official_cit_entries[0]) > 0 else None

        template = loader.get_template('case.html')
        context = {
            'citation': official_citation,
            'title': data['casebody']['title'],
            'case_html': generate_html(data['casebody']['data']),
            'page_description': data['name'],
            'page_title': data['name_abbreviation'],
        }
        return template.render(context, renderer_context['request'])


class BrowsableAPIRenderer(renderers.BrowsableAPIRenderer):
    @cache_func(
        key=lambda self, data, view, request: 'filter-form:'+hashlib.md5((request.get_full_path()).encode('utf8')).hexdigest(),
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
                    context['page_title'] = parsed_response['name_abbreviation']
                    context['page_description'] = parsed_response['name']

                if context['name'] == "Jurisdiction Instance":
                    context['page_title'] = "Jurisdiction: {}".format(parsed_response['name'])
                    context['page_description'] = "The CAPAPI Jurisdiction Entry for {}".format(parsed_response['name_long'])

                if context['name'] == "Court Instance":
                    context['page_title'] = parsed_response['name_abbreviation']
                    context['page_description'] = "The CAPAPI Court Entry for {}".format(parsed_response['name'])

                if context['name'] == "Volume Instance":
                    context['page_title'] = "{} v.{} ({})".format(parsed_response['reporter'], parsed_response['volume_number'], parsed_response['publication_year'])
                    context['page_description'] = "The CAPAPI Volume Entry for {} v. {} ({})".format(parsed_response['reporter'], parsed_response['volume_number'], parsed_response['publication_year'])

                if context['name'] == "Reporter Instance":
                    context['page_title'] = parsed_response['short_name']
                    context['page_description'] = "The CAPAPI Court Entry for {}".format(parsed_response['full_name'])

            except:
                return context
        else:
            context['page_title'] = context['name']
            context['page_description'] = "CAPAPI: The Caselaw Access Project API"
        return context

class PassthroughRenderer(renderers.JSONRenderer):
    """
        Return data as-is. View should supply a Response.
    """
    media_type = 'application/json'  # used only for rendering errors
    format = ''
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, HttpResponseBase):
            return data
        return super().render(data, accepted_media_type, renderer_context)



def generate_xml_error(error_text, message_text):
    return """
        <data>
            <error>%s</error>
            <message>%s</message>
        </data>
    """ % (error_text, message_text)

def generate_html_error(error_text, message_text, first_page=None, last_page=None, case_name=None):
    if first_page is not None and last_page is not None and case_name is not None:
        section_and_title = """
        <section data-data-firstpage="{0}" data-data-lastpage="{1}" data-class="casebody">
        <h4>{2}</h4>
        """.format(first_page, last_page, case_name)
    else:
        section_and_title = "<section>"

    return """
        {}
        <article class='error'>
            <h1>Error: {}</h1>
            <p><span style="font-weight: bold;">Details:</span> <span style="font-style: italic;">{}</span></p>
        </article>
        </section>
    """.format(section_and_title, error_text, message_text)

