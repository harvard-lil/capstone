import hashlib
import re

from django.conf import settings
from rest_framework import renderers

from capapi.resources import cache_func
from scripts.generate_case_html import generate_html
from scripts import helpers


class CaseJSONRenderer(renderers.JSONRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        request = renderer_context['request']

        if 'casebody' not in data:
            return super(CaseJSONRenderer, self).render(data, renderer_context=renderer_context)

        if data['casebody']['status'] != 'ok':
            return super(CaseJSONRenderer, self).render(data, renderer_context=renderer_context)

        body_format = request.query_params.get('body_format', None)

        if body_format == 'html':
            data['casebody']['data'] = generate_html(data['casebody']['data'])
        elif body_format == 'xml':
            extracted = helpers.extract_casebody(data['casebody']['data'])
            c = helpers.serialize_xml(extracted)
            data['casebody']['data'] = re.sub(r"\s{2,}", " ", c.decode())
        else:
            # send text to everyone else
            data['casebody']['data'] = helpers.extract_casebody(data['casebody']['data']).text()

        return super(CaseJSONRenderer, self).render(data, renderer_context=renderer_context)


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
            return generate_xml_error("Case Body Not Retrieved", "When specifying a return format other than JSON, you must explicity specify full_case=true")

        if data['casebody']['status'] != 'ok':
            return generate_xml_error("Case Body Error", data['casebody']['status'])
        else:
            return data['casebody']['data']


class HTMLRenderer(renderers.BaseRenderer):
    media_type = 'text/html'
    format = 'html'

    def render(self, data, media_type=None, renderer_context=None):
        if 'detail' in data:
            if data['detail'] == "Not found.":
                return generate_html_error("Case Not Found.", "The case specified by the URL does not exist in our database.")
            return generate_html_error("Authentication Error", data['detail'])

        # if user requested format=html without requesting full casebody
        if 'casebody' not in data:
            return generate_html_error("Case Body Not Retrieved", "When specifying a return format other than JSON, you must explicity specify full_case=true")

        if data['casebody']['status'] != 'ok':
            return generate_html_error("Case Body Error", data['casebody']['status'], data['first_page'], data['last_page'], data['name'],)
        else:
            return generate_html(data['casebody']['data'])


class BrowsableAPIRenderer(renderers.BrowsableAPIRenderer):
    @cache_func(
        key=lambda self, data, view, request: hashlib.md5(('filter-form:'+request.get_full_path()).encode('utf8')).hexdigest(),
        timeout=settings.API_COUNT_CACHE_TIMEOUT,
    )
    def get_filter_form(self, data, view, request):
        return super().get_filter_form(data, view, request)


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
        %s
        <article class='error'>
            <p>{0}</p>
            <p>{1}</p>
        </article>
        </section>
    """.format(section_and_title, error_text, message_text)

