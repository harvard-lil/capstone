import os
from contextlib import contextmanager
from django.template.defaultfilters import slugify
from functools import lru_cache

import boto3
from django.conf import settings

nsmap = {
    'mets': 'http://www.loc.gov/METS/',
    'case': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case:v1',
    'casebody': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1',
    'volume': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Volume:v1',
    'xlink': 'http://www.w3.org/1999/xlink',
    'alto': 'http://www.loc.gov/standards/alto/ns-v3#',
    'info': 'info:lc/xmlns/premis-v2',
}

def read_file(path):
    """
        Get contents of a local file by path.
    """
    with open(path) as in_file:
        return in_file.read()



def generate_unique_slug(model, field, raw_string, count=None):
    """
    :param field: the field requiring unique slug
    :param raw_string: basis for slug
    :return:
    Rejection sampling: generate unique slug, check for uniqueness
    if found in model, resample
    """

    if count:
        slug = "%s-%s" % (slugify(raw_string[:100]), str(count))
    else:
        slug = "%s" % slugify(raw_string[:100])
        count = 0

    kwargs = {field: slug}

    found = model.objects.filter(**kwargs)
    if found.count() == 0:
        return slug
    else:
        count += 1
        return generate_unique_slug(model, field, raw_string, count=count)
