import json
import re
import socket
import requests
from collections import namedtuple, OrderedDict
from contextlib import contextmanager
import django_hosts
from elasticsearch.exceptions import NotFoundError
from functools import wraps, lru_cache
from urllib.parse import urlencode
from pathlib import Path
import markdown
from django.core.signing import Signer
from django.template.loader import render_to_string
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.toc import TocExtension
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework import renderers
from rest_framework.request import Request as RestRequest

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core.cache import caches
from django.core.mail import EmailMessage
from django.db import transaction, connections, OperationalError
from django.urls import NoReverseMatch
from django.utils.functional import lazy
from django.utils.safestring import mark_safe


def cache_func(key, timeout=None, cache_name='default'):
    """
        Decorator to cache decorated function's output according to a custom key.
        `key` should be a lambda that takes the decorated function's arguments and returns a cache key.
    """
    cache = caches[cache_name]
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            cache_key = key(*args, **kwargs)

            # return existing value, if any
            value = cache.get(cache_key)
            if value is not None:
                print("Got existing for", cache_key)
                return value
            print("Making new for", cache_key)

            # cache new value
            value = func(*args, **kwargs)
            cache.set(cache_key, value, timeout)
            return value
        return decorated
    return decorator

@cache_func(
    key=lambda section: 'get_data_from_lil_site:%s' % section,
    timeout=settings.CACHED_LIL_DATA_TIMEOUT
)
def get_data_from_lil_site(section="news"):
    try:
        response = requests.get("https://lil.law.harvard.edu/api/%s/caselaw-access-project/" % section)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return []
    content = response.content.decode()
    start_index = content.index('(')
    if section == "contributors":
        # account for strangely formatted response
        end_index = content.index(']}') + 2
    else:
        end_index = -1
    data = json.loads(content.strip()[start_index + 1:end_index])
    return data[section]

_host_names = sorted(settings.HOSTS.keys())

def reverse(*args, **kwargs):
    """
        Wrap django_hosts.reverse() to try all known hosts.
    """
    kwargs.setdefault('scheme', 'https' if settings.MAKE_HTTPS_URLS else 'http')

    # if host is provided, just use that
    if 'host' in kwargs:
        return django_hosts.reverse(*args, **kwargs)

    # try each host
    for i, host_name in enumerate(_host_names):
        kwargs['host'] = host_name
        try:
            return django_hosts.reverse(*args, **kwargs)
        except NoReverseMatch:
            # raise NoReverseMatch only after testing final host
            if i == len(_host_names)-1:
                raise

reverse_lazy = lazy(reverse, str)

def show_toolbar_callback(request):
    """
        Whether to show django-debug-toolbar.
        This adds an optout for urls with ?no_toolbar
    """
    from debug_toolbar.middleware import show_toolbar
    return False if 'no_toolbar' in request.GET else show_toolbar(request)


class StatementTimeout(Exception):
    pass

@contextmanager
def statement_timeout(timeout, db="default"):
    """
        Context manager to kill queries if they take longer than `timeout` seconds.
        Timed-out queries will raise StatementTimeout.
    """
    with transaction.atomic(using=db):
        with connections[db].cursor() as cursor:
            cursor.execute("SHOW statement_timeout")
            original_timeout = cursor.fetchone()[0]
            cursor.execute("SET LOCAL statement_timeout = '%ss'" % timeout)
            try:
                yield
            except OperationalError as e:
                if e.args[0] == 'canceling statement due to statement timeout\n':
                    raise StatementTimeout()
                raise
            # reset to default, in case we're in a nested transaction
            cursor.execute("SET LOCAL statement_timeout = %s", [original_timeout])

@contextmanager
def transaction_safe_exceptions(using=None):
    """
        If we are in a transaction, then it doesn't work to catch ORM errors like DoesNotExist or IntegrityError,
        as they abort the transaction. This context manager starts a sub-transaction to catch the errors, only
        if necessary. Example:

            with transaction.atomic(using='capstone'):
                try:
                    with transaction_safe_exceptions():
                        Foo.objects.get(id=1)
                except Foo.DoesNotExist:
                    pass
                    # ORM queries here will still work thanks to calling transaction_safe_exceptions()
    """
    if transaction.get_connection(using=using).in_atomic_block:
        with transaction.atomic(using=using):
            yield
    else:
        yield

def select_raw_sql(sql, args=None, using=None):
    with connections[using].cursor() as cursor:
        cursor.execute(sql, args)
        nt_result = namedtuple('Result', [col[0] for col in cursor.description])
        return [nt_result(*row) for row in cursor.fetchall()]

def send_contact_email(title, content, from_address):
    """
        Send a message on behalf of a user to our contact email.
        Use reply-to for the user address so we can use email services that require authenticated from addresses.
    """
    EmailMessage(
        title,
        content,
        settings.DEFAULT_FROM_EMAIL,
        [settings.DEFAULT_FROM_EMAIL],
        headers={'Reply-To': from_address}
    ).send(fail_silently=False)


def user_has_harvard_email(failure_url='non-harvard-email'):
    """
        Decorator to forward user if they don't have Harvard email. E.g.:

        @user_has_harvard_email()
        def my_view(request):
    """
    return user_passes_test(
        test_func=lambda u: bool(re.search(r'[.@]harvard.edu$', u.email)),
        login_url=failure_url)


def render_markdown(markdown_doc):
    """
        Render given markdown document and return (html, table_of_contents, meta)
    """

    md = markdown.Markdown(extensions=[TocExtension(baselevel=2, marker=''), AttrListExtension(), listStyleExtension(),
                                       'meta'])
    html = md.convert(markdown_doc.lstrip())
    toc = md.toc.replace('<a ', '<a class="list-group-item" ').replace('<li', '<li class="doc-toc-item"')
    toc = "".join(toc.splitlines(True)[2:-2])  # strip <div><ul> around toc by dropping first and last two lines
    meta = {k:' '.join(v) for k, v in md.Meta.items()}
    return html, toc, meta

class listStyleExtension(Extension):
    """
        This extension to the Markdown library looks at li elements which have the add_list_class attribute and
        adds the space-separated list of classes to its parent ul or ol element
    """
    def extendMarkdown(self, md):
        md.treeprocessors.register(listStyleProcessor(md), 'list_style', 7)

class listStyleProcessor(Treeprocessor):
    """
        This is the meat of the listStyleExtension extension for python markdown
    """
    def run(self, tree):
        # the list comprehension that feeds this for loop returns the parent (/..) of all list items regardless of their
        # location in the document (//li) if they have the add_list_class attribute ([@add_list_class])
        for modified_parent in [ element for element in tree.findall('.//li[@add_list_class]/..') ]:
            existing_classes = [] if 'class' not in modified_parent.attrib \
                else modified_parent.attrib['class'].split(' ')
            new_classes = [word for child in modified_parent.findall('./li[@add_list_class]')
                           for word in child.attrib['add_list_class'].split(' ')]
            # assigns re-assigns the class as a space separated list of unique classes
            modified_parent.attrib['class'] = " ".join(list(set(new_classes + existing_classes)))
        return tree

def is_google_bot(request):
    """
    from https://blog.majsky.cz/detecting-google-bot-python-and-django/
    """
    if "Googlebot" not in request.META.get('HTTP_USER_AGENT', ''):
        return False
    ip = request.user.ip_address
    try:
        host = socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.error):
        return False
    domain_name = ".".join(host.split('.')[1:])
    if domain_name not in ['googlebot.com', 'google.com']:
        return False
    host_ip = socket.gethostbyname(host)
    return host_ip == ip


def page_image_url(url, targets=[], waits=[], fallback=None, timeout=None):
    """
        Generate a link to the /screenshot/ view for the given url and target.
    """
    payload = OrderedDict({'url': url})
    if targets:
        payload['targets'] = targets
    if waits:
        payload['waits'] = waits
    if fallback:
        payload['fallback'] = fallback
    if timeout is not None:
        payload['timeout'] = timeout
    signed_payload = Signer().sign(json.dumps(payload))
    return "%s?%s" % (reverse('screenshot'), urlencode({
        'payload': signed_payload,
    }))


def is_browser_request(request):
    """
    Differentiate between command line and browser requests
    """
    drf_renderer = DefaultContentNegotiation().select_renderer(RestRequest(request), [renderers.JSONRenderer, renderers.TemplateHTMLRenderer])
    return drf_renderer[0] is renderers.TemplateHTMLRenderer


safe_domains = [(h['subdomain']+"." if h['subdomain'] else "") + settings.PARENT_HOST for h in settings.HOSTS.values()]


### docs indexing ###
# functions to load and index the documentation files in templates/docs

docs_path = Path(__file__).parent.joinpath('templates/docs')


def path_to_url(path):
    if str(path) == '.':
        return ''
    return re.sub(r'\d+_', '', str(path.with_suffix('')))


def iter_docs():
    for path in sorted(docs_path.glob('**/*')):
        if not (path.suffix == '.md' or path.is_dir()):
            continue
        yield path


def get_doc_links():
    """
        Return a map of doc name to url. Given 'docs/01_user_pathways/01_researchers.md', return
        {'researchers': 'user_pathways/researchers'}.
    """
    doc_links = {}
    for path in iter_docs():
        order, file_name = path.with_suffix('').name.split('_', 1)
        if file_name == 'index':
            continue
        if file_name in doc_links:
            raise ValueError(f"Two documentation pages have the file name '{file_name}'. Change the file name for one of them.")
        doc_links[file_name] = path_to_url(path.relative_to(docs_path))
    return doc_links


def get_toc_by_url():
    from capapi.documents import CaseDocument
    base_path = Path(__file__).parent.joinpath('templates/docs')
    toc_by_url = {
        '': {
            'parents': [],
            'children': [],
            'url': '',
            'meta': {
                'doc_link': '/',
            }
        },
    }

    # context variables for rendering markdown templates
    context = {
        'email': settings.DEFAULT_FROM_EMAIL,
        'news': get_data_from_lil_site(section="news"),
    }
    try:
        case = CaseDocument.get(id=settings.API_DOCS_CASE_ID)
    except NotFoundError:
        try:
            case = CaseDocument.search()[0].execute()[0]
        except NotFoundError:
            case = None
    context['case_id'] = case.id if case else 1
    context['case_url'] = reverse('cases-detail', args=[context['case_id']], host='api')
    context['case_cite'] = case.citations[0].cite if case else "123 U.S. 456"

    def path_string_to_title(string):
        return string.replace('-', ' ').replace('_', ' ').title().replace('Api', 'API').replace('Cap', 'CAP')

    for path in iter_docs():
        if not (path.suffix == '.md' or path.is_dir()):
            continue
        rel_path = path.relative_to(base_path)
        parent_url = path_to_url(rel_path.parent)
        order, file_name = rel_path.with_suffix('').name.split('_', 1)
        display_name = path_string_to_title(file_name)
        is_index = display_name == 'Index'
        if is_index:
            entry = toc_by_url[parent_url]
        else:
            entry = {
                'url': path_to_url(rel_path),
                'file_name': file_name,
                'label': display_name,
                'uid': str(rel_path.with_suffix('')).replace("/", "_"),
                'content': '',
                'children': [],
                'order': int(order),
                'meta': {
                    'title': display_name,
                },
            }
        if path.suffix == '.md':
            entry['path'] = str(path)
            try:
                markdown_doc = render_to_string(str(path), context)
            except Exception as e:
                raise Exception(f"Error rendering template {path}") from e
            content, doc_toc, meta = render_markdown(markdown_doc)
            if settings.DOCS_SHOW_DRAFTS is False and meta.get('status') == 'draft':
                continue
            entry['doc_toc'] = mark_safe(doc_toc)
            entry['doc_toc_absolute'] = mark_safe(
                re.sub(r'href="#', 'href="{}#'.format(reverse('docs', args=[entry['url']])), doc_toc))

            entry['content'] = mark_safe(content)
            entry['meta'].update({k: mark_safe(v) for k, v in meta.items()})
            entry['label'] = entry['meta'].get('short_title') or entry['meta']['title']
        if not is_index:
            parent_entry = toc_by_url[parent_url]
            parent_entry['children'].append(entry)
            entry['parents'] = parent_entry['parents'] + [parent_entry]
            toc_by_url[entry['url']] = entry

    for item in toc_by_url.values():
        item['children'].sort(key=lambda i: i['order'])

    return toc_by_url


# in production, only calculate these once
if not settings.DEBUG:
    get_toc_by_url = lru_cache(None)(get_toc_by_url)
    get_doc_links = lru_cache(None)(get_doc_links)
