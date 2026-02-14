# Custom sites migrations for Django 6.0+
# Django 6.0 removed built-in migrations for contrib.sites.
# allauth still references ('sites', '0001_initial') as a dependency.
# This file provides the missing migration.

from django.contrib.sites.models import _simple_domain_name_validator
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(max_length=100, unique=True, validators=[_simple_domain_name_validator], verbose_name='domain name')),
                ('name', models.CharField(max_length=50, verbose_name='display name')),
            ],
            options={
                'verbose_name': 'site',
                'verbose_name_plural': 'sites',
                'db_table': 'django_site',
                'ordering': ['domain'],
            },
        ),
    ]
