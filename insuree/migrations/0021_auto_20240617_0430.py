# Generated by Django 3.2.23 on 2024-06-17 04:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('insuree', '0020_auto_20240205_0934'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='family',
            index=models.Index(fields=['uuid'], name='IX_tblFamilies_uuid'),
        )
    ]