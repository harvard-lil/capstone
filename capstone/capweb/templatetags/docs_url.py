from django import template

from capweb.helpers import reverse, get_doc_links

register = template.Library()


doc_links = get_doc_links()


@register.simple_tag()
def docs_url(doc_link):
    """
        Link to a documentation page. This can either be the value of the `doc_link:` key in the markdown file,
        if there is one, or else the text part of the filename ('example' from '01_example.md').

        This allows us to consistently link to docs pages when they are moved or reordered.
    """
    return reverse('docs', args=[doc_links[doc_link]])
