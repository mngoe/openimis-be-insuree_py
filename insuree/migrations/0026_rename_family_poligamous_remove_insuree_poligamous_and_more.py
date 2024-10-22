# Generated by Django 4.2.16 on 2024-10-18 12:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('insuree', '0024_auto_20240326_1505'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='insuree',
            name='poligamous',
        ),
        migrations.RenameField(
            model_name='family',
            old_name='poligamous',
            new_name='polygamous',
        ),
        migrations.AlterField(
            model_name='family',
            name='polygamous',
            field=models.BooleanField(db_column='PolygamousFamily', blank=True,  null=True),
        ),
    ]
