# Generated by Django 2.2.16 on 2021-02-17 17:23

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('labs', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='TimeLine',
            new_name='Temp_rename',
        ),
    ]
