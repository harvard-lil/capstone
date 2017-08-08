from django.template.defaultfilters import slugify


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
