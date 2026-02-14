# Django 6.0 + DEFAULT_AUTO_FIELD = BigAutoField
# The Site model's id must match the project's DEFAULT_AUTO_FIELD.
# Also add the missing domain validator.

from django.contrib.sites.models import _simple_domain_name_validator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="site",
            name="id",
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="site",
            name="domain",
            field=models.CharField(
                max_length=100,
                unique=True,
                validators=[_simple_domain_name_validator],
                verbose_name="domain name",
            ),
        ),
    ]
