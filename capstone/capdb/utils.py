from django.template.defaultfilters import slugify


def generate_unique_slug(instance, raw_string, field='slug', max_tries=1000):
    """
        Get a unique slug for instance by sluggifying raw_string, checking database, and appending -1, -2 etc. if necessary.
        When checking uniqueness, ignore this object itself if it already exists in the database.

        Usage:
            my_instance.slug = generate_unique_slug(my_instance, 'Obj Title')
    """

    slug_base = "%s" % slugify(raw_string[:100])
    for count in range(max_tries):
        slug = slug_base
        if count:
            slug = "%s-%s" % (slug, count)

        # ORM query for objects of the same model, with the same slug
        found = type(instance).objects.filter(**{field: slug})

        # Exclude this exact instance from the query
        if instance.pk:
            found = found.exclude(pk=instance.pk)

        if not found.exists():
            return slug

    raise Exception("No unique slug found after %s tries." % max_tries)
