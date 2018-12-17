# TODO (https://github.com/harvard-lil/capstone/pull/709): Properly actualize the migration
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('capdb', '0057_auto_20181115_1834'),
    ]

    operations = [
        migrations.CreateModel(
            name='CitationGraph',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('src_case', models.ForeignKey(null=False, on_delete=models.deletion.CASCADE, related_name='case_metadatas', to='capdb.CaseMetadata')),
                ('dst_case', models.ForeignKey(null=False, on_delete=models.deletion.CASCADE, related_name='case_metadatas', to='capdb.CaseMetadata')),
            ],
        ),
    ]
