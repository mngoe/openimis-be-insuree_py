# Generated by Django 3.2.17 on 2023-03-18 19:08

import core.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('insuree', '0013_auto_20211103_1023'),
    ]

    operations = [
        migrations.CreateModel(
            name='InsureeAttachment',
            fields=[
                ('idAttachment', models.AutoField(db_column='idAttachment', primary_key=True, serialize=False)),
                ('folder', models.CharField(db_column='Folder', max_length=250, null=True)),
                ('filename', models.CharField(db_column='FileName', max_length=250, null=True)),
                ('title', models.CharField(db_column='Title', max_length=250, null=True)),
                ('date', core.fields.DateField(blank=True, db_column='AttachmentDate', null=True)),
                ('document', models.TextField()),
                ('mime', models.CharField(db_column='Mime', max_length=250)),
                ('insuree', models.ForeignKey(db_column='InsureeID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='attachments', to='insuree.insuree')),
            ],
            options={
                'db_table': 'tblattachment',
            },
        ),
    ]
