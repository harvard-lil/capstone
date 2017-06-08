import logging
from random import randint

from django.template.defaultfilters import slugify
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


def generate_unique_slug(model, raw_string):
    """
    Rejection sampling: generate unique slug, check for uniqueness
    if found in model, resample
    """
    rand_num = randint(1000, 10000)
    slug = "%s-%s" % (slugify(raw_string[:100]), rand_num)
    try:
        model.objects.get(slug=slug)
        logger.warn("Slug %s found in %s model" % (slug, model))
        generate_unique_slug(model, raw_string)
    except ObjectDoesNotExist:
        return slug
