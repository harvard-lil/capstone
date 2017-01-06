import gc
from random import randint
from django.template.defaultfilters import slugify

def queryset_iterator(queryset, chunksize=1000):
    '''
    taken from https://djangosnippets.org/snippets/1949/
    Iterate over a Django Queryset ordered by the primary key

    This method loads a maximum of chunksize (default: 1000) rows in it's
    memory at the same time while django normally would load all rows in it's
    memory. Using the iterator() method only causes it to not preload all the
    classes.

    Note that the implementation of the iterator does not support ordered query sets.
    '''
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()

def generate_unique_slug(model, value):
    rand_num = randint(1000,10000)
    slug = "%s-%s" % (slugify(value[:100]),rand_num)
    # check for uniqueness
    print slug
    try:
        model.objects.get(slug=slug)
        # if case exists, call again
        print 'slug exists:', slug
        generate_unique_slug(value)
    except:
        return slug
