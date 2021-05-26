from django.db import migrations


def add_author(apps, schema_editor):
    Timeline = apps.get_model("labs", "Timeline")

    for timeline in Timeline.objects.all():
        if "author" not in timeline.timeline:
            timeline.timeline["author"] = "CAP User"
        timeline.save()


class Migration(migrations.Migration):
    dependencies = [
        ('labs', '0008_alter_timeline_timeline'),
    ]

    operations = [
        migrations.RunPython(add_author, migrations.RunPython.noop),
    ]
