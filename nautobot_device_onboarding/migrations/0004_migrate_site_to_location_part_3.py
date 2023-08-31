from django.db import migrations, models

import nautobot.dcim.models
import nautobot.extras.models 


class Migration(migrations.Migration):

    dependencies = [
        ("nautobot_device_onboarding", "0004_migrate_site_to_location_part_2"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="onboardingtask",
            name="site",
        )
    ]
