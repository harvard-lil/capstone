# TODO (https://github.com/harvard-lil/capstone/pull/709): Finalize fields for actualization

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('capdb', '0057_auto_20181115_1834'),
    ]

    operations = [
        migrations.CreateModel(
            name='CrossCaseCitation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('src_case', models.TextField()),
                ('dst_case', models.TextField()),
                ('count', models.IntegerField()),
            ],
        ),
    ]
