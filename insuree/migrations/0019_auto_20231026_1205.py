# Generated by Django 3.2.21 on 2023-10-26 12:05

import core.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('insuree', '0018_confirmationtype_is_confirmation_number_required'),
    ]

    operations = [
        migrations.AlterField(
            model_name='insuree',
            name='chf_id',
            field=models.CharField(blank=True, db_column='CHFID', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='insuree',
            name='dob',
            field=core.fields.DateField(blank=True, db_column='DOB', null=True),
        ),
        migrations.AlterField(
            model_name='insuree',
            name='head',
            field=models.BooleanField(db_column='IsHead', default=False),
        ),
        migrations.AlterField(
            model_name='insuree',
            name='status',
            field=models.CharField(blank=True, choices=[('AC', 'Active'), ('IN', 'Inactive'), ('DE', 'Dead')], default='AC', max_length=2, null=True),
        ),
    ]