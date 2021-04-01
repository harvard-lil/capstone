# Generated by Django 2.2.19 on 2021-04-01 12:46

from django.db import migrations, models
from labs.models import get_short_uuid


class Migration(migrations.Migration):

    dependencies = [
        ('labs', '0005_auto_20210401_1246'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timeline',
            name='uuid',
            field=models.CharField(default=get_short_uuid, max_length=10, unique=True),
        )
    ]
