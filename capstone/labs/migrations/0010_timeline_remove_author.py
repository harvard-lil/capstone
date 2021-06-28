from django.db import migrations


def add_author(apps, schema_editor):
    Timeline = apps.get_model("labs", "Timeline")

    for timeline in Timeline.objects.all():
        if "author" in timeline.timeline and timeline.timeline["author"] == "CAP User":
            timeline.timeline["author"] = ""
        timeline.save()


class Migration(migrations.Migration):
    dependencies = [
        ('labs', '0009_timeline_add_author'),
    ]

    operations = [
        migrations.RunPython(add_author, migrations.RunPython.noop),
    ]
