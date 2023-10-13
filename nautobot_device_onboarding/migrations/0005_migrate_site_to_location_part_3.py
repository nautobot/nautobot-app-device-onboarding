from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_device_onboarding", "0005_migrate_site_to_location_part_2"),
    ]

    run_before = [
        ("dcim", "0040_remove_region_and_site"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="onboardingtask",
            name="site",
        )
    ]
