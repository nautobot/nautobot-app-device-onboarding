# Generated by Django 3.2.21 on 2023-10-11 19:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0006_update_model_fields_part_3"),
    ]

    operations = [
        migrations.AlterField(
            model_name="onboardingtask",
            name="ip_address",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
    ]
