# Generated by Django 3.2.20 on 2023-07-28 16:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('insuree', '0020_merge_20230714_1158'),
    ]

    operations = [
        migrations.AddField(
            model_name='insuree',
            name='arab_last_name',
            field=models.CharField(blank=True, db_column='ArabLastName', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='insuree',
            name='arab_other_names',
            field=models.CharField(blank=True, db_column='ArabOtherNames', max_length=100, null=True),
        ),
    ]
