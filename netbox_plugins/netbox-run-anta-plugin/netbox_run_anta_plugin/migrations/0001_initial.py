# migrations/0001_initial.py

from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AntaStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('last_known_hash', models.CharField(blank=True, help_text='The SHA256 hash of the status file content from the last run', max_length=64)),
            ],
            options={
                'verbose_name': 'ANTA Status',
                'verbose_name_plural': 'ANTA Status',
            },
        ),
    ]
