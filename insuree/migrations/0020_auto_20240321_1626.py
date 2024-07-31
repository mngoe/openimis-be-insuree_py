# Generated by Django 3.2.23 on 2024-03-21 16:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('insuree', '0019_auto_20231026_1205'),
    ]

    operations = [
        migrations.AddField(
            model_name='family',
            name='family_level',
            field=models.CharField(choices=[('1', '1'), ('2', '2')], db_column='FamilyLevel', default='1', max_length=1),
        ),
        migrations.AddField(
            model_name='family',
            name='parent',
            field=models.ForeignKey(blank=True, db_column='ParentFamily', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='insuree.family'),
        ),
    ]