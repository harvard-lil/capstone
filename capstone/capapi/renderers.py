import hashlib

from django.conf import settings
from rest_framework import renderers

from capapi.resources import cache_func
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
            return generate_xml_error("Case Body Not Retrieved", "When specifying a return format other than JSON, you must explicity specify full_case=true")

        if data['casebody']['status'] != 'ok':
            return generate_xml_error("Case Body Error", data['casebody']['status'])
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
            return generate_html_error("Case Body Not Retrieved", "When specifying a return format other than JSON, you must explicity specify full_case=true")

        if data['casebody']['status'] != 'ok':
            return generate_html_error("Case Body Error", data['casebody']['status'], data['first_page'], data['last_page'], data['name'],)

        return super().render(generate_html(data['casebody']['data']), media_type, renderer_context)


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
        {}
        <article class='error'>
            <p>{}</p>
            <p>{}</p>
        </article>
        </section>
    """.format(section_and_title, error_text, message_text)

