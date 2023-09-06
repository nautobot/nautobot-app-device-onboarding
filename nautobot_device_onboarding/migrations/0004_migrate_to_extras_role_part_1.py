from django.db import migrations, models

import nautobot.dcim.models
import nautobot.extras.models 


class Migration(migrations.Migration):


    dependencies = [
        ("nautobot_device_onboarding", "0003_onboardingtask_label"),
        ("extras", "0061_role_and_alter_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="onboardingtask",
            name="new_role",
            field=nautobot.extras.models.RoleField(to="dcim.Device", on_delete=models.SET_NULL, blank=True, null=True),
        ),
    ]

