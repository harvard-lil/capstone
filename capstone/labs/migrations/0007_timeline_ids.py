# Generated by Django 2.2.19 on 2021-04-01 12:46

from django.db import migrations, models
from labs.models import get_short_uuid


# Move IDS for cases, events, and categories to strings from integers
def fill_reporter_slug(apps, schema_editor):
    Timeline = apps.get_model("labs", "Timeline")
    for timeline in Timeline.objects.all():
        for event in timeline.timeline['events']:
            if type(event['id']) is int:
                event['id'] = get_short_uuid()

        for case in timeline.timeline['cases']:
            if type(case['id']) is int:
                case['id'] = get_short_uuid()

        if 'categories' in timeline.timeline:
            for cat in timeline.timeline['categories']:
                if ('id' in cat and type(cat['id']) is int) or ('id' not in cat):
                    cat['id'] = get_short_uuid()

        timeline.save()


class Migration(migrations.Migration):
    dependencies = [
        ('labs', '0006_auto_20210401_1246'),
    ]

    operations = [
        migrations.RunPython(fill_reporter_slug, migrations.RunPython.noop),
    ]
