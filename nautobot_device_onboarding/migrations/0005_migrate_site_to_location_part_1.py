from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0004_migrate_to_extras_role_part_3"),
        ("dcim", "0034_migrate_region_and_site_data_to_locations"),
        ("extras", "0062_collect_roles_from_related_apps_roles"),
    ]

    operations = [
        migrations.AddField(
            model_name="onboardingtask",
            name="location",
            field=models.ForeignKey(to="dcim.Location", on_delete=models.SET_NULL, blank=True, null=True),
        ),
    ]
