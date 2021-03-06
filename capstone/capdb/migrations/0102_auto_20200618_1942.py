# Generated by Django 2.2.13 on 2020-06-18 19:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('capdb', '0101_auto_20200423_1714'),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP INDEX IF EXISTS %s;' % index_name,
        ) for index_name in (
            'idx_casemetadata_name_abbr_upper_gin',
            'capdb_casemetadata_name_abbreviation_7d78f106',
            'capdb_casemetadata_name_abbreviation_7d78f106_like',
            'capdb_casemetadata_case_id_ed4ba326_like',
            'idx_casemetadata_docket_number_upper',
        )
    ]
