import re
from rest_framework import renderers
from scripts.generate_case_html import generate_html
from scripts import helpers


class JSONRenderer(renderers.JSONRenderer):
    media_type = 'application/json'
    format = 'json'

    def render(self, data, media_type=None, renderer_context=None):
        request = renderer_context['request']

        if 'casebody' not in data:
            return super(JSONRenderer, self).render(data, renderer_context=renderer_context)

        if data['casebody']['status'] != 'ok':
            return super(JSONRenderer, self).render(data, renderer_context=renderer_context)

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

        return super(JSONRenderer, self).render(data, renderer_context=renderer_context)


class XMLRenderer(renderers.BaseRenderer):
    media_type = 'application/xml'
    format = 'xml'

    def render(self, data, media_type=None, renderer_context=None):
        if 'detail' in data:
            return """
                <data>
                    <error>Authentication Error</error>
                    <message>%s</message>
                </data>s
            """ % (data['detail'])

        # if user requested format=xml without requesting full casebody
        if 'casebody' not in data:
            return """
                <data>
                    <error>Not Allowed Error</error>     
                </data>
            """

        if data['casebody']['status'] != 'ok':
            return """
                <data>
                    <error>Casebody Error</error>
                    <message>%s</message>
                </data>
            """ % (data['casebody']['status'])
        else:
            return data['casebody']['data']


class HTMLRenderer(renderers.BaseRenderer):
    media_type = 'text/html'
    format = 'html'

    def render(self, data, media_type=None, renderer_context=None):
        if 'detail' in data:
            return """
                <section>
                    <article class='error'>
                        <p>Authentication Error</p>
                        <p>%s</p>
                    </article>
                </section>
            """ % (data['detail'])

        # if user requested format=html without requesting full casebody
        if 'casebody' not in data:
            return """
                <section>
                    <article class='error'>
                        <p>Not Allowed Error</p>
                    </article>
                </section>
            """

        if data['casebody']['status'] != 'ok':
            return """
                <section data-data-firstpage="%s" data-data-lastpage="%s" data-class="casebody">
                <h4>%s</h4>
                <article class='error'>
                    <p>Casebody Error</p>
                    <p>%s</p>
                </article>
                </section>
            """ % (data['first_page'],
                   data['last_page'],
                   data['name'],
                   data['casebody']['status'])
        else:
            return generate_html(data['casebody']['data'])
