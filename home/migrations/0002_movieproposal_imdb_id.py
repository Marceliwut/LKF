# Generated migration to add imdb_id field to MovieProposal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='movieproposal',
            name='imdb_id',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
